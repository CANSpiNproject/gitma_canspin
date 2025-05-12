from gitma_canspin.project import CatmaProject, AnnotationCollection, Annotation
from gitma_canspin._write_annotation import write_annotation_json_with_ac_object
from gitma_canspin.annotation import get_tagset_uuid
from gitma_canspin._helper import (
    makedir_if_necessary, 
    dict_travel_generator, 
    reduce_decimal_place, 
    prevent_division_by_zero,
    translate_dict, 
    abs_local_save_path, 
    canspin_catma_projects, 
    canspin_annotation_tsv_columns,
    canspin_annotation_schema_mapping,
    key_translation
)

import pandas as pd
from copy import deepcopy
import time
import os
import subprocess
import random
import yaml
import json
import re

from typing import Union, Tuple, Dict, List, Generator

import plotly.graph_objects
import pygal
from collections import Counter
import plotly.express as px
import plotly
import numpy as np
import bs4

from pyannote.core import Segment
from pygamma_agreement import (CombinedCategoricalDissimilarity, Continuum)

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(format='%(name)s - %(levelname)s - %(message)s', level=logging.INFO)

class CanspinProject:
    """Basic class with loading and management features for Catma projects.
    It is a wrapper class for gitmas CatmaProject class with tweaks and features designed for the use in the CANSpiN project.

    Args:
        imported_project(CatmaProject, optional): An already loaded CatmaProject can be passed here.
        init_settings(dict, optional): Defines necessary settings for loading the CATMA project.
    """
    def __init__(
            self,
            imported_project: Union[CatmaProject, None] = None,
            init_settings: Union[dict, None] = None):
        
        self.default_init_settings: dict = {
            'project_name': 'CATMA_5D2A90F0-4428-41CB-9D3A-E649CD1702C2_CANSpiN',
            'selected_annotation_collection': None,
            'load_from_gitlab': False,
            'gitlab_access_token': None
        }

        self.init_settings: dict = self.default_init_settings if not init_settings else init_settings

        self.project: Union[CatmaProject, None] = imported_project if imported_project else self.load_project()
        self.unify_plain_text_line_endings()

        self.tsv_annotations: Dict[str, Dict[str, pd.DataFrame]] = self.load_tsv_annotations()

    def load_project(self) -> Union[CatmaProject, None]:
        """Method to fill self.project with a CatmaProject instance downloaded from Catmas gitlab or from local folder.

        Returns:
            CatmaProject or None: Downloaded or locally loaded CatmaProject instance or None in case of a loading error.
        """
        try:
            return CatmaProject(
                project_name=self.init_settings.get('project_name', 'CATMA_5D2A90F0-4428-41CB-9D3A-E649CD1702C2_CANSpiN'),
                included_acs=self.init_settings.get('selected_annotation_collection'),
                load_from_gitlab=self.init_settings.get('load_from_gitlab', False),
                gitlab_access_token=self.init_settings.get('gitlab_access_token')
            )
        except:
            logger.warning('Could not load the Catma project.', exc_info=True)
            return None

    def unify_plain_text_line_endings(self) -> None:
        """Helper method which checks if text in CatmaProject object was loaded on a windows system.
        In this case the line endings ('\r\n') are reduced to unix standard ('\n') so that the text has the same length on windows and unix machines.
        """
        _correction_applied: bool = False

        if self.project:
            if len(self.project.annotation_collections):
                for ac in self.project.annotation_collections:
                    if b'\r\n' in ac.text.plain_text.encode():
                        byte_text = ac.text.plain_text.encode()
                        corrected_byte_text = byte_text.replace(b'\r\n', b'\n')
                        corrected_string_text = corrected_byte_text.decode()
                        ac.text.plain_text = corrected_string_text
                        _correction_applied = True
        
        if _correction_applied:
            logger.info('The line endings of all texts of the loaded project have been unified to unix standard.')

    def update_project(self) -> None:
        """Method to update the CatmaProject instance in self.project by accessing Catmas gitlab backend.
        Uses the update method of CatmaProject class.
        """
        if not self.project:
            logger.info('Currently no project is loaded.')
            return
        
        try:
            self.project.update()
        except:
            logger.warning('Could not update the Catma project.', exc_info=True)

    def load_tsv_annotations(self) -> Dict[str, Dict[str, pd.DataFrame]]:
        """Method to fill self.tsv_annotations with a dict of dicts containing a tsv filename as key and a Dataframe with the respective annotation data as value.
        The Data is derived from the tsv folders within the CANSpiN corpora repos. For that, the corpus.yaml inside the repos is processed as well as the respective tsv folders.
        The keys of the dict equal the annotation schemes of the corpus found in the corpus.yaml.
        The keys of the subordinated dict equal the tsv filenames containing the annotations.
        To be successfully loaded, the CANSpiN corpora repos must be placed in the project folder.

        Returns:
            Dict[str, Dict[str, pd.DataFrame]] or an empty dict: A dict with a dict of lists of Dataframes derived from the annotation tsv files or an empty dict in case of missing tsv files or repo folders.
        """
        # get corpus repos in project folder, using hardcoded dict canspin_catma_projects from helper module
        rel_local_save_path = os.getcwd()
        folders_in_project_folder: List[str] = os.listdir(rel_local_save_path)
        projects_corpora_folders_in_project_folder: List[str] = [folder for folder in folders_in_project_folder if self.init_settings['project_name'] in canspin_catma_projects and folder in canspin_catma_projects[self.init_settings['project_name']]['corpora_folders']]

        if not projects_corpora_folders_in_project_folder:
            logger.info(f"No annotation tsv files loaded for the given project name: not a canspin project or missing canspin corpora folders.")
            return dict()

        # load each corpus yaml
        corpora_data: Dict[str, dict] = dict()

        for corpus_folder in projects_corpora_folders_in_project_folder:
            corpus_yaml_filepath: str = os.path.join(rel_local_save_path, corpus_folder, "corpus.yaml")
            
            if not os.path.exists(corpus_yaml_filepath):
                logger.info("No annotation tsv files loaded for the given project name: corpus yaml not found.")
                return dict()
            
            with open(corpus_yaml_filepath, encoding='utf-8') as stream:
                try:
                    yaml_data: dict = yaml.safe_load(stream)
                    corpora_data[corpus_folder] = yaml_data
                except:
                    logger.warning(f"The corpus yaml for '{corpus_folder}' could not be parsed.", exc_info=True)
                    corpora_data[corpus_folder] = dict()

        if not len([_corpus_folder for _corpus_folder in corpora_data if len(corpora_data[_corpus_folder])]):
            logger.info("No annotation tsv files loaded for the given project name: no corpus yaml data could be parsed.")
            return dict()

        # get annotation tsv filenames for every annotation schema found in the corpus yamls
        annotation_data: Dict[str, List[str]] = dict()

        def _get_tsv_file_names_of_schema(schema_dict: dict) -> List[str]:          
            return list(dict_travel_generator(schema_dict, str))
            
        for corpus_folder in corpora_data:
            if not len(corpora_data[corpus_folder]):
                logger.info(f"No annotation tsv files loaded for '{corpus_folder}' due to missing corpus yaml data.")
                continue
            for text in corpora_data[corpus_folder]['texts']:
                for annotation_schema in corpora_data[corpus_folder]['texts'][text]['annotations']:
                    if annotation_schema not in annotation_data:
                        annotation_data[annotation_schema] = list()
                    annotation_data[annotation_schema].extend(_get_tsv_file_names_of_schema(corpora_data[corpus_folder]['texts'][text]['annotations'][annotation_schema]))

        if not len([_annotation_schema for _annotation_schema in annotation_data if len(annotation_data[_annotation_schema])]):
            logger.info(f"No annotation tsv files loaded for the given project name: corpus yaml data does not provide any annotation tsv filenames.")
            return dict()

        # load annotation tsv files as Dataframes, put all together in a result dict ({annotation_schema: {tsv_filename: pd.Dataframe}}) and return it
        result: Dict[str, Dict[str, pd.DataFrame]] = dict()

        for annotation_schema in annotation_data:
            result[annotation_schema] = {
                tsv_filename: pd.read_csv(
                        filepath_or_buffer=os.path.join(
                            rel_local_save_path, 
                            tsv_filename.split("_")[0].lower(), 
                            f"{annotation_schema}-tsv", 
                            tsv_filename
                        ), 
                        sep="\t", 
                        header=0
                    ) for tsv_filename in annotation_data[annotation_schema]
            }

        return result

    def tsv_annotations_has_data(self) -> bool:
        """Helper method to determine if any dataframes are saved inside the tsv_annotations dict.

        Returns:
            bool: True if any dataframes are saved inside the tsv_annotations dict.
        """
        return isinstance((next(dict_travel_generator(self.tsv_annotations, pd.DataFrame), None)), pd.DataFrame)

    def print_tsv_annotations_overview(self) -> None:
        """Helper method for getting an quick visual overview over the loaded tsv data of the project.
        Prints lists of filenames sorted under their respective annotation schema.
        """
        if self.tsv_annotations_has_data():
            logger.info(f'tsv files found in canspin project!')
            time.sleep(1)
            print('\noverview:')
            for annotation_schema in self.tsv_annotations:
                print(f'- schema "{annotation_schema}"')
                for filename in self.tsv_annotations[annotation_schema]:
                    print(f'\t{filename}')
        else:
            logger.info('There are no annotation tsvs loaded in the canspin project.')

    def print_projects_annotation_collection_list(
            self,
            filter_for_text: Union[str, None] = None) -> None:
        """Helper method for finding annotation collections in the loaded project.
        Prints the names of all annotation collections of the loaded project, possibly filted by text title.

        Args:
            filter_for_text (Union[str, None], optional): Takes a string and filters the printed list for those collections, whose refering text has a name, which includes the substring delivered with the filter_for_text argument. Defaults to None.
        """
        if not self.project:
            logger.info('Currently no project is loaded.')
            return
        
        self.project.print_annotation_collections_list(filter_for_text=filter_for_text)

    def get_annotation_collection_index_by_ac_name_and_text_title(
            self,
            ac_name: str, 
            text_title: str) -> Union[int, None]:
        """Helper method for finding a annotation collection index value in the self.project.annotation_collections list.
        Both the annotation collection name and the title of the text the annotation collection refers to are \
        necessary value to determine the index value.

        Args:
            ac_name (str): The name of the Annotation Collection you are looking for.
            text_title (str): The title of the text the Annotation Collection refers to.
        
        Returns:
            Integer or None: The index value of the annotation collection you are looking for or None, in case there is no project loaded.

        Raises:
            ValueError: If there is a project loaded, but the input data leads to no clear allocation, \
                        then it is assumed that the data entered for determining the index value is incorrect, \
                        as the rule in the CANSpiN project is that several annotation collections may not have \
                        the same name for the same text.
        """
        if not self.project:
            logger.info('Currently no project is loaded.')
            return
        
        indices: list = [
            index for index, ac in enumerate(self.project.annotation_collections)
            if ac.name == ac_name and ac.text.title == text_title
        ]

        if len(indices) != 1:
            raise ValueError('No or two or more indices have been found. The given AnnotationCollection name or text title might be wrong.')
        
        return indices[0]
    
    def test_text_borders(
            self, 
            annotation_collection_index: int,
            text_borders: Tuple[int, int],
            text_snippet_length: int = 30) -> Union[str, None]:
        """Helper method for testing text_border values for selecting a desired text segment of an original annotation collections text.
        Logs and exports a substring of an annotation collections text. It's beginning and end is defined by text_borders parameter, \
        the length of the text blocks at the beginning and the end is defined by text_snippets_length parameter.

        Args:
            annotation_collection_index (int): Selects the annotation collection by index.
            text_borders (tuple): Specifies the first and the last character index of the selected text inside the original annotation collections text.
            text_snippets_length (int, optional): Specifies the amount of text logged right and left from the defined text_borders. Defaults to 30.

        Returns:
            Str: A substring of an annotation collection text is returned. It's beginning and end is defined by text_borders parameter, \
                 the length of the text blocks at the beginning and the end is defined by text_snippets_length parameter.

        Raises:
            ValueError: Is raised, if a project is loaded, but no annotation collection index or text_borders values are provided.
        """
        if not self.project:
            logger.info('Currently no project is loaded.')
            return
        
        if annotation_collection_index is None:
            raise ValueError('No annotation collection index has been provided.')
        
        if not text_borders:
            raise ValueError('No text_borders values have been provided.')

        text: str = self.project.annotation_collections[annotation_collection_index].text.plain_text
        text = text[text_borders[0]:text_borders[1]]
        result: str = '"' + ((text[:text_snippet_length] + '...' + text[-abs(text_snippet_length):]) if len(text) >= (text_snippet_length * 2) else text) + '"'
        
        logger.info(result)
        return result
    
    def get_text_border_values_by_string_search(
            self, 
            annotation_collection_index: int, 
            substrings: Tuple[str, str]) -> Union[Tuple[int, int], Tuple[List[int], List[int]], None]:
        """Helper method for determing text_border values for selecting a desired text segment of an original annotation collections text.
        Based on the two provided substrings in the substrings tuple the indices of the first character (of the first substring \
        and the last character (of the second substring) in the text string are computed. If exactly two index values could be determined, \
        they are returned in a tuple. If none or multiple values are determined either for the first or the second substring, a tuple \
        of lists with none or multiple values is returned.

        Args:
            annotation_collection_index (int): Selects the annotation collection by index, in whose text the substrings are to be found.
            substrings (Tuple[str, str]): Defines the substrings for which the indices inside the given text are to be determined.

        Returns:
            Union[Tuple[int, int], Tuple[List[int], List[int]]]: If exactly two index values could be determined, \
                                                                 a tuple with two integers is returned. If none or multiple values \
                                                                 are determined either for the first or the second substring, \
                                                                 a tuple of lists with none or multiple possible values is returned.

        Raises:
            ValueError: Is raised, if a project is loaded, but no annotation collection index or substrings are provided.
        """
        if not self.project:
            logger.info('Currently no project is loaded.')
            return
        
        if annotation_collection_index is None:
            raise ValueError('No annotation collection index has been provided.')
        
        if not substrings:
            raise ValueError('No valid substring input has been provided.')
        
        occurences_start = [match.start() for match in re.finditer(substrings[0], self.project.annotation_collections[annotation_collection_index].text.plain_text)]
        occurences_end = [match.end() for match in re.finditer(substrings[1], self.project.annotation_collections[annotation_collection_index].text.plain_text)]
        
        result = (occurences_start[0], occurences_end[0]) \
                 if len(occurences_start) == 1 and len(occurences_end) == 1 \
                 else (occurences_start, occurences_end)
        return result

class AnnotationExporter(CanspinProject):
    """Bundling class to access and control all export functions created for the CATMA-to-CANSpiN pipeline for annotation data.

    Args:
        imported_project(CatmaProject, optional): An already loaded CatmaProject can be passed here.
        init_settings(dict, optional): Defines necessary settings for loading the CATMA project.
        processing_settings(dict, optional): Defines necessary and optional settings for the export process.
        steps(Dict[str, dict], optional): Controls processing pipeline steps, i.e. step activation and file names for steps input and output.
    """
    def __init__(
            self,
            imported_project: Union[CatmaProject, None] = None,
            init_settings: Union[dict, None] = None,
            processing_settings: Union[dict, None] = None,
            steps: Union[Dict[str, dict], None] = None):
        
        super().__init__(
            imported_project=imported_project,
            init_settings=init_settings
        )
        
        self.default_processing_settings: dict = {
            'spacy_model_lang': 'German',
            'nlp_max_text_len': 2000000,
            'text_borders': None,
            'insert_paragraphs': True,
            'paragraph_recognition_text_class': 'eltec-deu',
            'use_all_text_selection_segments': True
        }
        self.default_steps: Dict[str, dict] = {
            'create_basic_token_tsv': {
                'activated': True,
                'output_tsv_file_name': 'basic_token_table'
            },
            'create_annotated_token_tsv': {
                'activated': True,
                'input_tsv_file_name': 'basic_token_table',
                'output_tsv_file_name': 'annotated_token_table'
            },
            'create_annotated_tei': {
                'activated': True,
                'input_tsv_file_name': 'annotated_token_table',
                'output_tei_file_name': 'annotated_tei'
            }
        }

        self.processing_settings: dict = self.default_processing_settings if not processing_settings else processing_settings
        self.steps: Dict[str, dict] = self.default_steps if not steps else steps

    def test_text_borders(
            self, 
            annotation_collection_index,
            text_borders: Union[Tuple[int, int], None] = None, 
            text_snippet_length: int = 30) -> Union[str, None]:
        """Helper method for finding text_border values for selecting a desired text segment of an original annotation collections text.
        Logs and returns a substring of an annotation collections text. It's beginning and end is defined by text_borders parameter, \
        the length of the text blocks at the beginning and the end is defined by text_snippets_length parameter.

        Args:
            annotation_collection_index (int): Selects the annotation collection by index.
            text_borders (tuple, optional): Specifies the first and the last character index of the selected text inside the original annotation collections text. \
                                            Defaults to None. If no value is provided, the method will use settings von self.processing_settings.
            text_snippets_length (int, optional): Specifies the amount of text logged right and left from the defined text_borders. Defaults to 30.

        Returns:
            Str: A substring of an annotation collection text is returned. It's beginning and end is defined by text_borders parameter, \
                 the length of the text blocks at the beginning and the end is defined by text_snippets_length parameter.

        Raises:
            ValueError: Is raised, if a project is loaded, but no annotation collection index is provided.
        """
        if not self.project:
            logger.info('Currently no project is loaded.')
            return
        
        if annotation_collection_index is None:
            raise ValueError('No annotation collection index has been provided.')
        
        text_borders: Union[Tuple[int, int], None] = self.processing_settings['text_borders'] if not text_borders else text_borders

        if text_borders:
            text: str = self.project.annotation_collections[annotation_collection_index].text.plain_text
            text = text[text_borders[0]:text_borders[1]]
            result: str = '"' + ((text[:text_snippet_length] + '...' + text[-abs(text_snippet_length):]) if len(text) >= (text_snippet_length * 2) else text) + '"'
            
            logger.info(result)
            return result
        else:
            logger.info('No text borders were passed to the method or saved in the exporters processing settings.')

    def run(self, annotation_collection_index: int = 0) -> None:
        """Runs export pipeline steps defined in self.steps dictionary for the one annotation collection selected by annotation_collection_index.
        The pipline consists of 3 possible steps: create_basic_token_tsv, create_annotated_token_tsv and create_annotated_tei. \
        create_basic_token_tsv uses the DataFrame data loaded from gitlab as input. \
        create_annotated_token_tsv additionally depends on an input tsv file located in the folder of execution. \
        create_annotated_tei depends only on an input tsv file located in the folder of execution.

        Args:
            annotation_collection_index (int, optional): Selects the annotation collection by index. Defaults to 0.
        """
        if not self.project:
            logger.info('Currently no project is loaded.')
            return
        
        if len(self.project.annotation_collections) > 1:
            logger.info(f'There are multiple Annotation Collections in the currently loaded project.')
            logger.info(f'Selected Collection for export pipeline: "{self.project.annotation_collections[annotation_collection_index].name}" refering to text "{self.project.annotation_collections[annotation_collection_index].text.title}".')
        
        logger.info(f'Pipeline started.')

        methods = {
            'create_basic_token_tsv': (
                self.project.annotation_collections[annotation_collection_index].create_basic_token_tsv,
                {
                    'created_file_name': self.steps['create_basic_token_tsv']['output_tsv_file_name'],
                    'spacy_model_lang': self.processing_settings['spacy_model_lang'],
                    'text_borders': self.processing_settings['text_borders'],
                    'nlp_max_text_len': self.processing_settings['nlp_max_text_len']
                }
            ),
            'create_annotated_token_tsv': (
                self.project.annotation_collections[annotation_collection_index].create_annotated_token_tsv,
                {
                    'basic_token_file_name': self.steps['create_annotated_token_tsv']['input_tsv_file_name'],
                    'created_file_name': self.steps['create_annotated_token_tsv']['output_tsv_file_name'],
                    'text_borders': self.processing_settings['text_borders'],
                    'use_all_text_selection_segments': self.processing_settings['use_all_text_selection_segments']
                }
            ),
            'create_annotated_tei': (
                self.project.annotation_collections[annotation_collection_index].create_annotated_tei,
                {
                    'annotated_token_file_name': self.steps['create_annotated_tei']['input_tsv_file_name'],
                    'created_file_name': self.steps['create_annotated_tei']['output_tei_file_name'],
                    'insert_paragraphs': self.processing_settings['insert_paragraphs'],
                    'paragraph_recognition_text_class': self.processing_settings['paragraph_recognition_text_class']
                }
            )
        }

        activated_steps: List[str] = [step_name for step_name, step_settings in self.steps.items() if step_settings['activated']]

        for number, step_name in enumerate(iterable=activated_steps, start=1):
            logger.info(f'Executing step {number}/{len(activated_steps)}: "{step_name}" ...')
            methods[step_name][0](**methods[step_name][1])

        logger.info(f'Pipeline finished.')

class AnnotationAnalyzer(CanspinProject):
    """Bundling class to analyze and visualize annotation data.

    Args:
        imported_project(CatmaProject, optional): An already loaded CatmaProject can be passed here.
        init_settings(dict, optional): Defines necessary settings for loading the CATMA project.
    """
    def __init__(
        self,
        imported_project: Union[CatmaProject, None] = None,
        init_settings: Union[dict, None] = None):

        super().__init__(
            imported_project=imported_project,
            init_settings=init_settings
        )

        self.default_get_corpus_annotation_statistics_settings: dict = {
            # calculations (dict): specifies, which statistics will be calculated when executing the get_corpus_annotation_statistics method
            'calculations': {
                'amount_of_annotations': True,
                'amount_of_annotations_by_class': True,
                'amount_of_token': True,
                'amount_of_annotated_token': True,
                'amount_of_annotated_token_by_class': True,
                'ratios': True,
                'word_lists_by_class': True
            },
            # custom_grouping (Union[dict, None]): enable comparing features for statistics calculation by defining a dict in the custom_grouping key
            # the dict has to have one of the following structures, comparing either groups, groups with multiple subgroups or a mixture of both:
            # - {group_1: [], group_2: [], group_3: []}
            # - {group_1: {subgroup_1_1: [], subgroup_1_2: []}, group_2: {subgroup_2_1: [], subgroup_2_2: []}, group_3: {subgroup_3_1: [], subgroup_3_2: [], subgroup_3_3: []}}
            # - {group_1: [], group_2: {subgroup_2_1: [], subgroup_2_2: []}}
            # each list contains multiple tuple with 2 strings, specifying an annotation schema and a filename, refering to self.tsv_annotations data
            # files can be placed in multiple groups and subgroups
            # the keys in the custom_grouping dict can be freely named
            # if custom_grouping is not activated, the statistical values are grouped by annotation scheme as given in the corpus.yaml file of the corpus and by corpus as given by the filename
            'custom_grouping': None,
            # text_borders (Union[Tuple[int, int], None]): select a specific amount of token of every text. with the tuple the indices of the token
            # are specified. if the first token with a given index does not exist, the first one of the text is selected.
            # if the second token with a given index does not exist, the last one of the text is selected.
            'text_borders': None
        }
        self.default_get_iaa_settings: dict = {
            # alpha (float): coefficient weighting the positional dissimilarity value
            'alpha': 1.0,
            # beta (float): coefficient weighting the categorical dissimilarity value
            'beta': 1.0,
            # delta_empty (float): evaluation of dissimilarity with regard to blank spaces, i.e. when a text passage has been annotated by one annotator and not by another. defaults to 1.
            'delta_empty': 1.0,
            # n_samples (int): number of random continuum sampled from this continuum used to estimate the gamma measure
            'n_samples': 30,
            # precision_level (float): error percentage of the gamma estimation. if a literal precision level is passed (e.g. "medium"), the corresponding numerical value will be used (high: 1%, medium: 2%, low : 5%)
            'precision_level': 0.01,
            # text_borders (Union[Tuple(int, int), None]): specifies the first and the last character index of the selected text inside the annotation collections text. defaults to None
            'text_borders': None
        }
        self.default_render_progression_bar_chart_settings: dict = {
            # separation_unit_type values (str):
            #   'sentence': each bar represents X sentences, seperated by periods
            #   'token': each bar represents X token, seperated by spaces
            'separation_unit_type': 'token',
            # separation_unit_amount (int): amount of units of type selected in separation_unit_type for token amount representing a single bar in the chart
            'separation_unit_amount': 200,
            # output_type (str):
            #   'show': use default show method
            #   'html': export to html
            #   'svg': export to svg
            'output_type': 'show',
            # width (int): width of graphic in pixel
            'width': 1400,
            # height (int): height of graphic in pixel
            'height': 800,
            # font_size (int): general font size in pixel
            'font_size': 18,
            # title (bool): switch creation of default title on or off
            'title': True,
            # svg_render_engine (str):
            #   'auto': use kaleido if it is installed, otherwise use orca
            #   'kaleido': use kaleido
            #   'orca': use orca
            'svg_render_engine': 'auto',
            # category_and_class_system_name (str): select which category and classes should be selected in self.category_and_class_systems
            'category_and_class_system_name': 'CS1 v1.1.0 deu',
            # translate_classes_to_english (bool): based on the category_and_class_system_name the classes can be translated to English if a translation dict for this class system and language exists
            'translate_classes_to_english': False
        }
        self.default_render_overview_pie_chart_settings: dict = {
            # category_and_class_system_name (str): select which category and classes should be selected in self.category_and_class_systems
            'category_and_class_system_name': 'CS1 v1.1.0 deu'
        }
        self.category_and_class_systems: dict = {
            'CS1 v1.0.0 deu': {
                'languages': ['deu'],
                'categories': {
                    'Bewegung': '#B60000',
                    'Dimensionierung': '#7CD3C0',
                    'Ort': '#B6D3FF',
                    'Positionierung': '#DB8300',
                    'Richtung': '#92FFBD'
                },
                'classes': {
                    'Ort-Container': '#B6D3FF',
                    'Ort-Container-BK': '#CCDEFF',
                    'Ort-Objekt': '#D4EAFF',
                    'Ort-Objekt-BK': '#E6F2FF',
                    'Ort-Abstrakt': '#89A8F6',
                    'Ort-Abstrakt-BK': '#98C3FA',
                    'Ort-UE-XR': '#90A6C7',
                    'Ort-UE-RX': '#8093AD',
                    'Ort-UE-RR': '#6F8096',
                    'Bewegung-Subjekt': '#FF6D6D',
                    'Bewegung-Objekt': '#F60D00',
                    'Bewegung-Schall': '#FF4949',
                    'Bewegung-Licht': '#CA0B0B',
                    'Bewegung-Geruch': '#B60000',
                    'Bewegung-UE-XR': '#960000',
                    'Bewegung-UE-RX': '#7D0000',
                    'Bewegung-UE-RR': '#610000',
                    'Richtung': '#92FFBD',
                    'Richtung-UE-XR': '#75CC96',
                    'Richtung-UE-RX': '#69B584',
                    'Richtung-UE-RR': '#599970',
                    'Positionierung': '#DB8300',
                    'Positionierung-UE-XR': '#B56A01',
                    'Positionierung-UE-RX': '#995A02',
                    'Positionierung-UE-RR': '#804B01',
                    'Dimensionierung-Abstand': '#8AB6AD',
                    'Dimensionierung-Groesse': '#7CD3C0',
                    'Dimensionierung-Menge': '#7EF5D9',
                    'Dimensionierung-UE-XR': '#60847B',
                    'Dimensionierung-UE-RX': '#49615B',
                    'Dimensionierung-UE-RR': '#344541'
                }
            },
            'CS1 v1.1.0 deu': {
                'languages': ['deu'],
                'categories': {
                    'Bewegung': '#B60000',
                    'Dimensionierung': '#7CD3C0',
                    'Ort': '#B6D3FF',
                    'Positionierung': '#DB8300',
                    'Richtung': '#92FFBD'
                },
                'classes': {
                    'Ort-Container': '#B6D3FF',
                    'Ort-Container-BK': '#CCDEFF',
                    'Ort-Objekt': '#D4EAFF',
                    'Ort-Objekt-BK': '#E6F2FF',
                    'Ort-Abstrakt': '#89A8F6',
                    'Ort-Abstrakt-BK': '#98C3FA',
                    'Ort-ALT': '#90A6C7',
                    'Bewegung-Subjekt': '#FF6D6D',
                    'Bewegung-Objekt': '#F60D00',
                    'Bewegung-Schall': '#FF4949',
                    'Bewegung-Licht': '#CA0B0B',
                    'Bewegung-Geruch': '#B60000',
                    'Bewegung-ALT': '#960000',
                    'Richtung': '#92FFBD',
                    'Richtung-ALT': '#75CC96',
                    'Positionierung': '#DB8300',
                    'Positionierung-ALT': '#B56A01',
                    'Dimensionierung-Abstand': '#8AB6AD',
                    'Dimensionierung-Groesse': '#7CD3C0',
                    'Dimensionierung-Menge': '#7EF5D9',
                    'Dimensionierung-ALT': '#60847B'
                }
            },
            'CS1 v1.1.0 spa': {
                'languages': ['spa'],
                'categories': {
                    'Movimiento': '#B60000',
                    'Dimensionamiento': '#7CD3C0',
                    'Lugar': '#B6D3FF',
                    'Posicionamiento': '#DB8300',
                    'Dirección': '#92FFBD'
                },
                'classes': {
                    'Lugar-Contenedor': '#B6D3FF',
                    'Lugar-Contenedor-CM': '#CCDEFF',
                    'Lugar-Objeto': '#D4EAFF',
                    'Lugar-Objeto-CM': '#E6F2FF',
                    'Lugar-Abstracto': '#89A8F6',
                    'Lugar-Abstracto-CM': '#98C3FA',
                    'Lugar-ALT': '#90A6C7',
                    'Movimiento-Sujeto': '#FF6D6D',
                    'Movimiento-Objeto': '#F60D00',
                    'Movimiento-Sonido': '#FF4949',
                    'Movimiento-Luz': '#CA0B0B',
                    'Movimiento-Olfato': '#B60000',
                    'Movimiento-ALT': '#960000',
                    'Dirección': '#92FFBD',
                    'Dirección-ALT': '#75CC96',
                    'Posicionamiento': '#DB8300',
                    'Posicionamiento-ALT': '#B56A01',
                    'Dimensionamiento-Distancia': '#8AB6AD',
                    'Dimensionamiento-Tamaño': '#7CD3C0',
                    'Dimensionamiento-Cantitad': '#7EF5D9',
                    'Dimensionamiento-ALT': '#60847B'
                }
            },
            'spaceAN v1.0.0' : {
                'languages': ['deu', 'spa'],
                'categories': {
                    'CONTAINER': '#9dc3fd',
                    'OBJECT': '#7bf8d2',
                },
                'classes': {
                    'CONTAINER-ARTEFACT': '#9dc3fd',
                    'CONTAINER-NATURAL': '#7192c4',
                    'CONTAINER-REGION': '#4d678d',
                    'CONTAINER-SETTLEMENT': '#334663',
                    'OBJECT-ARTEFACT': '#7bf8d2',
                    'OBJECT-NATURAL': '#64b39b'
                }
            }
        }
    
    def _load_tsv_files(
            self, 
            tsv_filepath_list: List[str],
            render_settings: dict) -> pd.DataFrame:
        """Helper method to load data from tsv file(s) into one pandas dataframe.
        Designed for usage in analyzing methods, which might take a pandas dataframe or a list of tsv filepaths as input.

        Args:
            tsv_filepath_list (List[str]): List of strings, which are filepaths referring to tsv files following the CANSpiN annotation file schema.
            render_settings (dict): Specific render settings for the respective analyzing method.
            
        Returns:
            pd.DataFrame: If one filepath is delivered, this file will be transformed into a dataframe. If multiple filepathes are delivered, the given data will be transformed and concatinated in order of the given list to one dataframe.

        Raises:
            ValueError: Is raised if tsv_filepath_list is empty, contains other data types than strings, if delivered data do not follow the CANSpiN annotation file schema or if not all annotations belong to the class system specified in the render_settings.
            FileNotFoundError: Is raised if a given filepath is wrong.
        """
        dataframes: List[Dict[str, pd.DataFrame]] = []

        # initial input checks
        if not len(tsv_filepath_list):
            raise ValueError('Input data is neither a dataframe nor a list of strings.')

        for tsv_filepath in tsv_filepath_list:
            if not isinstance(tsv_filepath, str):
                raise ValueError('Input data is neither a dataframe nor a list of strings.')
            if not os.path.exists(tsv_filepath):
                raise FileNotFoundError('A filepath given in the input data is not valid.')
            
        # transformation into dataframes and data structure checks
        for tsv_filepath in tsv_filepath_list:
            df: pd.DataFrame = pd.read_csv(tsv_filepath, sep='\t')

            missing_columns: bool = bool(len([column_name for column_name in canspin_annotation_tsv_columns if column_name not in df.columns]))
            missing_data: bool = bool(not len(df.index))
            if missing_columns:
                raise ValueError('The tsv file does not contain all the columns defined in the CANSpiN annotation file schema.')
            if missing_data:
                raise ValueError('The tsv file does not contain any data besides the column names.')
            
            df_without_iob_prefixes_on_tags: pd.DataFrame = df['Tag'].apply(lambda x: x[2:] if x != 'O' else 'O')
            all_tags: np.ndarray = df_without_iob_prefixes_on_tags.unique()
            canspin_tags: np.ndarray = all_tags[all_tags != 'O']
            out_of_schema_tags: bool = bool([tag for tag in canspin_tags if tag not in self.category_and_class_systems[render_settings['category_and_class_system_name']]['classes']])
            if out_of_schema_tags:
                raise ValueError('The tsv file does contain tags which does not belong to the class system selected in the render settings.')

            dataframes.append({tsv_filepath: df})

        # concatinate dataframes, if needed, and return the result dataframe
        return dataframes[0][list(dataframes[0].keys())[0]] if len(dataframes) == 1 else \
                pd.concat([element[list(element.keys())[0]] for element in dataframes]).reset_index(drop=True)

    def test_text_borders(
            self, 
            annotation_collection_index,
            text_borders: Union[Tuple[int, int], None] = None, 
            text_snippet_length: int = 30) -> Union[str, None]:
        """Helper method for finding text_border values for selecting a desired text segment of an original annotation collections text.
        Logs and returns a substring of an annotation collections text. It's beginning and end is defined by text_borders parameter, \
        the length of the text blocks at the beginning and the end is defined by text_snippets_length parameter.

        Args:
            annotation_collection_index (int): Selects the annotation collection by index.
            text_borders (tuple, optional): Specifies the first and the last character index of the selected text inside the original annotation collections text. \
                                            Defaults to None. If no value is provided, the method will use settings von self.default_get_iaa_settings.
            text_snippets_length (int, optional): Specifies the amount of text logged right and left from the defined text_borders. Defaults to 30.

        Returns:
            Str: A substring of an annotation collection text is returned. It's beginning and end is defined by text_borders parameter, \
                 the length of the text blocks at the beginning and the end is defined by text_snippets_length parameter.

        Raises:
            ValueError: Is raised, if a project is loaded, but no annotation collection index is provided.
        """
        if not self.project:
            logger.info('Currently no project is loaded.')
            return
        
        if annotation_collection_index is None:
            raise ValueError('No annotation collection index has been provided.')
        
        text_borders: Union[None, Tuple[int, int]] = self.default_get_iaa_settings['text_borders'] if not text_borders else text_borders

        if text_borders:
            text: str = self.project.annotation_collections[annotation_collection_index].text.plain_text
            text = text[text_borders[0]:text_borders[1]]
            result: str = '"' + ((text[:text_snippet_length] + '...' + text[-abs(text_snippet_length):]) if len(text) >= (text_snippet_length * 2) else text) + '"'
            
            logger.info(result)
            return result
        else:
            logger.info('No text borders were passed to the method or saved in the exporters processing settings.')

    def render_overview_pie_chart(
            self, 
            input_data: Union[pd.DataFrame, List[str]],
            render_overview_pie_chart_settings: Union[dict, None] = None,
            export_filename: str = 'overview_pie_chart_export') -> None:
        """Method for rendering a plotly pie chart as html, refering to the whole data as basic quantity given via the input_tsv parameter.
        Uses the plotly.express.sunburst method and data derived pandas dataframes or tsv files following the CANSpiN annotation file schema.
        Saves the output html in the project_folder/images folder and shows it with plotly's default renderer settings.

        Args:
            input_data (Union[pd.DataFrame, str]): Designed to take a pandas dataframe from the CanspinProject's self.tsv_annotations dict or one or more tsv files.
            render_overview_pie_chart_settings (Union[dict, None], optional): Delivers custom setting for the category and class system used in the visualization. Defaults to default_render_overview_pie_chart_settings.
            export_filename(str): Name of output file with pie chart, which is saved in the project_folder/images folder. Defaults to 'overview_pie_chart_export'.
        """           
        render_settings: dict = self.default_render_overview_pie_chart_settings if not render_overview_pie_chart_settings else render_overview_pie_chart_settings
        tsv_data_df: pd.DataFrame = input_data if isinstance(input_data, pd.DataFrame) else self._load_tsv_files(tsv_filepath_list=input_data, render_settings=render_settings)

        new_df = tsv_data_df[tsv_data_df['Tag'].str.startswith('B')].drop_duplicates(subset=['Annotation_ID'])
        def extract_suffix(value):
            parts = value.split('-')
            if len(parts) > 1:
                return parts[1]
            else:
                return None
        new_df['Tag_categories'] = new_df['Tag'].apply(extract_suffix)

        def extract_suffix_2(value):
            parts = value.split('-', 1)
            if len(parts) > 1:
                return parts[1]
            else:
                return None
        new_df['Tag_classes'] = new_df['Tag'].apply(extract_suffix_2)

        new_df['Anzahl']=1

        df_grouped = new_df.groupby(['Tag_categories', 'Tag_classes']).size().reset_index(name='Anzahl')
        df_grouped = new_df.sort_values(by=['Tag_categories', 'Tag_classes'])

        color_discrete_map = {
            **self.category_and_class_systems[render_settings['category_and_class_system_name']]['categories'],
            **self.category_and_class_systems[render_settings['category_and_class_system_name']]['classes']
        }

        fig = px.sunburst(
            df_grouped, path=['Tag_categories', 'Tag_classes'], 
            values='Anzahl', 
            color='Tag_categories', 
            color_discrete_map=color_discrete_map, 
            custom_data=['Anzahl']) 
        fig.update_traces(
            textinfo="label+percent entry",
            hovertemplate='<b>%{label}</b><br>Anzahl: %{customdata[0]}<br>',
            texttemplate='%{label}: %{customdata[0]}'
        )
        colors = list(fig.data[0]['marker']['colors'])
        for i, path in enumerate(fig.data[0]['ids']):
            if path.split('/')[0] in color_discrete_map:
                colors[i] = color_discrete_map[path.split('/')[0]]
            if path.split('/')[-1] in color_discrete_map:
                colors[i] = color_discrete_map[path.split('/')[-1]]
        fig.data[0]['marker']['colors'] = tuple(colors)
        fig.update_layout(
            width=1500,
            height=1200,
            font=dict(size=20)
        )

        html_str: str = fig.to_html()
        html_filepath_str: str = os.path.join(abs_local_save_path, 'images', f'{export_filename}.html')

        if (os.path.isfile(html_filepath_str)):
            logger.info(f'HTML file {html_filepath_str} already exists and will be overwritten.')

        with open(html_filepath_str, 'w') as file:
            file.write(html_str)
            logger.info(f'HTML file {html_filepath_str} successfully created.')
            
        fig.show()

    # TODO: implement option to define the amount of segments instead of the amount of tokens per segment only
    def render_progression_bar_chart(
            self,
            input_data: Union[pd.DataFrame, List[str]],
            render_progression_bar_chart_settings: Union[dict, None] = None,
            export_filename: Union[str, None] = None) -> None:
        """Method for rendering plotly progression bar, each bar displaying the amount of token per class inside a defined textual window, refering to the whole data as basic quantity given via the input_tsv parameter.
        Uses the plotly.express.bar method and data derived pandas dataframes or tsv files following the CANSpiN annotation file schema.
        Saves the output in the project_folder/images folder or shows it with plotly's default renderer settings.

        Args:
            input_data: Union[pd.DataFrame, List[str]]: Designed to take a pandas dataframe from the CanspinProject's self.tsv_annotations dict or one or more tsv files.
            render_progression_bar_chart_settings(Union[dict, None], optional): Delivers custom settings for data visualization and output. Defaults to self.default_render_progression_bar_chart_settings.
            export_filename(Union[str, None], optional): Name of output file with bar chart, which is saved in the project_folder/images folder, if the output type is set to 'html' or 'svg' in render_settings. Defaults to 'render_progression_bar_chart__{render_settings["separation_unit_amount"]}-{render_settings["separation_unit_type"]}-window'.
        """
        render_settings: dict = self.default_render_progression_bar_chart_settings if not render_progression_bar_chart_settings else render_progression_bar_chart_settings
        export_filename: str = export_filename if export_filename else f'render_progression_bar_chart__{render_settings["separation_unit_amount"]}-{render_settings["separation_unit_type"]}-window'

        tsv_data_df: pd.DataFrame = input_data if isinstance(input_data, pd.DataFrame) else self._load_tsv_files(tsv_filepath_list=input_data, render_settings=render_settings)

        _my_globals: dict = {
            'text_units': [], # List[int]
            'last_text_unit_amount': 0, # int
            'class_instance_counter': {}, # Dict[str, List[int]]
            'class_list': self.category_and_class_systems[render_settings['category_and_class_system_name']]['classes'] # Dict[str, str]
        }

        for classname in list(_my_globals['class_list'].keys()):
            _my_globals['class_instance_counter'][classname] = []

        def _transform_with_token_separation(input: pd.DataFrame, separation_unit_amount: int = render_settings['separation_unit_amount']) -> pd.DataFrame:
            # get count of text units in text and add 0 count times in class_instance_counter for each class
            text_units_count: int = (len(input.index) // separation_unit_amount) + (1 if (len(input.index) % separation_unit_amount != 0) else 0)
            _my_globals['last_text_unit_amount'] = separation_unit_amount if (len(input.index) % separation_unit_amount == 0) else (len(input.index) % separation_unit_amount)

            for key in _my_globals['class_instance_counter']:
                _my_globals['class_instance_counter'][key] = [0] * text_units_count
            
            # saves ids of annotations already counted to handle multi token annotations
            processed_annotations: List[str] = []

            # check all tokens in counting annotations process
            for row_index, row in input.iterrows():
                current_text_unit: int = row_index // separation_unit_amount
                if not current_text_unit in _my_globals['text_units']:
                    _my_globals['text_units'].append(current_text_unit)

                if (row['Tag'].startswith('B-')):
                    if (
                        (row['Multi_Token_Annotation'] == 1) or 
                        ((row['Multi_Token_Annotation'] != 1) and (row['Annotation_ID'] not in processed_annotations))
                    ):
                        classname: str = row['Tag'][2:]
                        _my_globals['class_instance_counter'][classname][current_text_unit] += 1
                        processed_annotations.append(row['Annotation_ID'])

            # create and return output dataframe, translate the classes to English if necessary
            output_df_structure: dict = {'Text_Unit': _my_globals['text_units'], **_my_globals['class_instance_counter']}

            if render_settings['translate_classes_to_english'] and render_settings['category_and_class_system_name'] in key_translation:
                _my_globals['class_list'] = translate_dict(input=_my_globals['class_list'], translation=key_translation[render_settings['category_and_class_system_name']])
                output_df_structure = translate_dict(input=output_df_structure, translation=key_translation[render_settings['category_and_class_system_name']])

            return pd.DataFrame(output_df_structure)

        def _transform_with_sentence_separation(input: pd.DataFrame, separation_unit_amount: int = render_settings['separation_unit_amount']) -> pd.DataFrame:
            for row_index, row in input.iterrows():
                # ! critical TODO: create dataframe with sections defined per sentence
                #
                # transform
                # from:
                # Token_ID | Text_Pointer | Token | Tag | Annotation_ID | Multi_Token_Annotation [6 columns]
                # to:
                # Text_Unit | Ort-Container | Ort-Container-BK | ... [32 columns]
                #
                raise NotImplementedError

            return pd.DataFrame()

        transformation_methods: dict = {
            'token': _transform_with_token_separation,
            'sentence': _transform_with_sentence_separation
        }

        transformed_data_df: pd.DataFrame = transformation_methods[render_settings['separation_unit_type']](tsv_data_df)

        fig: plotly.graph_objects.Figure = px.bar(
            data_frame=transformed_data_df,
            x='Text_Unit',
            y=list(_my_globals['class_list'].keys()),
            color_discrete_map=_my_globals['class_list'],
            title=f'Class instance amount progression (text unit settings: {render_settings["separation_unit_type"]}, {render_settings["separation_unit_amount"]}. last text unit amount: {_my_globals["last_text_unit_amount"]}. output setting: {render_settings["output_type"]}.)' if render_settings['title'] else '',
            width=render_settings['width'],
            height=render_settings['height']
        ).update_layout(xaxis_title='text units', yaxis_title='annotation amount', legend_title='annotation classes', font={'size': render_settings['font_size']})
    
        if render_settings['output_type'] != 'show':
            makedir_if_necessary(os.path.join(abs_local_save_path, 'images'))

        def _show_chart(bar_chart_object: plotly.graph_objects.Figure) -> None:
            logger.info(f'Showing bar chart with separation unit type={render_settings["separation_unit_type"]} and separation unit amount={render_settings["separation_unit_amount"]}. The last text unit contains {_my_globals["last_text_unit_amount"]} {render_settings["separation_unit_type"]}s.')
            bar_chart_object.show()

        def _write_html(bar_chart_object: plotly.graph_objects.Figure) -> None:
            html_str: str = bar_chart_object.to_html()
            html_filepath_str: str = os.path.join(abs_local_save_path, 'images', f'{export_filename}.html')

            if (os.path.isfile(html_filepath_str)):
                logger.info(f'HTML file {html_filepath_str} already exists and will be overwritten.')

            with open(html_filepath_str, 'w') as file:
                file.write(html_str)
                logger.info(f'HTML file {html_filepath_str} successfully created.')

        def _write_svg(bar_chart_object: plotly.graph_objects.Figure, render_engine: str) -> None:
            svg_file_str: str = os.path.join(abs_local_save_path, 'images', f'{export_filename}.svg')

            if (os.path.isfile(svg_file_str)):
                logger.info(f'SVG file {svg_file_str} already exists and will be overwritten.')

            # falls unter Windows 11 die svg-Erzeugung ohne Fehlermeldung nicht zum Abschluss kommt, verwendet als Engine "Orca":
            # write_image(file=svg_file_str, engine='orca'); installiert dafür das Paket "plotly-orca" via conda oder pip
            bar_chart_object.write_image(file=svg_file_str, engine=render_engine)
            logger.info(f'SVG file {svg_file_str} successfully created.')

        output_methods: dict = {
            'show': [_show_chart, {'bar_chart_object': fig}],
            'html': [_write_html, {'bar_chart_object': fig}],
            'svg': [_write_svg, {'bar_chart_object': fig, 'render_engine': render_settings['svg_render_engine']}]
        }

        output_methods[render_settings['output_type']][0](**output_methods[render_settings['output_type']][1])

    def get_iaa(
            self,
            annotation_collections: List[AnnotationCollection],
            get_iaa_settings: Union[dict, None] = None) -> float:
        """Method for calculation of gamma as metric for inter-annotator agreement as float value between 0.0 and 1.0.
        Uses the pygamma-agreement package.

        Args:
            annotation_collections(List[AnnotationCollection]): At least two references to already loaded annotation collections, which belong to the same text, have to be passed here in the list.
            get_iaa_settings(Union[dict, None], optional): Delivers custom settings for gamma calculation. Defaults to self.default_get_iaa_settings.
            
        Returns:
            float: If two annotation collections belonging to the same text are provided, a gamma value is calculated according to the settings delivered in get_iaa_settings or self.get_iaa_settings.

        Raises:
            ValueError: Is raised, when the delivered AnnotationCollection objects are less than two, are not delivered in a list or do not refer to the same text or the same tagset.
        """
        get_iaa_settings: dict = self.default_get_iaa_settings if not get_iaa_settings else get_iaa_settings

        # checks if input_acs argument is list containing at least 2 AnnotationCollection objects
        if type(annotation_collections) is not list or len(annotation_collections) < 2:
            raise ValueError('There are less than two AnnotationCollections delivered to get_iaa method or they are not delivered inside a list.')

        # checks if all delivered AnnotationCollection objects refer to the same text
        first_plain_text_id: str = annotation_collections[0].plain_text_id
        if len([ac for ac in annotation_collections if ac.plain_text_id == first_plain_text_id]) < len(annotation_collections):
            raise ValueError('Not all AnnotationCollections delivered to get_iaa method refer to the same text.')
        
        # check if all delivered Annotation objects refer to the same tagset
        first_tagset_id: str = annotation_collections[0].annotations[0].data['body']['tagset']
        if len([an for ac in annotation_collections for an in ac if an.data['body']['tagset'] != first_tagset_id]):
            raise ValueError('Not all Annotations delivered to get_iaa method refer to the same tagset.')

        # collect all selections in a list
        selection_list: List[tuple] = []
        for ac in annotation_collections:
            for an in ac.annotations:
                selections_in_text_borders: Generator[dict, None, None] = \
                    (
                        item for item in an.data['target']['items'] 
                        if item['selector']['start'] >= get_iaa_settings['text_borders'][0] 
                        and item['selector']['end'] <= get_iaa_settings['text_borders'][1]
                    ) \
                    if get_iaa_settings['text_borders'] \
                    else (item for item in an.data['target']['items'])
                for item in selections_in_text_borders:
                    selection_list.append((ac.name, Segment(item['selector']['start'], item['selector']['end']), an.tag.name))

        # create continuum and add all selections of selection_list to continuum
        continuum = Continuum()
        for selection in selection_list:
            continuum.add(selection[0], selection[1], selection[2])
        
        # application of gamma calculation settings and execution of calculation
        dissim = CombinedCategoricalDissimilarity(alpha=get_iaa_settings['alpha'], beta=get_iaa_settings['beta'], delta_empty=get_iaa_settings['delta_empty'])
        gamma_results = continuum.compute_gamma(dissimilarity=dissim, n_samples=get_iaa_settings['n_samples'], precision_level=get_iaa_settings['precision_level'])

        return gamma_results.gamma
    
    def get_random_middle_chapter(self, xml_file: str) -> np.str_:
            """
            Method for randomly selecting a middle chapter of an XML file following the CANSpiN XML scheme. 
            Each chapter is wrapped in a <div> element with a type attribute of "chapter" and might by part of higher hierachy <div> containers.
            The function will extract all chapter <head> tags, split them into three sections,
            and randomly select a chapter from the middle section. The result is a string representation
            of the chapter's head section. It is returned and logged.

            Args:
                xml_file (str): Path to the XML file containing the text structure in string format
                                (e.g. "c:/Users/CANSpiN/CANSpiN-lat-19-004.xml" or relative paths).

            Returns:
                np.str_: The heading (Title and/or chapter) of a randomly selected chapter from the middle 
                    section of the XML file. 
                    
            Raises:
                FileNotFoundError: If the XML file does not exist.
                ValueError: If the XML file has no .xml ending,
                            does not contain any <div> elements with type="chapter",
                            does not contain any <head> tags,
                            does contain less than 3 valid chapters.
            """

            # Handling to verify the file provided
            if not os.path.exists(xml_file):
                raise FileNotFoundError(f"File {xml_file} does not exist.")
            elif not xml_file.endswith('.xml'):
                raise ValueError(f"The file {xml_file} has no XML file ending. Please provide a valid XML file path.")

            # Extract chapter heads from the XML file
            def extract_head_from_chapters(xml_file: str) -> List[str]:
                with open(xml_file, 'r', encoding='utf-8') as file:
                    xml_content: str = file.read()

                # Parse the XML content
                parsed_xml_text: bs4.BeautifulSoup = bs4.BeautifulSoup(xml_content, 'xml')

                # Find all <div> elements with type="chapter" and check if any exist
                text_chapters: bs4.element.ResultSet[bs4.PageElement] = parsed_xml_text.find_all('div', {'type': 'chapter'})
                if not text_chapters:
                    raise ValueError(f"The file {xml_file} does not contain any <div> elements with type='chapter'. Please provide a correct formatted xml following the CANSpiN scheme.")

                # Initialize an empty list to store the heads data
                heads_content: List[str] = []

                # Loop through each chapter div and find the <head> tags
                for chapter in text_chapters:
                    head_tags: str = ''
                    
                    heads_in_chapter: bs4.element.ResultSet[bs4.PageElement] = chapter.find_all('head')

                    # If multiple <head> tags, merge their values
                    for head in heads_in_chapter:
                        head_tags += head.get_text().strip() + " "
                    
                    # Strip whitespace, add merged text to heads_content list, if it more than an empty string
                    if len(head_tags):
                        heads_content.append(head_tags.strip())

                # Verify if enough <head> content exists in file    
                if not heads_content:
                    raise ValueError(f"The file {xml_file} does not contain any head tags inside the chapters. Please provide a correct formatted xml following the CANSpiN scheme.")

                if len(heads_content) < 3:
                    raise ValueError(f"The file {xml_file} only contains {len(heads_content)} valid chapter{'s' if len(heads_content) > 1 else ''}. This is not sufficient for the selection of a middle chapter.")

                return heads_content

            # Split a list into three parts
            def split_list(list_data: list) -> List[np.ndarray[np.str_]]:
                return np.array_split(list_data, 3)

            # Pick a random chapter from the middle list
            def random_from_list(middle_chapters_list: np.ndarray[np.str_]) -> np.str_:
                return random.choice(middle_chapters_list)

            # Extract chapter heads
            heads_content: List[str] = extract_head_from_chapters(xml_file)

            # Split the list into three parts
            beginning_chapters_list, middle_chapters_list, ending_chapters_list = split_list(heads_content)

            # Get the random chapter from the middle_chapters_list
            random_chapter: Union[np.str_, str] = random_from_list(middle_chapters_list)
            logger.info(f"The randomly selected chapter for the middle section is: '{random_chapter}' (selected out of {len(middle_chapters_list)} possible middle chapter{'s' if len(middle_chapters_list) > 1 else ''}).")
            return random_chapter
        
    # TODO: add sorting in results of get_amount_of_annotations, get_amount_of_token, and get_amount_of_annotated_token
    # TODO: bundle subfunctions to reduce code redundancy
    # TODO: add result class with different output methods (move visualization methods into this class?)
    # TODO: add lexicological statistics (most frequent lemmata (vs. words) per annotation class, relations to semantic fields)
    # TODO: add cooccurence statistics for annotations (the instances of which annotation classes occur most frequently nearby together)
    # TODO: add annotation density value by calculating the average annotation amount per 100 (?) token to _get_ratios subfunction for chapters and corpuses, in total and by class
    def get_corpus_annotation_statistics(
            self, 
            get_corpus_annotation_statistics_settings: Union[dict, None] = None,
            safe_result_to_file: Union[str, None] = None) -> dict:
        """docstring
        """
        get_corpus_annotation_statistics_settings: dict = self.default_get_corpus_annotation_statistics_settings if not get_corpus_annotation_statistics_settings else get_corpus_annotation_statistics_settings
        
        #TODO: add checks for get_corpus_annotation_statistics_settings structure and values
        #TODO: if done, add tests for this checks in test_analyser.py

        def _get_df_with_text_borders(input: pd.DataFrame, text_borders: Union[Tuple[int, int], None]) -> pd.DataFrame:
            """Helper function to return a complete or a part of a dataframe derived from a canspin annotation tsv.
            If the passed text_borders values do not fit the length of input, they are silently corrected to "0" and/or len(input.index).

            Args:
                input (pd.DataFrame): a dataframe derived from a canspin annotation tsv file.
                text_borders (Union[Tuple[int, int], None]): a tuple that defines the first (inclusive) and the last (exclusive) token
                                                             to be selected from the input dataframe.

            Returns:
                pd.DataFrame: the input dataframe or a selected part of it as new dataframe.
            """
            if not text_borders:
                return input
            
            input_length: int = len(input.index)
            start_value: Union[int, None] = text_borders[0] if (text_borders[0] >= 0 and text_borders[0] < input_length) else 0
            end_value: Union[int, None] = text_borders[1] if (text_borders[1] > start_value and text_borders[1] < input_length) else input_length

            return input[start_value:end_value]


        def get_amount_of_annotations() -> dict:
            result = dict(amount_of_annotations={})
            custom_grouping: Union[dict, None] = get_corpus_annotation_statistics_settings['custom_grouping']
            text_borders: Union[Tuple[int, int], None] = get_corpus_annotation_statistics_settings['text_borders']

            # execute amount of annotations calculation with custom groups
            if custom_grouping:
                # create list of tuples for calculation:
                # tsv_annotations_dict: save every filename tuple (schema, filename) together with its groups and possible subgroups
                #                       combinations in a list of tuples of [(group, subgroup), (group)]
                #                       in this tsv_annotations_dict ({(schema, filename): [(group, subgroup), (group)]})
                # group_list: save every unique combination of schema, group and possible subgroup as nested tuple (schema, (group, subgroup)) in a list
                tsv_annotations_dict: Dict[Tuple[str, str], List[Tuple[str, Union[str, None]]]] = {}
                for group in custom_grouping:
                    if isinstance(custom_grouping[group], dict):
                        for subgroup in custom_grouping[group]:
                            for file_tuple in custom_grouping[group][subgroup]:
                                tsv_annotations_dict[file_tuple] = tsv_annotations_dict[file_tuple] + [(group, subgroup)] \
                                if file_tuple in tsv_annotations_dict and isinstance(tsv_annotations_dict[file_tuple], list) \
                                else [(group, subgroup)]
                        continue
                    for file_tuple in custom_grouping[group]:
                        tsv_annotations_dict[file_tuple] = tsv_annotations_dict[file_tuple] + [(group,)] \
                        if file_tuple in tsv_annotations_dict and isinstance(tsv_annotations_dict[file_tuple], list) \
                        else [(group,)]
                group_list: List[Tuple[str, Tuple[str, Union[str, None]]]] = []
                for group in custom_grouping:
                    if isinstance(custom_grouping[group], dict):
                        for subgroup in custom_grouping[group]:
                            schemes_in_subgroup: List[str] = list(set([file_tuple[0] for file_tuple in custom_grouping[group][subgroup]]))
                            for schema in schemes_in_subgroup:
                                group_list.append((schema, (group, subgroup)))
                        continue
                    schemes_in_group: List[str] = list(set([file_tuple[0] for file_tuple in custom_grouping[group]]))
                    for schema in schemes_in_group:
                        group_list.append((schema, (group,)))
                group_list = list(set(group_list))
                                
                # build result dict structure for amount_of_annotations
                for schema in list(set([schema for schema, _ in group_list])):
                    result['amount_of_annotations'][schema] = dict()
                for group_tuple in group_list:
                    if len(group_tuple[1]) == 1:
                        result['amount_of_annotations'][group_tuple[0]][group_tuple[1][0]] = dict()
                    elif len(group_tuple[1]) == 2:
                        if group_tuple[1][0] not in result['amount_of_annotations'][group_tuple[0]]:
                            result['amount_of_annotations'][group_tuple[0]][group_tuple[1][0]] = dict()
                        result['amount_of_annotations'][group_tuple[0]][group_tuple[1][0]][group_tuple[1][1]] = dict()

                # fill result dict with amount_of_annotations values by filename
                for file_tuple, file_tuple_groups in tsv_annotations_dict.items():
                    file_df: pd.DataFrame = _get_df_with_text_borders(self.tsv_annotations[file_tuple[0]][file_tuple[1]], text_borders)
                    filtered_df_with_annotations: pd.DataFrame = file_df[file_df['Tag'].str.startswith('B-')].drop_duplicates(subset=['Annotation_ID'])
                    for file_tuple_group in file_tuple_groups:
                        if len(file_tuple_group) == 1:
                            result['amount_of_annotations'][file_tuple[0]][file_tuple_group[0]][file_tuple[1]] = len(filtered_df_with_annotations.index)
                        elif len(file_tuple_group) == 2:
                            result['amount_of_annotations'][file_tuple[0]][file_tuple_group[0]][file_tuple_group[1]][file_tuple[1]] = len(filtered_df_with_annotations.index)

                # calculate sums by groups and possible subgroups
                for schema, grouping in group_list:
                    if len(grouping) == 1:
                        result['amount_of_annotations'][schema][grouping[0]]['TOTAL'] = sum(result['amount_of_annotations'][schema][grouping[0]].values())
                    elif len(grouping) == 2:
                        result['amount_of_annotations'][schema][grouping[0]][grouping[1]]['TOTAL'] = sum(result['amount_of_annotations'][schema][grouping[0]][grouping[1]].values())
                        result['amount_of_annotations'][schema][grouping[0]]['TOTAL'] = sum(
                            [
                                result['amount_of_annotations'][schema][grouping[0]][subgroup].get('TOTAL', 0) \
                                for subgroup in result['amount_of_annotations'][schema][grouping[0]] \
                                if isinstance(result['amount_of_annotations'][schema][grouping[0]][subgroup], dict)
                            ]
                        )

                # calculate sums by schema
                for schema in result['amount_of_annotations']:
                    result['amount_of_annotations'][schema]['TOTAL'] = sum([result['amount_of_annotations'][schema][group]['TOTAL'] for group in result['amount_of_annotations'][schema]])

            # execute amount of annotations calculation with default groups by annotation schema and corpus
            else:
                # extract lists of tuples for calculation out of self.tsv_annotations dict:
                # tsv_annotations_list: save every filename together with its corpus and schema in tuples of (schema, corpus, filename)
                # corpus_list: save every unique combination of schema and corpus in tuples of (schema, corpus)
                tsv_annotations_list: List[Tuple[str, str, str]] = [(schema, filename.split('_')[0].lower(), filename) for schema in self.tsv_annotations for filename in self.tsv_annotations[schema]]
                corpus_list: List[Tuple[str, str]] = list(set([(tsv_annotation[0], tsv_annotation[1]) for tsv_annotation in tsv_annotations_list]))

                # build result dict structure for amount_of_annotations
                for schema in self.tsv_annotations:
                    result['amount_of_annotations'][schema] = dict()
                for schema, corpus in corpus_list:
                    result['amount_of_annotations'][schema][corpus] = dict()

                # fill result dict with amount_of_annotations values by filename
                for schema, corpus, filename in tsv_annotations_list:
                    file_df: pd.DataFrame = _get_df_with_text_borders(self.tsv_annotations[schema][filename], text_borders)
                    filtered_df_with_annotations: pd.DataFrame = file_df[file_df['Tag'].str.startswith('B-')].drop_duplicates(subset=['Annotation_ID'])
                    result['amount_of_annotations'][schema][corpus][filename] = len(filtered_df_with_annotations.index)

                # calculate sums by corpus
                for schema, corpus in corpus_list:
                    result['amount_of_annotations'][schema][corpus]['TOTAL'] = sum(result['amount_of_annotations'][schema][corpus].values())

                # calculate sums by schema
                for schema in result['amount_of_annotations']:
                    result['amount_of_annotations'][schema]['TOTAL'] = sum([result['amount_of_annotations'][schema][corpus]['TOTAL'] for corpus in result['amount_of_annotations'][schema]])

            return result

        def get_amount_of_annotations_by_class() -> dict:
            result = dict(amount_of_annotations_by_class={})
            custom_grouping: Union[dict, None] = get_corpus_annotation_statistics_settings['custom_grouping']
            text_borders: Union[Tuple[int, int], None] = get_corpus_annotation_statistics_settings['text_borders']

            # execute amount of annotations by class calculation with custom groups
            if custom_grouping:
                # create list of tuples for calculation:
                # tsv_annotations_dict: save every filename tuple (schema, filename) together with its groups and possible subgroups
                #                       combinations in a list of tuples of [(group, subgroup), (group)]
                #                       in this tsv_annotations_dict ({(schema, filename): [(group, subgroup), (group)]})
                # group_list: save every unique combination of schema, group and possible subgroup as nested tuple (schema, (group, subgroup)) in a list
                tsv_annotations_dict: Dict[Tuple[str, str], List[Tuple[str, Union[str, None]]]] = {}
                for group in custom_grouping:
                    if isinstance(custom_grouping[group], dict):
                        for subgroup in custom_grouping[group]:
                            for file_tuple in custom_grouping[group][subgroup]:
                                tsv_annotations_dict[file_tuple] = tsv_annotations_dict[file_tuple] + [(group, subgroup)] \
                                if file_tuple in tsv_annotations_dict and isinstance(tsv_annotations_dict[file_tuple], list) \
                                else [(group, subgroup)]
                        continue
                    for file_tuple in custom_grouping[group]:
                        tsv_annotations_dict[file_tuple] = tsv_annotations_dict[file_tuple] + [(group,)] \
                        if file_tuple in tsv_annotations_dict and isinstance(tsv_annotations_dict[file_tuple], list) \
                        else [(group,)]
                group_list: List[Tuple[str, Tuple[str, Union[str, None]]]] = []
                for group in custom_grouping:
                    if isinstance(custom_grouping[group], dict):
                        for subgroup in custom_grouping[group]:
                            schemes_in_subgroup: List[str] = list(set([file_tuple[0] for file_tuple in custom_grouping[group][subgroup]]))
                            for schema in schemes_in_subgroup:
                                group_list.append((schema, (group, subgroup)))
                        continue
                    schemes_in_group: List[str] = list(set([file_tuple[0] for file_tuple in custom_grouping[group]]))
                    for schema in schemes_in_group:
                        group_list.append((schema, (group,)))
                group_list = list(set(group_list))

                # build result dict structure for amount_of_annotations_by_class
                for schema in list(set([schema for schema, _ in group_list])):
                    result['amount_of_annotations_by_class'][schema] = dict()
                for group_tuple in group_list:
                    if len(group_tuple[1]) == 1:
                        result['amount_of_annotations_by_class'][group_tuple[0]][group_tuple[1][0]] = dict()
                    elif len(group_tuple[1]) == 2:
                        if group_tuple[1][0] not in result['amount_of_annotations_by_class'][group_tuple[0]]:
                            result['amount_of_annotations_by_class'][group_tuple[0]][group_tuple[1][0]] = dict()
                        result['amount_of_annotations_by_class'][group_tuple[0]][group_tuple[1][0]][group_tuple[1][1]] = dict()

                # fill result dict with amount_of_annotations_by_class values by filename:
                for file_tuple, file_tuple_groups in tsv_annotations_dict.items():
                    # filter the token dataframe for annotations, get a dataframe copy without iob prefixes in Tags column and transform the dataframe into a dict of occurences in the Tag column
                    file_df: pd.DataFrame = _get_df_with_text_borders(self.tsv_annotations[file_tuple[0]][file_tuple[1]], text_borders)
                    filtered_df: pd.DataFrame = file_df[file_df['Tag'].str.startswith('B-')].drop_duplicates(subset=['Annotation_ID'])
                    filtered_df_without_iob_schema: pd.Series = filtered_df.Tag.replace({r'^[BI]-': r''}, regex=True)
                    file_summary: dict = filtered_df_without_iob_schema.value_counts().to_dict()

                    # add missing classes of the schema to the file_summary dict, if the schema is known and no instances of the respective classes exist in the dataframe
                    if file_tuple[0] in canspin_annotation_schema_mapping:
                        # determine current class system name by language, with help of canspin_annotation_schema_mapping
                        corpus = file_tuple[1].split('_')[0].lower()

                        # TODO: undo hardcoding and build language recognition based on configuration files
                        current_language: Union[str, None] = 'deu' if corpus.split('-')[1] == 'deu' else \
                                                             ('spa' if corpus.split('-')[1] in ['spa', 'lat'] else None)

                        if not current_language:
                            logger.info(f'The language of {file_tuple[1]} (in schema {file_tuple[0]}) could not be determined. Skipping the addition of classes with missing instances for this file..')
                            for file_tuple_group in file_tuple_groups:
                                if len(file_tuple_group) == 1:
                                    result['amount_of_annotations_by_class'][file_tuple[0]][file_tuple_group[0]][file_tuple[1]] = file_summary
                                elif len(file_tuple_group) == 2:
                                    result['amount_of_annotations_by_class'][file_tuple[0]][file_tuple_group[0]][file_tuple_group[1]][file_tuple[1]] = file_summary
                            continue

                        current_category_and_class_system_name: Union[str, None] = next(
                            (category_and_class_system_name for category_and_class_system_name in self.category_and_class_systems \
                            if current_language in self.category_and_class_systems[category_and_class_system_name]['languages'] \
                            and category_and_class_system_name in canspin_annotation_schema_mapping[file_tuple[0]]),
                            None
                        )

                        if not current_category_and_class_system_name:
                            logger.info(f'The category and class system name of {file_tuple[1]} (in schema {file_tuple[0]}) could not be determined. Skipping the addition of classes with missing instances for this file..')
                            for file_tuple_group in file_tuple_groups:
                                if len(file_tuple_group) == 1:
                                    result['amount_of_annotations_by_class'][file_tuple[0]][file_tuple_group[0]][file_tuple[1]] = file_summary
                                elif len(file_tuple_group) == 2:
                                    result['amount_of_annotations_by_class'][file_tuple[0]][file_tuple_group[0]][file_tuple_group[1]][file_tuple[1]] = file_summary
                            continue

                        for classname in self.category_and_class_systems[current_category_and_class_system_name]['classes']:
                            if classname not in file_summary:
                                file_summary[classname] = 0

                    for file_tuple_group in file_tuple_groups:
                        if len(file_tuple_group) == 1:
                            result['amount_of_annotations_by_class'][file_tuple[0]][file_tuple_group[0]][file_tuple[1]] = file_summary
                        elif len(file_tuple_group) == 2:
                            result['amount_of_annotations_by_class'][file_tuple[0]][file_tuple_group[0]][file_tuple_group[1]][file_tuple[1]] = file_summary

                # calculate sums by groups and possible subgroups
                # TODO: transform into dict comprehensions
                for schema, grouping in group_list:
                    if len(grouping) == 1:
                        sum_dict_by_group = {}
                        for filename in result['amount_of_annotations_by_class'][schema][grouping[0]]:
                            for classname in result['amount_of_annotations_by_class'][schema][grouping[0]][filename]:
                                if classname not in sum_dict_by_group:
                                    sum_dict_by_group[classname] = 0
                                sum_dict_by_group[classname] += result['amount_of_annotations_by_class'][schema][grouping[0]][filename][classname]
                        result['amount_of_annotations_by_class'][schema][grouping[0]]['TOTAL'] = sum_dict_by_group
                    elif len(grouping) == 2:
                        sum_dict_by_subgroup = {}
                        for filename in result['amount_of_annotations_by_class'][schema][grouping[0]][grouping[1]]:
                            for classname in result['amount_of_annotations_by_class'][schema][grouping[0]][grouping[1]][filename]:
                                if classname not in sum_dict_by_subgroup:
                                    sum_dict_by_subgroup[classname] = 0
                                sum_dict_by_subgroup[classname] += result['amount_of_annotations_by_class'][schema][grouping[0]][grouping[1]][filename][classname]
                        result['amount_of_annotations_by_class'][schema][grouping[0]][grouping[1]]['TOTAL'] = sum_dict_by_subgroup
                        sum_dict_by_group = {}
                        for subgroup in result['amount_of_annotations_by_class'][schema][grouping[0]]:
                            if subgroup == 'TOTAL' or 'TOTAL' not in result['amount_of_annotations_by_class'][schema][grouping[0]][subgroup]:
                                continue
                            for classname in result['amount_of_annotations_by_class'][schema][grouping[0]][subgroup]['TOTAL']:
                                if classname not in sum_dict_by_group:
                                    sum_dict_by_group[classname] = 0
                                sum_dict_by_group[classname] += result['amount_of_annotations_by_class'][schema][grouping[0]][subgroup]['TOTAL'][classname]
                        result['amount_of_annotations_by_class'][schema][grouping[0]]['TOTAL'] = sum_dict_by_group

                # calculate sums by schema
                # TODO: transform into dict comprehension
                for schema in result['amount_of_annotations_by_class']:
                    sum_dict_by_schema = {}
                    for group in result['amount_of_annotations_by_class'][schema]:
                        for classname in result['amount_of_annotations_by_class'][schema][group]['TOTAL']:
                            if classname not in sum_dict_by_schema:
                                sum_dict_by_schema[classname] = 0
                            sum_dict_by_schema[classname] += result['amount_of_annotations_by_class'][schema][group]['TOTAL'][classname]
                    result['amount_of_annotations_by_class'][schema]['TOTAL'] = sum_dict_by_schema

            # execute amount of annotations by class calculation with default groups by annotation schema and corpus
            else:
                # extract lists of tuples for calculation out of self.tsv_annotations dict:
                # tsv_annotations_list: save every filename together with its corpus and schema in tuples of (schema, corpus, filename)
                # corpus_list: save every unique combination of schema and corpus in tuples of (schema, corpus)
                tsv_annotations_list: List[Tuple[str, str, str]] = [(schema, filename.split('_')[0].lower(), filename) for schema in self.tsv_annotations for filename in self.tsv_annotations[schema]]
                corpus_list: List[Tuple[str, str]] = list(set([(tsv_annotation[0], tsv_annotation[1]) for tsv_annotation in tsv_annotations_list]))

                # build result dict structure for amount_of_annotations_by_class
                for schema in self.tsv_annotations:
                    result['amount_of_annotations_by_class'][schema] = dict()
                for schema, corpus in corpus_list:
                    result['amount_of_annotations_by_class'][schema][corpus] = dict()

                # fill result dict with amount_of_annotations_by_class values by filename:
                for schema, corpus, filename in tsv_annotations_list:
                    # filter the token dataframe for annotations, get a dataframe copy without iob prefixes in Tags column and transform the dataframe into a dict of occurences in the Tag column
                    file_df: pd.DataFrame = _get_df_with_text_borders(self.tsv_annotations[schema][filename], text_borders)
                    filtered_df: pd.DataFrame = file_df[file_df['Tag'].str.startswith('B-')].drop_duplicates(subset=['Annotation_ID'])
                    filtered_df_without_iob_schema: pd.Series = filtered_df.Tag.replace({r'^[BI]-': r''}, regex=True)
                    file_summary: dict = filtered_df_without_iob_schema.value_counts().to_dict()

                    # add missing classes of the schema to the file_summary dict, if the schema is known and no instances of the respective classes exist in the dataframe
                    if schema in canspin_annotation_schema_mapping:
                        # determine current class system name by language, with help of canspin_annotation_schema_mapping
                        # TODO: undo hardcoding and build language recognition based on configuration files
                        current_language: Union[str, None] = 'deu' if corpus.split('-')[1] == 'deu' else \
                                                             ('spa' if corpus.split('-')[1] in ['spa', 'lat'] else None)

                        if not current_language:
                            logger.info(f'The language of {filename} (in schema {schema}) could not be determined. Skipping the addition of classes with missing instances for this file..')
                            result['amount_of_annotations_by_class'][schema][corpus][filename] = file_summary
                            continue

                        current_category_and_class_system_name: Union[str, None] = next(
                            (category_and_class_system_name for category_and_class_system_name in self.category_and_class_systems \
                            if current_language in self.category_and_class_systems[category_and_class_system_name]['languages'] \
                            and category_and_class_system_name in canspin_annotation_schema_mapping[schema]),
                            None
                        )

                        if not current_category_and_class_system_name:
                            logger.info(f'The category and class system name of {filename} (in schema {schema}) could not be determined. Skipping the addition of classes with missing instances for this file..')
                            result['amount_of_annotations_by_class'][schema][corpus][filename] = file_summary
                            continue

                        for classname in self.category_and_class_systems[current_category_and_class_system_name]['classes']:
                            if classname not in file_summary:
                                file_summary[classname] = 0

                    result['amount_of_annotations_by_class'][schema][corpus][filename] = file_summary

                # calculate sums by corpus
                # TODO: transform into dict comprehension
                for schema, corpus in corpus_list:
                    sum_dict_by_corpus = {}
                    for filename in result['amount_of_annotations_by_class'][schema][corpus]:
                        for classname in result['amount_of_annotations_by_class'][schema][corpus][filename]:
                            if classname not in sum_dict_by_corpus:
                                sum_dict_by_corpus[classname] = 0
                            sum_dict_by_corpus[classname] += result['amount_of_annotations_by_class'][schema][corpus][filename][classname]
                    result['amount_of_annotations_by_class'][schema][corpus]['TOTAL'] = sum_dict_by_corpus

                # calculate sums by schema
                # TODO: transform into dict comprehension
                for schema in result['amount_of_annotations_by_class']:
                    sum_dict_by_schema = {}
                    for corpus in result['amount_of_annotations_by_class'][schema]:
                        for classname in result['amount_of_annotations_by_class'][schema][corpus]['TOTAL']:
                            if classname not in sum_dict_by_schema:
                                sum_dict_by_schema[classname] = 0
                            sum_dict_by_schema[classname] += result['amount_of_annotations_by_class'][schema][corpus]['TOTAL'][classname]
                    result['amount_of_annotations_by_class'][schema]['TOTAL'] = sum_dict_by_schema

            return result

        def get_amount_of_token() -> dict:
            result = dict(amount_of_token={})
            custom_grouping: Union[dict, None] = get_corpus_annotation_statistics_settings['custom_grouping']
            text_borders: Union[Tuple[int, int], None] = get_corpus_annotation_statistics_settings['text_borders']

            # execute amount of token calculation with custom groups
            if custom_grouping:
                # create list of tuples for calculation:
                # tsv_annotations_dict: save every filename tuple (schema, filename) together with its groups and possible subgroups
                #                       combinations in a list of tuples of [(group, subgroup), (group)]
                #                       in this tsv_annotations_dict ({(schema, filename): [(group, subgroup), (group)]})
                # group_list: save every unique combination of schema, group and possible subgroup as nested tuple (schema, (group, subgroup)) in a list
                tsv_annotations_dict: Dict[Tuple[str, str], List[Tuple[str, Union[str, None]]]] = {}
                for group in custom_grouping:
                    if isinstance(custom_grouping[group], dict):
                        for subgroup in custom_grouping[group]:
                            for file_tuple in custom_grouping[group][subgroup]:
                                tsv_annotations_dict[file_tuple] = tsv_annotations_dict[file_tuple] + [(group, subgroup)] \
                                if file_tuple in tsv_annotations_dict and isinstance(tsv_annotations_dict[file_tuple], list) \
                                else [(group, subgroup)]
                        continue
                    for file_tuple in custom_grouping[group]:
                        tsv_annotations_dict[file_tuple] = tsv_annotations_dict[file_tuple] + [(group,)] \
                        if file_tuple in tsv_annotations_dict and isinstance(tsv_annotations_dict[file_tuple], list) \
                        else [(group,)]
                group_list: List[Tuple[str, Tuple[str, Union[str, None]]]] = []
                for group in custom_grouping:
                    if isinstance(custom_grouping[group], dict):
                        for subgroup in custom_grouping[group]:
                            schemes_in_subgroup: List[str] = list(set([file_tuple[0] for file_tuple in custom_grouping[group][subgroup]]))
                            for schema in schemes_in_subgroup:
                                group_list.append((schema, (group, subgroup)))
                        continue
                    schemes_in_group: List[str] = list(set([file_tuple[0] for file_tuple in custom_grouping[group]]))
                    for schema in schemes_in_group:
                        group_list.append((schema, (group,)))
                group_list = list(set(group_list))

                # build result dict structure for amount_of_token
                for schema in list(set([schema for schema, _ in group_list])):
                    result['amount_of_token'][schema] = dict()
                for group_tuple in group_list:
                    if len(group_tuple[1]) == 1:
                        result['amount_of_token'][group_tuple[0]][group_tuple[1][0]] = dict()
                    elif len(group_tuple[1]) == 2:
                        if group_tuple[1][0] not in result['amount_of_token'][group_tuple[0]]:
                            result['amount_of_token'][group_tuple[0]][group_tuple[1][0]] = dict()
                        result['amount_of_token'][group_tuple[0]][group_tuple[1][0]][group_tuple[1][1]] = dict()

                # fill result dict with amount_of_token values by filename
                for file_tuple, file_tuple_groups in tsv_annotations_dict.items():
                    file_df: pd.DataFrame = _get_df_with_text_borders(self.tsv_annotations[file_tuple[0]][file_tuple[1]], text_borders)
                    for file_tuple_group in file_tuple_groups:
                        if len(file_tuple_group) == 1:
                            result['amount_of_token'][file_tuple[0]][file_tuple_group[0]][file_tuple[1]] = len(file_df.index)
                        elif len(file_tuple_group) == 2:
                            result['amount_of_token'][file_tuple[0]][file_tuple_group[0]][file_tuple_group[1]][file_tuple[1]] = len(file_df.index)

                # calculate sums by groups and possible subgroups
                for schema, grouping in group_list:
                    if len(grouping) == 1:
                        result['amount_of_token'][schema][grouping[0]]['TOTAL'] = sum(result['amount_of_token'][schema][grouping[0]].values())
                    elif len(grouping) == 2:
                        result['amount_of_token'][schema][grouping[0]][grouping[1]]['TOTAL'] = sum(result['amount_of_token'][schema][grouping[0]][grouping[1]].values())
                        result['amount_of_token'][schema][grouping[0]]['TOTAL'] = sum(
                            [
                                result['amount_of_token'][schema][grouping[0]][subgroup].get('TOTAL', 0) \
                                for subgroup in result['amount_of_token'][schema][grouping[0]] \
                                if isinstance(result['amount_of_token'][schema][grouping[0]][subgroup], dict)
                            ]
                        )

                # calculate sums by schema
                for schema in result['amount_of_token']:
                    result['amount_of_token'][schema]['TOTAL'] = sum([result['amount_of_token'][schema][group]['TOTAL'] for group in result['amount_of_token'][schema]])

            # execute amount of token calculation with default groups by annotation schema and corpus
            else:
                # extract lists of tuples for calculation out of self.tsv_annotations dict:
                # tsv_annotations_list: save every filename together with its corpus and schema in tuples of (schema, corpus, filename)
                # corpus_list: save every unique combination of schema and corpus in tuples of (schema, corpus)
                tsv_annotations_list: List[Tuple[str, str, str]] = [(schema, filename.split('_')[0].lower(), filename) for schema in self.tsv_annotations for filename in self.tsv_annotations[schema]]
                corpus_list: List[Tuple[str, str]] = list(set([(tsv_annotation[0], tsv_annotation[1]) for tsv_annotation in tsv_annotations_list]))

                # build result dict structure for amount_of_token
                for schema in self.tsv_annotations:
                    result['amount_of_token'][schema] = dict()
                for schema, corpus in corpus_list:
                    result['amount_of_token'][schema][corpus] = dict()

                # fill result dict with amount_of_token values by filename
                for schema, corpus, filename in tsv_annotations_list:
                    file_df: pd.DataFrame = _get_df_with_text_borders(self.tsv_annotations[schema][filename], text_borders)
                    result['amount_of_token'][schema][corpus][filename] = len(file_df.index)

                # calculate sums by corpus
                for schema, corpus in corpus_list:
                    result['amount_of_token'][schema][corpus]['TOTAL'] = sum(result['amount_of_token'][schema][corpus].values())

                # calculate sums by schema
                for schema in result['amount_of_token']:
                    result['amount_of_token'][schema]['TOTAL'] = sum([result['amount_of_token'][schema][corpus]['TOTAL'] for corpus in result['amount_of_token'][schema]])
                
            return result

        def get_amount_of_annotated_token() -> dict:
            result = dict(amount_of_annotated_token={})
            custom_grouping: Union[dict, None] = get_corpus_annotation_statistics_settings['custom_grouping']
            text_borders: Union[Tuple[int, int], None] = get_corpus_annotation_statistics_settings['text_borders']

            # execute amount of annotated token calculation with custom groups
            if custom_grouping:
                # create list of tuples for calculation:
                # tsv_annotations_dict: save every filename tuple (schema, filename) together with its groups and possible subgroups
                #                       combinations in a list of tuples of [(group, subgroup), (group)]
                #                       in this tsv_annotations_dict ({(schema, filename): [(group, subgroup), (group)]})
                # group_list: save every unique combination of schema, group and possible subgroup as nested tuple (schema, (group, subgroup)) in a list
                tsv_annotations_dict: Dict[Tuple[str, str], List[Tuple[str, Union[str, None]]]] = {}
                for group in custom_grouping:
                    if isinstance(custom_grouping[group], dict):
                        for subgroup in custom_grouping[group]:
                            for file_tuple in custom_grouping[group][subgroup]:
                                tsv_annotations_dict[file_tuple] = tsv_annotations_dict[file_tuple] + [(group, subgroup)] \
                                if file_tuple in tsv_annotations_dict and isinstance(tsv_annotations_dict[file_tuple], list) \
                                else [(group, subgroup)]
                        continue
                    for file_tuple in custom_grouping[group]:
                        tsv_annotations_dict[file_tuple] = tsv_annotations_dict[file_tuple] + [(group,)] \
                        if file_tuple in tsv_annotations_dict and isinstance(tsv_annotations_dict[file_tuple], list) \
                        else [(group,)]
                group_list: List[Tuple[str, Tuple[str, Union[str, None]]]] = []
                for group in custom_grouping:
                    if isinstance(custom_grouping[group], dict):
                        for subgroup in custom_grouping[group]:
                            schemes_in_subgroup: List[str] = list(set([file_tuple[0] for file_tuple in custom_grouping[group][subgroup]]))
                            for schema in schemes_in_subgroup:
                                group_list.append((schema, (group, subgroup)))
                        continue
                    schemes_in_group: List[str] = list(set([file_tuple[0] for file_tuple in custom_grouping[group]]))
                    for schema in schemes_in_group:
                        group_list.append((schema, (group,)))
                group_list = list(set(group_list))

                # build result dict structure for amount_of_annotated_token
                for schema in list(set([schema for schema, _ in group_list])):
                    result['amount_of_annotated_token'][schema] = dict()
                for group_tuple in group_list:
                    if len(group_tuple[1]) == 1:
                        result['amount_of_annotated_token'][group_tuple[0]][group_tuple[1][0]] = dict()
                    elif len(group_tuple[1]) == 2:
                        if group_tuple[1][0] not in result['amount_of_annotated_token'][group_tuple[0]]:
                            result['amount_of_annotated_token'][group_tuple[0]][group_tuple[1][0]] = dict()
                        result['amount_of_annotated_token'][group_tuple[0]][group_tuple[1][0]][group_tuple[1][1]] = dict()

                # fill result dict with amount_of_annotated_token values by filename
                for file_tuple, file_tuple_groups in tsv_annotations_dict.items():
                    file_df: pd.DataFrame = _get_df_with_text_borders(self.tsv_annotations[file_tuple[0]][file_tuple[1]], text_borders)
                    for file_tuple_group in file_tuple_groups:
                        if len(file_tuple_group) == 1:
                            result['amount_of_annotated_token'][file_tuple[0]][file_tuple_group[0]][file_tuple[1]] = int((file_df.Multi_Token_Annotation.values > 0).sum())
                        elif len(file_tuple_group) == 2:
                            result['amount_of_annotated_token'][file_tuple[0]][file_tuple_group[0]][file_tuple_group[1]][file_tuple[1]] = int((file_df.Multi_Token_Annotation.values > 0).sum())

                # calculate sums by groups and possible subgroups
                for schema, grouping in group_list:
                    if len(grouping) == 1:
                        result['amount_of_annotated_token'][schema][grouping[0]]['TOTAL'] = sum(result['amount_of_annotated_token'][schema][grouping[0]].values())
                    elif len(grouping) == 2:
                        result['amount_of_annotated_token'][schema][grouping[0]][grouping[1]]['TOTAL'] = sum(result['amount_of_annotated_token'][schema][grouping[0]][grouping[1]].values())
                        result['amount_of_annotated_token'][schema][grouping[0]]['TOTAL'] = sum(
                            [
                                result['amount_of_annotated_token'][schema][grouping[0]][subgroup].get('TOTAL', 0) \
                                for subgroup in result['amount_of_annotated_token'][schema][grouping[0]] \
                                if isinstance(result['amount_of_annotated_token'][schema][grouping[0]][subgroup], dict)
                            ]
                        )

                # calculate sums by schema
                for schema in result['amount_of_annotated_token']:
                    result['amount_of_annotated_token'][schema]['TOTAL'] = sum([result['amount_of_annotated_token'][schema][group]['TOTAL'] for group in result['amount_of_annotated_token'][schema]])

            # execute amount of annotated token calculation with default groups per annotation schema and corpus
            else:
                # extract lists of tuples for calculation out of self.tsv_annotations dict:
                # tsv_annotations_list: save every filename together with its corpus and schema in tuples of (schema, corpus, filename)
                # corpus_list: save every unique combination of schema and corpus in tuples of (schema, corpus)
                tsv_annotations_list: List[Tuple[str, str, str]] = [(schema, filename.split('_')[0].lower(), filename) for schema in self.tsv_annotations for filename in self.tsv_annotations[schema]]
                corpus_list: List[Tuple[str, str]] = list(set([(tsv_annotation[0], tsv_annotation[1]) for tsv_annotation in tsv_annotations_list]))

                # build result dict structure for amount_of_annotated_token
                for schema in self.tsv_annotations:
                    result['amount_of_annotated_token'][schema] = dict()
                for schema, corpus in corpus_list:
                    result['amount_of_annotated_token'][schema][corpus] = dict()

                # fill result dict with amount_of_annotated_token values by filename
                for schema, corpus, filename in tsv_annotations_list:
                    file_df: pd.DataFrame = _get_df_with_text_borders(self.tsv_annotations[schema][filename], text_borders)
                    result['amount_of_annotated_token'][schema][corpus][filename] = int((file_df.Multi_Token_Annotation.values > 0).sum())

                # calculate sums by corpus
                for schema, corpus in corpus_list:
                    result['amount_of_annotated_token'][schema][corpus]['TOTAL'] = sum(result['amount_of_annotated_token'][schema][corpus].values())

                # calculate sums by schema
                for schema in result['amount_of_annotated_token']:
                    result['amount_of_annotated_token'][schema]['TOTAL'] = sum([result['amount_of_annotated_token'][schema][corpus]['TOTAL'] for corpus in result['amount_of_annotated_token'][schema]])

            return result
        
        def get_amount_of_annotated_token_by_class() -> dict:
            result = dict(amount_of_annotated_token_by_class={})
            custom_grouping: Union[dict, None] = get_corpus_annotation_statistics_settings['custom_grouping']
            text_borders: Union[Tuple[int, int], None] = get_corpus_annotation_statistics_settings['text_borders']

            # execute amount of annotated token by class calculation with custom groups
            if custom_grouping:
                # create list of tuples for calculation:
                # tsv_annotations_dict: save every filename tuple (schema, filename) together with its groups and possible subgroups
                #                       combinations in a list of tuples of [(group, subgroup), (group)]
                #                       in this tsv_annotations_dict ({(schema, filename): [(group, subgroup), (group)]})
                # group_list: save every unique combination of schema, group and possible subgroup as nested tuple (schema, (group, subgroup)) in a list
                tsv_annotations_dict: Dict[Tuple[str, str], List[Tuple[str, Union[str, None]]]] = {}
                for group in custom_grouping:
                    if isinstance(custom_grouping[group], dict):
                        for subgroup in custom_grouping[group]:
                            for file_tuple in custom_grouping[group][subgroup]:
                                tsv_annotations_dict[file_tuple] = tsv_annotations_dict[file_tuple] + [(group, subgroup)] \
                                if file_tuple in tsv_annotations_dict and isinstance(tsv_annotations_dict[file_tuple], list) \
                                else [(group, subgroup)]
                        continue
                    for file_tuple in custom_grouping[group]:
                        tsv_annotations_dict[file_tuple] = tsv_annotations_dict[file_tuple] + [(group,)] \
                        if file_tuple in tsv_annotations_dict and isinstance(tsv_annotations_dict[file_tuple], list) \
                        else [(group,)]
                group_list: List[Tuple[str, Tuple[str, Union[str, None]]]] = []
                for group in custom_grouping:
                    if isinstance(custom_grouping[group], dict):
                        for subgroup in custom_grouping[group]:
                            schemes_in_subgroup: List[str] = list(set([file_tuple[0] for file_tuple in custom_grouping[group][subgroup]]))
                            for schema in schemes_in_subgroup:
                                group_list.append((schema, (group, subgroup)))
                        continue
                    schemes_in_group: List[str] = list(set([file_tuple[0] for file_tuple in custom_grouping[group]]))
                    for schema in schemes_in_group:
                        group_list.append((schema, (group,)))
                group_list = list(set(group_list))

                # build result dict structure for amount_of_annotated_token_by_class
                for schema in list(set([schema for schema, _ in group_list])):
                    result['amount_of_annotated_token_by_class'][schema] = dict()
                for group_tuple in group_list:
                    if len(group_tuple[1]) == 1:
                        result['amount_of_annotated_token_by_class'][group_tuple[0]][group_tuple[1][0]] = dict()
                    elif len(group_tuple[1]) == 2:
                        if group_tuple[1][0] not in result['amount_of_annotated_token_by_class'][group_tuple[0]]:
                            result['amount_of_annotated_token_by_class'][group_tuple[0]][group_tuple[1][0]] = dict()
                        result['amount_of_annotated_token_by_class'][group_tuple[0]][group_tuple[1][0]][group_tuple[1][1]] = dict()

                # fill result dict with amount_of_annotated_token_by_class values by filename:
                for file_tuple, file_tuple_groups in tsv_annotations_dict.items():
                    # get a dataframe copy without iob prefixes in Tags column, transform the dataframe into a dict of occurences in the Tag column and delete the amount of token with no cs1 class annotation
                    file_df: pd.DataFrame = _get_df_with_text_borders(self.tsv_annotations[file_tuple[0]][file_tuple[1]], text_borders)
                    df_without_iob_schema: pd.Series = file_df.Tag.replace({r'^[BI]-': r''}, regex=True)
                    file_summary: dict = df_without_iob_schema.value_counts().to_dict()
                    if 'O' in file_summary:
                        del file_summary['O']

                    # add missing classes of the schema to the file_summary dict, if the schema is known and no instances of the respective classes exist in the dataframe
                    if file_tuple[0] in canspin_annotation_schema_mapping:
                        # determine current class system name by language, with help of canspin_annotation_schema_mapping
                        corpus = file_tuple[1].split('_')[0].lower()

                        # TODO: undo hardcoding and build language recognition based on configuration files
                        current_language: Union[str, None] = 'deu' if corpus.split('-')[1] == 'deu' else \
                                                             ('spa' if corpus.split('-')[1] in ['spa', 'lat'] else None)

                        if not current_language:
                            logger.info(f'The language of {file_tuple[1]} (in schema {file_tuple[0]}) could not be determined. Skipping the addition of classes with missing instances for this file..')
                            for file_tuple_group in file_tuple_groups:
                                if len(file_tuple_group) == 1:
                                    result['amount_of_annotated_token_by_class'][file_tuple[0]][file_tuple_group[0]][file_tuple[1]] = file_summary
                                elif len(file_tuple_group) == 2:
                                    result['amount_of_annotated_token_by_class'][file_tuple[0]][file_tuple_group[0]][file_tuple_group[1]][file_tuple[1]] = file_summary
                            continue

                        current_category_and_class_system_name: Union[str, None] = next(
                            (category_and_class_system_name for category_and_class_system_name in self.category_and_class_systems \
                            if current_language in self.category_and_class_systems[category_and_class_system_name]['languages'] \
                            and category_and_class_system_name in canspin_annotation_schema_mapping[file_tuple[0]]),
                            None
                        )

                        if not current_category_and_class_system_name:
                            logger.info(f'The category and class system name of {file_tuple[1]} (in schema {file_tuple[0]}) could not be determined. Skipping the addition of classes with missing instances for this file..')
                            for file_tuple_group in file_tuple_groups:
                                if len(file_tuple_group) == 1:
                                    result['amount_of_annotated_token_by_class'][file_tuple[0]][file_tuple_group[0]][file_tuple[1]] = file_summary
                                elif len(file_tuple_group) == 2:
                                    result['amount_of_annotated_token_by_class'][file_tuple[0]][file_tuple_group[0]][file_tuple_group[1]][file_tuple[1]] = file_summary
                            continue

                        for classname in self.category_and_class_systems[current_category_and_class_system_name]['classes']:
                            if classname not in file_summary:
                                file_summary[classname] = 0

                    for file_tuple_group in file_tuple_groups:
                        if len(file_tuple_group) == 1:
                            result['amount_of_annotated_token_by_class'][file_tuple[0]][file_tuple_group[0]][file_tuple[1]] = file_summary
                        elif len(file_tuple_group) == 2:
                            result['amount_of_annotated_token_by_class'][file_tuple[0]][file_tuple_group[0]][file_tuple_group[1]][file_tuple[1]] = file_summary

                # calculate sums by groups and possible subgroups
                # TODO: transform into dict comprehensions
                for schema, grouping in group_list:
                    if len(grouping) == 1:
                        sum_dict_by_group = {}
                        for filename in result['amount_of_annotated_token_by_class'][schema][grouping[0]]:
                            for classname in result['amount_of_annotated_token_by_class'][schema][grouping[0]][filename]:
                                if classname not in sum_dict_by_group:
                                    sum_dict_by_group[classname] = 0
                                sum_dict_by_group[classname] += result['amount_of_annotated_token_by_class'][schema][grouping[0]][filename][classname]
                        result['amount_of_annotated_token_by_class'][schema][grouping[0]]['TOTAL'] = sum_dict_by_group
                    if len(grouping) == 2:
                        sum_dict_by_subgroup = {}
                        for filename in result['amount_of_annotated_token_by_class'][schema][grouping[0]][grouping[1]]:
                            for classname in result['amount_of_annotated_token_by_class'][schema][grouping[0]][grouping[1]][filename]:
                                if classname not in sum_dict_by_subgroup:
                                    sum_dict_by_subgroup[classname] = 0
                                sum_dict_by_subgroup[classname] += result['amount_of_annotated_token_by_class'][schema][grouping[0]][grouping[1]][filename][classname]
                        result['amount_of_annotated_token_by_class'][schema][grouping[0]][grouping[1]]['TOTAL'] = sum_dict_by_subgroup
                        sum_dict_by_group = {}
                        for subgroup in result['amount_of_annotated_token_by_class'][schema][grouping[0]]:
                            if subgroup == 'TOTAL' or 'TOTAL' not in result['amount_of_annotated_token_by_class'][schema][grouping[0]][subgroup]:
                                continue
                            for classname in result['amount_of_annotated_token_by_class'][schema][grouping[0]][subgroup]['TOTAL']:
                                if classname not in sum_dict_by_group:
                                    sum_dict_by_group[classname] = 0
                                sum_dict_by_group[classname] += result['amount_of_annotated_token_by_class'][schema][grouping[0]][subgroup]['TOTAL'][classname]
                        result['amount_of_annotated_token_by_class'][schema][grouping[0]]['TOTAL'] = sum_dict_by_group

                # calculate sums by schema
                # TODO: transform into dict comprehension
                for schema in result['amount_of_annotated_token_by_class']:
                    sum_dict_by_schema = {}
                    for group in result['amount_of_annotated_token_by_class'][schema]:
                        for classname in result['amount_of_annotated_token_by_class'][schema][group]['TOTAL']:
                            if classname not in sum_dict_by_schema:
                                sum_dict_by_schema[classname] = 0
                            sum_dict_by_schema[classname] += result['amount_of_annotated_token_by_class'][schema][group]['TOTAL'][classname]
                    result['amount_of_annotated_token_by_class'][schema]['TOTAL'] = sum_dict_by_schema

            # execute amount of annotated token by class calculation with default groups per annotation schema and corpus
            else:
                # extract lists of tuples for calculation out of self.tsv_annotations dict:
                # tsv_annotations_list: save every filename together with its corpus and schema in tuples of (schema, corpus, filename)
                # corpus_list: save every unique combination of schema and corpus in tuples of (schema, corpus)
                tsv_annotations_list: List[Tuple[str, str, str]] = [(schema, filename.split('_')[0].lower(), filename) for schema in self.tsv_annotations for filename in self.tsv_annotations[schema]]
                corpus_list: List[Tuple[str, str]] = list(set([(tsv_annotation[0], tsv_annotation[1]) for tsv_annotation in tsv_annotations_list]))

                # build result dict structure for amount_of_annotated_token_by_class
                for schema in self.tsv_annotations:
                    result['amount_of_annotated_token_by_class'][schema] = dict()
                for schema, corpus in corpus_list:
                    result['amount_of_annotated_token_by_class'][schema][corpus] = dict()

                # fill result dict with amount_of_annotated_token_by_class values by filename:
                for schema, corpus, filename in tsv_annotations_list:
                    # get a dataframe copy without iob prefixes in Tags column, transform the dataframe into a dict of occurences in the Tag column and delete the amount of token with no cs1 class annotation
                    file_df: pd.DataFrame = _get_df_with_text_borders(self.tsv_annotations[schema][filename], text_borders)
                    df_without_iob_schema: pd.Series = file_df.Tag.replace({r'^[BI]-': r''}, regex=True)
                    file_summary: dict = df_without_iob_schema.value_counts().to_dict()
                    if 'O' in file_summary:
                        del file_summary['O']

                    # add missing classes of the schema to the file_summary dict, if the schema is known and no instances of the respective classes exist in the dataframe
                    if schema in canspin_annotation_schema_mapping:
                        # determine current class system name by language, with help of canspin_annotation_schema_mapping
                        # TODO: undo hardcoding and build language recognition based on configuration files
                        current_language: Union[str, None] = 'deu' if corpus.split('-')[1] == 'deu' else \
                                                             ('spa' if corpus.split('-')[1] in ['spa', 'lat'] else None)

                        if not current_language:
                            logger.info(f'The language of {filename} (in schema {schema}) could not be determined. Skipping the addition of classes with missing instances for this file..')
                            result['amount_of_annotated_token_by_class'][schema][corpus][filename] = file_summary
                            continue

                        current_category_and_class_system_name: Union[str, None] = next(
                            (category_and_class_system_name for category_and_class_system_name in self.category_and_class_systems \
                            if current_language in self.category_and_class_systems[category_and_class_system_name]['languages'] \
                            and category_and_class_system_name in canspin_annotation_schema_mapping[schema]),
                            None
                        )

                        if not current_category_and_class_system_name:
                            logger.info(f'The category and class system name of {filename} (in schema {schema}) could not be determined. Skipping the addition of classes with missing instances for this file..')
                            result['amount_of_annotated_token_by_class'][schema][corpus][filename] = file_summary
                            continue

                        for classname in self.category_and_class_systems[current_category_and_class_system_name]['classes']:
                            if classname not in file_summary:
                                file_summary[classname] = 0

                    result['amount_of_annotated_token_by_class'][schema][corpus][filename] = file_summary

                # calculate sums by corpus
                # TODO: transform into dict comprehension
                for schema, corpus in corpus_list:
                    sum_dict_by_corpus = {}
                    for filename in result['amount_of_annotated_token_by_class'][schema][corpus]:
                        for classname in result['amount_of_annotated_token_by_class'][schema][corpus][filename]:
                            if classname not in sum_dict_by_corpus:
                                sum_dict_by_corpus[classname] = 0
                            sum_dict_by_corpus[classname] += result['amount_of_annotated_token_by_class'][schema][corpus][filename][classname]
                    result['amount_of_annotated_token_by_class'][schema][corpus]['TOTAL'] = sum_dict_by_corpus

                # calculate sums by schema
                # TODO: transform into dict comprehension
                for schema in result['amount_of_annotated_token_by_class']:
                    sum_dict_by_schema = {}
                    for corpus in result['amount_of_annotated_token_by_class'][schema]:
                        for classname in result['amount_of_annotated_token_by_class'][schema][corpus]['TOTAL']:
                            if classname not in sum_dict_by_schema:
                                sum_dict_by_schema[classname] = 0
                            sum_dict_by_schema[classname] += result['amount_of_annotated_token_by_class'][schema][corpus]['TOTAL'][classname]
                    result['amount_of_annotated_token_by_class'][schema]['TOTAL'] = sum_dict_by_schema

            return result
        
        def get_ratios(current_global_results: dict) -> dict:
            """The ratio calculation depends on the calculation results of absolute token amounts.
            If none of these calculation is activated, the ratios calculation will be skipped.

            Args:
                current_global_results (dict): It is the current state of the global result dict within the get_corpus_annotation_statistics method.
                                               If activated, the subfunction will be executed with a current_global_results dict by default.
            """
            result = dict(ratios={})
            custom_grouping: Union[dict, None] = get_corpus_annotation_statistics_settings['custom_grouping']

            already_executed_absolute_amount_calculations: list = [
                calculation for calculation in current_global_results \
                if calculation in [_calculation for _calculation in get_corpus_annotation_statistics_settings['calculations'] if _calculation.startswith('amount')] \
                and current_global_results[calculation]
            ]

            if not already_executed_absolute_amount_calculations:
                logger.info(f'No calculations of absolute token amounts were executed beforehand. Skipping calculation of ratios..')
                return result

            # execute ratios calculation with custom groups
            if custom_grouping:
                # TODO: implement calculation with custom grouping
                raise NotImplementedError

            # execute ratios calculation with default groups by annotation schema and corpus
            else:
                # extract lists of tuples for calculation out of self.tsv_annotations dict:
                # tsv_annotations_list: save every filename together with its corpus and schema in tuples of (schema, corpus, filename)
                # corpus_list: save every unique combination of schema and corpus in tuples of (schema, corpus)
                tsv_annotations_list: List[Tuple[str, str, str]] = [(schema, filename.split('_')[0].lower(), filename) for schema in self.tsv_annotations for filename in self.tsv_annotations[schema]]
                corpus_list: List[Tuple[str, str]] = list(set([(tsv_annotation[0], tsv_annotation[1]) for tsv_annotation in tsv_annotations_list]))

                # build result dict structure for ratios
                for schema in self.tsv_annotations:
                    result['ratios'][schema] = dict()
                for schema, corpus in corpus_list:
                    result['ratios'][schema][corpus] = dict()
                
                # fill result dict with ratio values by filename
                for schema, corpus, filename in tsv_annotations_list:
                    file_ratios: dict = {}

                    # add 'token_of_file:total_token_amount_in_corpus'
                    if 'amount_of_token' in already_executed_absolute_amount_calculations:
                        amount_of_token_in_file: int = current_global_results['amount_of_token'][schema][corpus][filename]
                        amount_of_token_in_corpus: int = current_global_results['amount_of_token'][schema][corpus]['TOTAL']
                        
                        file_ratios['token_of_file:total_token_amount_in_corpus'] = reduce_decimal_place(
                        prevent_division_by_zero(amount_of_token_in_file, amount_of_token_in_corpus), 4)
                        
                    # add 'annotated_token_by_class_in_file:annotated_token_by_class_in_corpus' by class and total
                    if 'amount_of_annotated_token_by_class' in already_executed_absolute_amount_calculations:
                        file_ratios['annotated_token_by_class_in_file:annotated_token_by_class_in_corpus'] = {}
                        classnames_in_both_dicts: List[str] = [
                            classname for classname in current_global_results['amount_of_annotated_token_by_class'][schema][corpus]['TOTAL'] \
                            if classname in current_global_results['amount_of_annotated_token_by_class'][schema][corpus][filename]
                        ]
                        
                        for classname in classnames_in_both_dicts:
                            amount_of_annotated_token_of_class_in_file: int = current_global_results['amount_of_annotated_token_by_class'][schema][corpus][filename][classname]
                            amount_of_annotated_token_of_class_in_corpus: int = current_global_results['amount_of_annotated_token_by_class'][schema][corpus]['TOTAL'][classname]
                            
                            file_ratios['annotated_token_by_class_in_file:annotated_token_by_class_in_corpus'][classname] = reduce_decimal_place(
                            prevent_division_by_zero(amount_of_annotated_token_of_class_in_file, amount_of_annotated_token_of_class_in_corpus), 4)
                            
                        total_amount_of_annotated_token_in_file: int = sum([
                            current_global_results['amount_of_annotated_token_by_class'][schema][corpus][filename][classname] \
                            for classname in current_global_results['amount_of_annotated_token_by_class'][schema][corpus][filename]
                        ])
                        total_amount_of_annotated_token_in_corpus: int = sum([
                            current_global_results['amount_of_annotated_token_by_class'][schema][corpus]['TOTAL'][classname] \
                            for classname in current_global_results['amount_of_annotated_token_by_class'][schema][corpus]['TOTAL']
                        ])
                        
                        file_ratios['annotated_token_by_class_in_file:annotated_token_by_class_in_corpus']['TOTAL'] = reduce_decimal_place(
                        prevent_division_by_zero(total_amount_of_annotated_token_in_file, total_amount_of_annotated_token_in_corpus), 4)

                    # add 'annotated_token_by_class_in_file:total_token_amount_in_file' by class and total
                    if all(calculation in already_executed_absolute_amount_calculations for calculation in ['amount_of_annotated_token_by_class', 'amount_of_token']):
                        file_ratios['annotated_token_by_class_in_file:total_token_amount_in_file'] = {}
                        total_token_amount_in_file: int = current_global_results['amount_of_token'][schema][corpus][filename]

                        for classname in current_global_results['amount_of_annotated_token_by_class'][schema][corpus][filename]:
                            amount_of_annoted_token_of_class_in_file: int = current_global_results['amount_of_annotated_token_by_class'][schema][corpus][filename][classname]

                            file_ratios['annotated_token_by_class_in_file:total_token_amount_in_file'][classname] = reduce_decimal_place(
                            prevent_division_by_zero(amount_of_annoted_token_of_class_in_file, total_token_amount_in_file), 4)

                        total_amount_of_annotated_token_in_file: int = sum([
                            current_global_results['amount_of_annotated_token_by_class'][schema][corpus][filename][classname] \
                            for classname in current_global_results['amount_of_annotated_token_by_class'][schema][corpus][filename]
                        ])

                        file_ratios['annotated_token_by_class_in_file:total_token_amount_in_file']['TOTAL'] = reduce_decimal_place(
                        prevent_division_by_zero(total_amount_of_annotated_token_in_file, total_token_amount_in_file), 4)

                    # add 'annotated_token_by_class_in_file:total_annotated_token_amount_in_file' by class
                    if all(calculation in already_executed_absolute_amount_calculations for calculation in ['amount_of_annotated_token_by_class', 'amount_of_annotated_token']):
                        file_ratios['annotated_token_by_class_in_file:total_annotated_token_amount_in_file'] = {}

                        for classname in current_global_results['amount_of_annotated_token_by_class'][schema][corpus][filename]:
                            amount_of_annotated_token_of_class_in_file: int = current_global_results['amount_of_annotated_token_by_class'][schema][corpus][filename][classname]
                            total_annotated_token_amount_in_file: int = current_global_results['amount_of_annotated_token'][schema][corpus][filename]

                            file_ratios['annotated_token_by_class_in_file:total_annotated_token_amount_in_file'][classname] = reduce_decimal_place(
                            prevent_division_by_zero(amount_of_annotated_token_of_class_in_file, total_annotated_token_amount_in_file), 4)

                    # add 'annotations_by_class_in_file:annotations_by_class_in_corpus' by class and total
                    if 'amount_of_annotations_by_class' in already_executed_absolute_amount_calculations:
                        file_ratios['annotations_by_class_in_file:annotations_by_class_in_corpus'] = {}
                        classnames_in_both_dicts: List[str] = [
                            classname for classname in current_global_results['amount_of_annotations_by_class'][schema][corpus]['TOTAL'] \
                            if classname in current_global_results['amount_of_annotations_by_class'][schema][corpus][filename]
                        ]
                        
                        for classname in classnames_in_both_dicts:
                            amount_of_annotations_of_class_in_file: int = current_global_results['amount_of_annotations_by_class'][schema][corpus][filename][classname]
                            amount_of_annotations_of_class_in_corpus: int = current_global_results['amount_of_annotations_by_class'][schema][corpus]['TOTAL'][classname]
                            
                            file_ratios['annotations_by_class_in_file:annotations_by_class_in_corpus'][classname] = reduce_decimal_place(
                            prevent_division_by_zero(amount_of_annotations_of_class_in_file, amount_of_annotations_of_class_in_corpus), 4)
                            
                        total_amount_of_annotations_in_file: int = sum([
                            current_global_results['amount_of_annotations_by_class'][schema][corpus][filename][classname] \
                            for classname in current_global_results['amount_of_annotations_by_class'][schema][corpus][filename]
                        ])
                        total_amount_of_annotations_in_corpus: int = sum([
                            current_global_results['amount_of_annotations_by_class'][schema][corpus]['TOTAL'][classname] \
                            for classname in current_global_results['amount_of_annotations_by_class'][schema][corpus]['TOTAL']
                        ])
                        
                        file_ratios['annotations_by_class_in_file:annotations_by_class_in_corpus']['TOTAL'] = reduce_decimal_place(
                        prevent_division_by_zero(total_amount_of_annotations_in_file, total_amount_of_annotations_in_corpus), 4)

                    # add 'annotations_by_class_in_file:total_token_amount_in_file' by class and total
                    if all(calculation in already_executed_absolute_amount_calculations for calculation in ['amount_of_annotations_by_class', 'amount_of_token']):
                        file_ratios['annotations_by_class_in_file:total_token_amount_in_file'] = {}
                        total_token_amount_in_file: int = current_global_results['amount_of_token'][schema][corpus][filename]

                        for classname in current_global_results['amount_of_annotations_by_class'][schema][corpus][filename]:
                            amount_of_annotations_of_class_in_file: int = current_global_results['amount_of_annotations_by_class'][schema][corpus][filename][classname]

                            file_ratios['annotations_by_class_in_file:total_token_amount_in_file'][classname] = reduce_decimal_place(
                            prevent_division_by_zero(amount_of_annotations_of_class_in_file, total_token_amount_in_file), 4)

                        total_amount_of_annotations_in_file: int = sum([
                            current_global_results['amount_of_annotations_by_class'][schema][corpus][filename][classname] \
                            for classname in current_global_results['amount_of_annotations_by_class'][schema][corpus][filename]
                        ])

                        file_ratios['annotations_by_class_in_file:total_token_amount_in_file']['TOTAL'] = reduce_decimal_place(
                        prevent_division_by_zero(total_amount_of_annotations_in_file, total_token_amount_in_file), 4)

                    # add 'annotations_by_class_in_file:total_annotations_amount_in_file' by class
                    if all(calculation in already_executed_absolute_amount_calculations for calculation in ['amount_of_annotations_by_class', 'amount_of_annotations']):
                        file_ratios['annotations_by_class_in_file:total_annotations_amount_in_file'] = {}

                        for classname in current_global_results['amount_of_annotations_by_class'][schema][corpus][filename]:
                            amount_of_annotations_of_class_in_file: int = current_global_results['amount_of_annotations_by_class'][schema][corpus][filename][classname]
                            total_annotations_amount_in_file: int = current_global_results['amount_of_annotations'][schema][corpus][filename]

                            file_ratios['annotations_by_class_in_file:total_annotations_amount_in_file'][classname] = reduce_decimal_place(
                            prevent_division_by_zero(amount_of_annotations_of_class_in_file, total_annotations_amount_in_file), 4)

                    result['ratios'][schema][corpus][filename] = file_ratios

                # fill result dict with ratio values by corpus
                for schema, corpus in corpus_list:
                    total_by_corpus_dict = {}
                    
                    # add 'token_of_corpus:total_token_amount_in_schema'
                    if 'amount_of_token' in already_executed_absolute_amount_calculations:
                        amount_of_token_in_corpus: int = current_global_results['amount_of_token'][schema][corpus]['TOTAL']
                        amount_of_token_in_schema: int = current_global_results['amount_of_token'][schema]['TOTAL']
                        
                        total_by_corpus_dict['token_of_corpus:total_token_amount_in_schema'] = reduce_decimal_place(
                        prevent_division_by_zero(amount_of_token_in_corpus, amount_of_token_in_schema), 4)

                    # add 'annotated_token_by_class_in_corpus:annotated_token_by_class_in_schema' by class and total
                    if 'amount_of_annotated_token_by_class' in already_executed_absolute_amount_calculations:
                        total_by_corpus_dict['annotated_token_by_class_in_corpus:annotated_token_by_class_in_schema'] = {}
                        classnames_in_both_dicts: List[str] = [
                            classname for classname in current_global_results['amount_of_annotated_token_by_class'][schema]['TOTAL'] \
                            if classname in current_global_results['amount_of_annotated_token_by_class'][schema][corpus]['TOTAL']
                        ]
                        
                        for classname in classnames_in_both_dicts:
                            amount_of_annotated_token_of_class_in_corpus: int = current_global_results['amount_of_annotated_token_by_class'][schema][corpus]['TOTAL'][classname]
                            amount_of_annotated_token_of_class_in_schema: int = current_global_results['amount_of_annotated_token_by_class'][schema]['TOTAL'][classname]

                            total_by_corpus_dict['annotated_token_by_class_in_corpus:annotated_token_by_class_in_schema'][classname] = reduce_decimal_place(
                            prevent_division_by_zero(amount_of_annotated_token_of_class_in_corpus, amount_of_annotated_token_of_class_in_schema), 4)
                            
                        total_amount_of_annotated_token_in_corpus: int = sum([
                            current_global_results['amount_of_annotated_token_by_class'][schema][corpus]['TOTAL'][classname] \
                            for classname in current_global_results['amount_of_annotated_token_by_class'][schema][corpus]['TOTAL']
                        ])
                        total_amount_of_annotated_token_in_schema: int = sum([
                            current_global_results['amount_of_annotated_token_by_class'][schema]['TOTAL'][classname] \
                            for classname in current_global_results['amount_of_annotated_token_by_class'][schema]['TOTAL']
                        ])
                        
                        total_by_corpus_dict['annotated_token_by_class_in_corpus:annotated_token_by_class_in_schema']['TOTAL'] = reduce_decimal_place(
                        prevent_division_by_zero(total_amount_of_annotated_token_in_corpus, total_amount_of_annotated_token_in_schema), 4)

                    # add 'annotated_token_by_class_in_corpus:total_token_amount_in_corpus' by class and total
                    if all(calculation in already_executed_absolute_amount_calculations for calculation in ['amount_of_annotated_token_by_class', 'amount_of_token']):
                        total_by_corpus_dict['annotated_token_by_class_in_corpus:total_token_amount_in_corpus'] = {}
                        total_token_amount_in_corpus: int = current_global_results['amount_of_token'][schema][corpus]['TOTAL']

                        for classname in current_global_results['amount_of_annotated_token_by_class'][schema][corpus]['TOTAL']:
                            amount_of_annotated_token_of_class_in_corpus: int = current_global_results['amount_of_annotated_token_by_class'][schema][corpus]['TOTAL'][classname]

                            total_by_corpus_dict['annotated_token_by_class_in_corpus:total_token_amount_in_corpus'][classname] = reduce_decimal_place(
                            prevent_division_by_zero(amount_of_annotated_token_of_class_in_corpus, total_token_amount_in_corpus), 4)

                        total_amount_of_annotated_token_in_corpus: int = sum([
                            current_global_results['amount_of_annotated_token_by_class'][schema][corpus]['TOTAL'][classname] \
                            for classname in current_global_results['amount_of_annotated_token_by_class'][schema][corpus]['TOTAL']
                        ])

                        total_by_corpus_dict['annotated_token_by_class_in_corpus:total_token_amount_in_corpus']['TOTAL'] = reduce_decimal_place(
                        prevent_division_by_zero(total_amount_of_annotated_token_in_corpus, total_token_amount_in_corpus), 4)

                    # add 'annotated_token_by_class_in_corpus:total_annotated_token_amount_in_corpus' by class
                    if all(calculation in already_executed_absolute_amount_calculations for calculation in ['amount_of_annotated_token_by_class', 'amount_of_annotated_token']):
                        total_by_corpus_dict['annotated_token_by_class_in_corpus:total_annotated_token_amount_in_corpus'] = {}

                        for classname in current_global_results['amount_of_annotated_token_by_class'][schema][corpus]['TOTAL']:
                            amount_of_annotated_token_of_class_in_corpus: int = current_global_results['amount_of_annotated_token_by_class'][schema][corpus]['TOTAL'][classname]
                            total_annotated_token_amount_in_corpus: int = current_global_results['amount_of_annotated_token'][schema][corpus]['TOTAL']

                            total_by_corpus_dict['annotated_token_by_class_in_corpus:total_annotated_token_amount_in_corpus'][classname] = reduce_decimal_place(
                            prevent_division_by_zero(amount_of_annotated_token_of_class_in_corpus, total_annotated_token_amount_in_corpus), 4)

                    # add 'annotations_by_class_in_corpus:annotations_by_class_in_schema' by class and total
                    if 'amount_of_annotations_by_class' in already_executed_absolute_amount_calculations:
                        total_by_corpus_dict['annotations_by_class_in_corpus:annotations_by_class_in_schema'] = {}
                        classnames_in_both_dicts: List[str] = [
                            classname for classname in current_global_results['amount_of_annotations_by_class'][schema]['TOTAL'] \
                            if classname in current_global_results['amount_of_annotations_by_class'][schema][corpus]['TOTAL']
                        ]
                        
                        for classname in classnames_in_both_dicts:
                            amount_of_annotations_of_class_in_corpus: int = current_global_results['amount_of_annotations_by_class'][schema][corpus]['TOTAL'][classname]
                            amount_of_annotations_of_class_in_schema: int = current_global_results['amount_of_annotations_by_class'][schema]['TOTAL'][classname]

                            total_by_corpus_dict['annotations_by_class_in_corpus:annotations_by_class_in_schema'][classname] = reduce_decimal_place(
                            prevent_division_by_zero(amount_of_annotations_of_class_in_corpus, amount_of_annotations_of_class_in_schema), 4)
                            
                        total_amount_of_annotations_in_corpus: int = sum([
                            current_global_results['amount_of_annotations_by_class'][schema][corpus]['TOTAL'][classname] \
                            for classname in current_global_results['amount_of_annotations_by_class'][schema][corpus]['TOTAL']
                        ])
                        total_amount_of_annotations_in_schema: int = sum([
                            current_global_results['amount_of_annotations_by_class'][schema]['TOTAL'][classname] \
                            for classname in current_global_results['amount_of_annotations_by_class'][schema]['TOTAL']
                        ])
                        
                        total_by_corpus_dict['annotations_by_class_in_corpus:annotations_by_class_in_schema']['TOTAL'] = reduce_decimal_place(
                        prevent_division_by_zero(total_amount_of_annotations_in_corpus, total_amount_of_annotations_in_schema), 4)

                    # add 'annotations_by_class_in_corpus:total_token_amount_in_corpus' by class and total
                    if all(calculation in already_executed_absolute_amount_calculations for calculation in ['amount_of_annotations_by_class', 'amount_of_token']):
                        total_by_corpus_dict['annotations_by_class_in_corpus:total_token_amount_in_corpus'] = {}
                        total_token_amount_in_corpus: int = current_global_results['amount_of_token'][schema][corpus]['TOTAL']

                        for classname in current_global_results['amount_of_annotations_by_class'][schema][corpus]['TOTAL']:
                            amount_of_annotations_of_class_in_corpus: int = current_global_results['amount_of_annotations_by_class'][schema][corpus]['TOTAL'][classname]

                            total_by_corpus_dict['annotations_by_class_in_corpus:total_token_amount_in_corpus'][classname] = reduce_decimal_place(
                            prevent_division_by_zero(amount_of_annotations_of_class_in_corpus, total_token_amount_in_corpus), 4)

                        total_amount_of_annotations_in_corpus: int = sum([
                            current_global_results['amount_of_annotations_by_class'][schema][corpus]['TOTAL'][classname] \
                            for classname in current_global_results['amount_of_annotations_by_class'][schema][corpus]['TOTAL']
                        ])

                        total_by_corpus_dict['annotations_by_class_in_corpus:total_token_amount_in_corpus']['TOTAL'] = reduce_decimal_place(
                        prevent_division_by_zero(total_amount_of_annotations_in_corpus, total_token_amount_in_corpus), 4)

                    # add 'annotations_by_class_in_corpus:total_annotations_amount_in_corpus' by class
                    if all(calculation in already_executed_absolute_amount_calculations for calculation in ['amount_of_annotations_by_class', 'amount_of_annotations']):
                        total_by_corpus_dict['annotations_by_class_in_corpus:total_annotations_amount_in_corpus'] = {}

                        for classname in current_global_results['amount_of_annotations_by_class'][schema][corpus]['TOTAL']:
                            amount_of_annotations_of_class_in_corpus: int = current_global_results['amount_of_annotations_by_class'][schema][corpus]['TOTAL'][classname]
                            total_annotations_amount_in_corpus: int = current_global_results['amount_of_annotations'][schema][corpus]['TOTAL']

                            total_by_corpus_dict['annotations_by_class_in_corpus:total_annotations_amount_in_corpus'][classname] = reduce_decimal_place(
                            prevent_division_by_zero(amount_of_annotations_of_class_in_corpus, total_annotations_amount_in_corpus), 4)
                   
                    result['ratios'][schema][corpus]['TOTAL'] = total_by_corpus_dict
               
            return result

        def get_word_lists_by_class() -> dict:
            result = dict(word_lists_by_class={})
            custom_grouping: Union[dict, None] = get_corpus_annotation_statistics_settings['custom_grouping']
            text_borders: Union[Tuple[int, int], None] = get_corpus_annotation_statistics_settings['text_borders']

            # execute word_lists_by_class calculation with custom groups
            if custom_grouping:
                # create list of tuples for calculation:
                # tsv_annotations_dict: save every filename tuple (schema, filename) together with its groups and possible subgroups
                #                       combinations in a list of tuples of [(group, subgroup), (group)]
                #                       in this tsv_annotations_dict ({(schema, filename): [(group, subgroup), (group)]})
                # group_list: save every unique combination of schema, group and possible subgroup as nested tuple (schema, (group, subgroup)) in a list
                tsv_annotations_dict: Dict[Tuple[str, str], List[Tuple[str, Union[str, None]]]] = {}
                for group in custom_grouping:
                    if isinstance(custom_grouping[group], dict):
                        for subgroup in custom_grouping[group]:
                            for file_tuple in custom_grouping[group][subgroup]:
                                tsv_annotations_dict[file_tuple] = tsv_annotations_dict[file_tuple] + [(group, subgroup)] \
                                if file_tuple in tsv_annotations_dict and isinstance(tsv_annotations_dict[file_tuple], list) \
                                else [(group, subgroup)]
                        continue
                    for file_tuple in custom_grouping[group]:
                        tsv_annotations_dict[file_tuple] = tsv_annotations_dict[file_tuple] + [(group,)] \
                        if file_tuple in tsv_annotations_dict and isinstance(tsv_annotations_dict[file_tuple], list) \
                        else [(group,)]
                group_list: List[Tuple[str, Tuple[str, Union[str, None]]]] = []
                for group in custom_grouping:
                    if isinstance(custom_grouping[group], dict):
                        for subgroup in custom_grouping[group]:
                            schemes_in_subgroup: List[str] = list(set([file_tuple[0] for file_tuple in custom_grouping[group][subgroup]]))
                            for schema in schemes_in_subgroup:
                                group_list.append((schema, (group, subgroup)))
                        continue
                    schemes_in_group: List[str] = list(set([file_tuple[0] for file_tuple in custom_grouping[group]]))
                    for schema in schemes_in_group:
                        group_list.append((schema, (group,)))
                group_list = list(set(group_list))

                # build result dict structure for word_lists_by_class
                for schema in list(set([schema for schema, _ in group_list])):
                    result['word_lists_by_class'][schema] = dict()
                for group_tuple in group_list:
                    if len(group_tuple[1]) == 1:
                        result['word_lists_by_class'][group_tuple[0]][group_tuple[1][0]] = dict()
                    elif len(group_tuple[1]) == 2:
                        if group_tuple[1][0] not in result['word_lists_by_class'][group_tuple[0]]:
                            result['word_lists_by_class'][group_tuple[0]][group_tuple[1][0]] = dict()
                        result['word_lists_by_class'][group_tuple[0]][group_tuple[1][0]][group_tuple[1][1]] = dict()

                # fill result dict with word_lists_by_class values by filename:
                for file_tuple, file_tuple_groups in tsv_annotations_dict.items():
                    file_summary: dict = {}
                    file_df: pd.DataFrame = _get_df_with_text_borders(self.tsv_annotations[file_tuple[0]][file_tuple[1]], text_borders)
                    filtered_df_with_annotated_token: pd.DataFrame = file_df[file_df['Multi_Token_Annotation'] > 0].copy()
                    filtered_df_with_annotated_token.Tag = filtered_df_with_annotated_token.Tag.replace({r'^[BI]-': r''}, regex=True)
                    classname_list: list = list(filtered_df_with_annotated_token.Tag.unique())
                    for classname in classname_list:
                        filtered_df_with_annotated_token_of_class: pd.DataFrame = filtered_df_with_annotated_token[filtered_df_with_annotated_token['Tag'] == classname]
                        file_summary[classname] = filtered_df_with_annotated_token_of_class.Token.value_counts().to_dict()

                    # add missing classes of the schema to the file_summary dict, if the schema is known and no instances of the respective classes exist in the dataframe
                    if file_tuple[0] in canspin_annotation_schema_mapping:
                        # determine current class system name by language, with help of canspin_annotation_schema_mapping
                        corpus = file_tuple[1].split('_')[0].lower()

                        # TODO: undo hardcoding and build language recognition based on configuration files
                        current_language: Union[str, None] = 'deu' if corpus.split('-')[1] == 'deu' else \
                                                             ('spa' if corpus.split('-')[1] in ['spa', 'lat'] else None)

                        if not current_language:
                            logger.info(f'The language of {file_tuple[1]} (in schema {file_tuple[0]}) could not be determined. Skipping the addition of classes with missing instances for this file..')
                            for file_tuple_group in file_tuple_groups:
                                if len(file_tuple_group) == 1:
                                    result['word_lists_by_class'][file_tuple[0]][file_tuple_group[0]][file_tuple[1]] = file_summary
                                elif len(file_tuple_group) == 2:
                                    result['word_lists_by_class'][file_tuple[0]][file_tuple_group[0]][file_tuple_group[1]][file_tuple[1]] = file_summary
                            continue

                        current_category_and_class_system_name: Union[str, None] = next(
                            (category_and_class_system_name for category_and_class_system_name in self.category_and_class_systems \
                            if current_language in self.category_and_class_systems[category_and_class_system_name]['languages'] \
                            and category_and_class_system_name in canspin_annotation_schema_mapping[file_tuple[0]]),
                            None
                        )

                        if not current_category_and_class_system_name:
                            logger.info(f'The category and class system name of {file_tuple[1]} (in schema {file_tuple[0]}) could not be determined. Skipping the addition of classes with missing instances for this file..')
                            for file_tuple_group in file_tuple_groups:
                                if len(file_tuple_group) == 1:
                                    result['word_lists_by_class'][file_tuple[0]][file_tuple_group[0]][file_tuple[1]] = file_summary
                                elif len(file_tuple_group) == 2:
                                    result['word_lists_by_class'][file_tuple[0]][file_tuple_group[0]][file_tuple_group[1]][file_tuple[1]] = file_summary
                            continue

                        for classname in self.category_and_class_systems[current_category_and_class_system_name]['classes']:
                            if classname not in file_summary:
                                file_summary[classname] = {}

                    for file_tuple_group in file_tuple_groups:
                        if len(file_tuple_group) == 1:
                            result['word_lists_by_class'][file_tuple[0]][file_tuple_group[0]][file_tuple[1]] = file_summary
                        elif len(file_tuple_group) == 2:
                            result['word_lists_by_class'][file_tuple[0]][file_tuple_group[0]][file_tuple_group[1]][file_tuple[1]] = file_summary

                # calculate sums by groups and possible subgroups
                # TODO: transform into dict comprehensions
                for schema, grouping in group_list:
                    if len(grouping) == 1:
                        sum_dict_by_group = {}
                        for filename in result['word_lists_by_class'][schema][grouping[0]]:
                            for classname in result['word_lists_by_class'][schema][grouping[0]][filename]:
                                if classname not in sum_dict_by_group:
                                    sum_dict_by_group[classname] = {}
                                for token in result['word_lists_by_class'][schema][grouping[0]][filename][classname]:
                                    if token in sum_dict_by_group[classname]:
                                        sum_dict_by_group[classname][token] = sum_dict_by_group[classname][token] + \
                                                                              result['word_lists_by_class'][schema][grouping[0]][filename][classname][token]
                                        continue
                                    sum_dict_by_group[classname][token] = result['word_lists_by_class'][schema][grouping[0]][filename][classname][token]
                        for classname in sum_dict_by_group:
                            sum_dict_by_group[classname] = dict(sorted(sum_dict_by_group[classname].items(), key=lambda x: int(x[1]), reverse=True))
                        result['word_lists_by_class'][schema][grouping[0]]['TOTAL'] = sum_dict_by_group
                    if len(grouping) == 2:
                        sum_dict_by_subgroup = {}
                        for filename in result['word_lists_by_class'][schema][grouping[0]][grouping[1]]:
                            for classname in result['word_lists_by_class'][schema][grouping[0]][grouping[1]][filename]:
                                if classname not in sum_dict_by_subgroup:
                                    sum_dict_by_subgroup[classname] = {}
                                for token in result['word_lists_by_class'][schema][grouping[0]][grouping[1]][filename][classname]:
                                    if token in sum_dict_by_subgroup[classname]:
                                        sum_dict_by_subgroup[classname][token] = sum_dict_by_subgroup[classname][token] + \
                                                                                 result['word_lists_by_class'][schema][grouping[0]][grouping[1]][filename][classname][token]
                                        continue
                                    sum_dict_by_subgroup[classname][token] = result['word_lists_by_class'][schema][grouping[0]][grouping[1]][filename][classname][token]
                        for classname in sum_dict_by_subgroup:
                            sum_dict_by_subgroup[classname] = dict(sorted(sum_dict_by_subgroup[classname].items(), key=lambda x: int(x[1]), reverse=True))
                        result['word_lists_by_class'][schema][grouping[0]][grouping[1]]['TOTAL'] = sum_dict_by_subgroup
                        sum_dict_by_group = {}
                        for subgroup in result['word_lists_by_class'][schema][grouping[0]]:
                            if subgroup == 'TOTAL' or 'TOTAL' not in result['word_lists_by_class'][schema][grouping[0]][subgroup]:
                                continue
                            for classname in result['word_lists_by_class'][schema][grouping[0]][subgroup]['TOTAL']:
                                if classname not in sum_dict_by_group:
                                    sum_dict_by_group[classname] = {}
                                for token in result['word_lists_by_class'][schema][grouping[0]][subgroup]['TOTAL'][classname]:
                                    if token in sum_dict_by_group[classname]:
                                        sum_dict_by_group[classname][token] = sum_dict_by_group[classname][token] + \
                                                                              result['word_lists_by_class'][schema][grouping[0]][subgroup]['TOTAL'][classname][token]
                                        continue
                                    sum_dict_by_group[classname][token] = result['word_lists_by_class'][schema][grouping[0]][subgroup]['TOTAL'][classname][token]
                        for classname in sum_dict_by_group:
                            sum_dict_by_group[classname] = dict(sorted(sum_dict_by_group[classname].items(), key=lambda x: int(x[1]), reverse=True))
                        result['word_lists_by_class'][schema][grouping[0]]['TOTAL'] = sum_dict_by_group

                # calculate sums by schema
                # TODO: transform into dict comprehension
                for schema in result['word_lists_by_class']:
                    sum_dict_by_schema = {}
                    for group in result['word_lists_by_class'][schema]:
                        for classname in result['word_lists_by_class'][schema][group]['TOTAL']:
                            if classname not in sum_dict_by_schema:
                                sum_dict_by_schema[classname] = {}
                            for token in result['word_lists_by_class'][schema][group]['TOTAL'][classname]:
                                if token in sum_dict_by_schema[classname]:
                                    sum_dict_by_schema[classname][token] = sum_dict_by_schema[classname][token] + \
                                                                           result['word_lists_by_class'][schema][group]['TOTAL'][classname][token]
                                    continue
                                sum_dict_by_schema[classname][token] = result['word_lists_by_class'][schema][group]['TOTAL'][classname][token]
                    for classname in sum_dict_by_schema:
                        sum_dict_by_schema[classname] = dict(sorted(sum_dict_by_schema[classname].items(), key=lambda x: int(x[1]), reverse=True))
                    result['word_lists_by_class'][schema]['TOTAL'] = sum_dict_by_schema

            # execute word_lists_by_class calculation with default groups by annotation schema and corpus
            else:
                # extract lists of tuples for calculation out of self.tsv_annotations dict:
                # tsv_annotations_list: save every filename together with its corpus and schema in tuples of (schema, corpus, filename)
                # corpus_list: save every unique combination of schema and corpus in tuples of (schema, corpus)
                tsv_annotations_list: List[Tuple[str, str, str]] = [(schema, filename.split('_')[0].lower(), filename) for schema in self.tsv_annotations for filename in self.tsv_annotations[schema]]
                corpus_list: List[Tuple[str, str]] = list(set([(tsv_annotation[0], tsv_annotation[1]) for tsv_annotation in tsv_annotations_list]))

                # build result dict structure for word_lists_by_class
                for schema in self.tsv_annotations:
                    result['word_lists_by_class'][schema] = dict()
                for schema, corpus in corpus_list:
                    result['word_lists_by_class'][schema][corpus] = dict()

                # fill result dict with word_lists_by_class values by filename
                for schema, corpus, filename in tsv_annotations_list:
                    file_summary: dict = {}
                    file_df: pd.DataFrame = _get_df_with_text_borders(self.tsv_annotations[schema][filename], text_borders)
                    filtered_df_with_annotated_token: pd.DataFrame = file_df[file_df['Multi_Token_Annotation'] > 0].copy()
                    filtered_df_with_annotated_token.Tag = filtered_df_with_annotated_token.Tag.replace({r'^[BI]-': r''}, regex=True)
                    classname_list: list = list(filtered_df_with_annotated_token.Tag.unique())
                    for classname in classname_list:
                        filtered_df_with_annotated_token_of_class: pd.DataFrame = filtered_df_with_annotated_token[filtered_df_with_annotated_token['Tag'] == classname]
                        file_summary[classname] = filtered_df_with_annotated_token_of_class.Token.value_counts().to_dict()

                    # add missing classes of the schema to the file_summary dict, if the schema is known and no instances of the respective classes exist in the dataframe
                    if schema in canspin_annotation_schema_mapping:
                        # determine current class system name by language, with help of canspin_annotation_schema_mapping
                        # TODO: undo hardcoding and build language recognition based on configuration files
                        current_language: Union[str, None] = 'deu' if corpus.split('-')[1] == 'deu' else \
                                                             ('spa' if corpus.split('-')[1] in ['spa', 'lat'] else None)

                        if not current_language:
                            logger.info(f'The language of {filename} (in schema {schema}) could not be determined. Skipping the addition of classes with missing instances for this file..')
                            result['word_lists_by_class'][schema][corpus][filename] = file_summary
                            continue

                        current_category_and_class_system_name: Union[str, None] = next(
                            (category_and_class_system_name for category_and_class_system_name in self.category_and_class_systems \
                            if current_language in self.category_and_class_systems[category_and_class_system_name]['languages'] \
                            and category_and_class_system_name in canspin_annotation_schema_mapping[schema]),
                            None
                        )

                        if not current_category_and_class_system_name:
                            logger.info(f'The category and class system name of {filename} (in schema {schema}) could not be determined. Skipping the addition of classes with missing instances for this file..')
                            result['word_lists_by_class'][schema][corpus][filename] = file_summary
                            continue

                        for classname in self.category_and_class_systems[current_category_and_class_system_name]['classes']:
                            if classname not in file_summary:
                                file_summary[classname] = {}

                    result['word_lists_by_class'][schema][corpus][filename] = file_summary

                # calculate sums by corpus
                # TODO: transform into dict comprehension
                for schema, corpus in corpus_list:
                    sum_dict_by_corpus = {}
                    for filename in result['word_lists_by_class'][schema][corpus]:
                        for classname in result['word_lists_by_class'][schema][corpus][filename]:
                            if classname not in sum_dict_by_corpus:
                                sum_dict_by_corpus[classname] = {}                            
                            for token in result['word_lists_by_class'][schema][corpus][filename][classname]:
                                if token in sum_dict_by_corpus[classname]:
                                    sum_dict_by_corpus[classname][token] = sum_dict_by_corpus[classname][token] + \
                                                                           result['word_lists_by_class'][schema][corpus][filename][classname][token]
                                    continue
                                sum_dict_by_corpus[classname][token] = result['word_lists_by_class'][schema][corpus][filename][classname][token]
                    for classname in sum_dict_by_corpus:
                        sum_dict_by_corpus[classname] = dict(sorted(sum_dict_by_corpus[classname].items(), key=lambda x: int(x[1]), reverse=True))
                    result['word_lists_by_class'][schema][corpus]['TOTAL'] = sum_dict_by_corpus

                # calculate sums by schema
                # TODO: transform into dict comprehension
                for schema in result['word_lists_by_class']:
                    sum_dict_by_schema = {}
                    for corpus in result['word_lists_by_class'][schema]:
                        for classname in result['word_lists_by_class'][schema][corpus]['TOTAL']:
                            if classname not in sum_dict_by_schema:
                                sum_dict_by_schema[classname] = {}
                            for token in result['word_lists_by_class'][schema][corpus]['TOTAL'][classname]:
                                if token in sum_dict_by_schema[classname]:
                                    sum_dict_by_schema[classname][token] = sum_dict_by_schema[classname][token] + \
                                                                           result['word_lists_by_class'][schema][corpus]['TOTAL'][classname][token]
                                    continue
                                sum_dict_by_schema[classname][token] = result['word_lists_by_class'][schema][corpus]['TOTAL'][classname][token]
                    for classname in sum_dict_by_schema:
                        sum_dict_by_schema[classname] = dict(sorted(sum_dict_by_schema[classname].items(), key=lambda x: int(x[1]), reverse=True))
                    result['word_lists_by_class'][schema]['TOTAL'] = sum_dict_by_schema

            return result

        # declare global result and methods
        result = dict()

        methods = {
            'amount_of_annotations': (get_amount_of_annotations, {}),
            'amount_of_annotations_by_class': (get_amount_of_annotations_by_class, {}), 
            'amount_of_token': (get_amount_of_token, {}),
            'amount_of_annotated_token': (get_amount_of_annotated_token, {}),
            'amount_of_annotated_token_by_class': (get_amount_of_annotated_token_by_class, {}),
            'ratios': (get_ratios, {'current_global_results': result}),
            'word_lists_by_class': (get_word_lists_by_class, {})
        }

        # check if self.tsv_annotations has data and return an empty dict if no data is available
        if not self.tsv_annotations_has_data():
            logger.info(f'No tsv annotation data loaded in the project: Calculation of corpus annotation statistics is not possible.')
            return result
        
        # execute calculations and fill the result dict
        # TODO: make sure that all subfunctions, that depend on the calculation results, are executed after the subfunctions, on which they depend on (dicts have no indices, but are ordered since python 3.7)
        activated_calculations: list = [calculation for calculation in get_corpus_annotation_statistics_settings['calculations'] if get_corpus_annotation_statistics_settings['calculations'][calculation]]
        for calculation in activated_calculations:
            result.update(methods[calculation][0](**methods[calculation][1]))

        # safe result to file if the respective parameter is a string
        if safe_result_to_file and isinstance(safe_result_to_file, str):
            export_filepath: str = os.path.join(abs_local_save_path, f'{safe_result_to_file}.json') \
                                   if '.json' not in safe_result_to_file \
                                   else safe_result_to_file
            json_file_str: str = json.dumps(result, indent=2, sort_keys=False, ensure_ascii=False)

            if (os.path.isfile(export_filepath)):
                logger.info(f'JSON file {export_filepath} already exists and will be overwritten.')

            with open(export_filepath, 'w') as file:
                file.write(json_file_str)
                logger.info(f'JSON file {export_filepath} successfully created.')

        return result
        
        # rename method
        # make input tsv amount selectable (implement grouping and subgrouping of tsv files)
        # {
        #   group_1: {
        #     subgroup_1_1: ['1.tsv'],
        #     subgroup_1_2: ['2.tsv']
        #   }
        #   group_2: {
        #     subgroup_2_1: ['3.tsv', '4.tsv'],
        #     subgroup_2_2: ['5.tsv', '6.tsv']
        #   }
        # }
        # word lists and heatmaps for cooccurence
        # should offer comparing algorithms and single group analysis
        # for comparisons: 
        # 
        # calculation of the proportion of annotation tokens in the total number of tokens


class AnnotationManipulator(CanspinProject):
    """Bundling class for changing annotation data.

    Args:
        imported_project(CatmaProject, optional): An already loaded CatmaProject can be passed here.
        init_settings(dict, optional): Defines necessary settings for loading the CATMA project.
    """
    def __init__(
        self,
        imported_project: Union[CatmaProject, None] = None,
        init_settings: Union[dict, None] = None):

        super().__init__(
            imported_project=imported_project,
            init_settings=init_settings
        )

        self.default_create_goldstandard_settings = {
            # 'strict' | 'overlapping'
            'segmentation': 'strict',
            # 'strict' | 'category'
            'classification': 'strict',
            'push_to_gitlab': True,
            'commit_message': 'gold annotation created with gitma_canspin'
        }

    def create_gold_standard_ac(
            self,
            input_acs: List[AnnotationCollection],
            ac_gold: AnnotationCollection,
            create_goldstandard_settings: Union[dict, None] = None) -> None:
        """Searches for matching annotations in input AnnotationCollections and copies all matches in another existing AnnotationCollection.
        The gold AnnotationCollection has to exist beforehand in the project. All Annotations in it will be deleted during gold standard creation, if any exist.
        The method is an version of CatmaProjects create_gold_annotations method optimized for CANSpiN project purposes (differences: possibility of handling multiple annotation collections, possibility of handling discontinous annotations, different decisions in algorithm for comparing annotation collections)
        
        Args:
            input_acs (List[AnnotationCollection]): List with references to input AnnotationCollections. Has to contain at least 1 AnnotationCollection reference.
            ac_gold (AnnotationCollection): Reference to AnnotationCollection for Gold Annotations. Has to exist beforehand in the project.
            create_goldstandard_settings (dict, optional): Custom settings for overlap test. Defaults to None. If None is provided, self.default_create_goldstandard_settings will be used.

        Raises:
            ValueError: Is raised, when input_acs is no list, is an empty list or when the delivered AnnotationCollection objects do not refer to the same text or tagsets.
        """
        # checks if input_acs argument is list containing at least 1 AnnotationCollection object
        if type(input_acs) is not list or not len(input_acs):
            raise ValueError('There is no AnnotationCollections delivered to create_gold_standard_ac method or it is not delivered as a list.')

        # checks if all delivered AnnotationCollection objects refer to the same text
        first_plain_text_id: str = input_acs[0].plain_text_id
        if len([ac for ac in input_acs if ac.plain_text_id == first_plain_text_id]) < len(input_acs):
            raise ValueError('Not all AnnotationCollections delivered to create_gold_standard_ac method refer to the same text.')

        # check if all delivered Annotation objects refer to the same tagset
        first_tagset_id: str = input_acs[0].annotations[0].data['body']['tagset']
        if len([an for ac in input_acs for an in ac if an.data['body']['tagset'] != first_tagset_id]):
            raise ValueError('Not all Annotations delivered to create_gold_standard_ac method refer to the same tagset.')

        # define working variables
        acs: Dict[int, List[Union[List[Annotation], pd.DataFrame]]] = {index: [ac.annotations.copy(), ac.df.copy().merge(pd.DataFrame(data=[an.uuid for an in ac.annotations], columns=['annotation_uuid']), left_index=True, right_index=True)] for index, ac in enumerate(input_acs)}
        create_goldstandard_settings: dict = create_goldstandard_settings if create_goldstandard_settings else self.default_create_goldstandard_settings

        # prepares start_point and end_point cells of every ac for taking a list as value
        # and adds start and end points in every ac dataframe as list to take discontinous annotations into account
        for ac in acs.values():
            ac[1]['start_point'] = ac[1]['start_point'].astype('object')
            ac[1]['end_point'] = ac[1]['end_point'].astype('object')
            for index, annotation in enumerate(ac[0]):
                start_points: List[int] = []
                end_points: List[int] = []
                for item in annotation.data['target']['items']:
                    start_points.append(item['selector']['start'])
                    end_points.append(item['selector']['end'])
                ac[1].at[index, 'start_point'] = start_points
                ac[1].at[index, 'end_point'] = end_points

        # segmentation methods and execution
        def _compare_for_strict_segmentation(annotation_collections: Dict[int, List[Union[List[Annotation], pd.DataFrame]]]) -> Union[List[Tuple[List[Annotation], List[int], List[int]]], None]:
            """Executes strict segmentation comparison of all Annotations delivered in annotation_collections parameter of the method.
            If annotation_collections variable contains only 1 ac, its data will be returned.
            If annotation_collections variable contains multiple annotation collections, the majority has to have the same text segments annotated to be counted as a match.
            
            Args:
                annotation_collections (Dict[int, List[Union[List[Annotation], pd.DataFrame]]]): Designed to take global acs variable value, which contains all annotation collections.

            Returns:
                Union[List[Tuple[List[Annotation], List[int], List[int]]], None]: It is a list of exact segmentation matches delivered as tuples containing a list of references to the matching annotation objects and two lists with the corresponding integer start and end point values. Can be None if no matches are found.
            """
            logger.info('Executing strict segmentation...')

            if len(annotation_collections) == 1:
                return [([an], annotation_collections[0][1].iloc[index]['start_point'], annotation_collections[0][1].iloc[index]['end_point']) for index, an in enumerate(annotation_collections[0][0])]
            
            output: List[Tuple[List[Annotation], List[int], List[int]]] = []
            all_df: pd.DataFrame = pd.concat([ac[1] for ac in annotation_collections.values()])
            all_an: List[Annotation] = [an for ac in annotation_collections.values() for an in ac[0]]
            for ac_index, (key, ac) in enumerate(annotation_collections.items()):
                logger.info(f'Strict segmentation: Processing annotation collection {ac_index + 1} / {len(annotation_collections)}...')
                for row_index, row in ac[1].iterrows():
                    logger.info(f'Strict segmentation: Processing annotation collection {ac_index + 1} / {len(annotation_collections)}: row {row_index} / {len(ac[1])}...')
                    filtered_all_df: pd.DataFrame = all_df[all_df['start_point'].map(lambda x: x == row['start_point']) & all_df['end_point'].map(lambda x: x == row['end_point'])]
                    if len(filtered_all_df) > 1:
                        if not len(output) or not ((row['start_point'] in [match[1] for match in output]) and (row['end_point'] in [match[2] for match in output])):
                            output.append(([an for an in all_an if an.uuid in filtered_all_df['annotation_uuid'].tolist()], row['start_point'], row['end_point']))

            logger.info('Finished strict segmentation.')
            return output

        segmentation_methods: dict = {'strict': _compare_for_strict_segmentation}
        matches: Union[List[Tuple[List[Annotation], List[int], List[int]]], None] = segmentation_methods[create_goldstandard_settings['segmentation']](acs)
        
        # majority principle: remove segmentation matches that involve only half or less than half of the AnnotationCollections
        matches = [match for match in matches if len(match[0]) > (len(acs) / 2)]

        # classification methods and execution
        def _compare_for_strict_classification(segmentation_result: List[Tuple[List[Annotation], List[int], List[int]]]) -> List[Tuple[List[Annotation], List[int], List[int]]]:
            """Executes strict classification comparison of all delivered segmentation matches.
            In every tuple the classification inside the Annotation objects are compared: The tag will be unified or the tuple will be deleted.
            If any tuple contains only 1 annotation, only 1 ac was passed to the segmentation subfunction. The input data is then returned.
            
            Args:
                segmentation_result (List[Tuple[List[Annotation], List[int], List[int]]]): Takes the result of a segmentation subfunction. Can not be None due to None check before _compare_for_strict_classification execution.

            Returns:
                List[Tuple[List[Annotation], List[int], List[int]]]
            """
            logger.info('Executing strict classification...')

            # TODO: implement
            classification_result = segmentation_result

            logger.info('Finished strict classification.')
            return classification_result

        classification_methods: dict = {'strict': _compare_for_strict_classification}
        matches = classification_methods[create_goldstandard_settings['classification']](matches) if matches is not None else None

        # copy matches to gold ac if matches were found
        def _copy_matches_to_gold_ac(classification_result: List[Tuple[List[Annotation], List[int], List[int]]]) -> None:
            """Sub function to copy Annotations into empty existing Gold Annotation Collection.
            Annotation classes copy method is not used for this purpose due to the fact that it takes \
                an annotation collections name as argument and not the collection itself. The write_annotation_json method \
                inside then uses this name and the CatmaProjects ac_dict property to get the collection, \
                but the ac_dict is incomplete if multiple collection exist with the same name.
            Method parameter create_goldstandard_settings['push_to_gitlab'] or class property self.default_create_goldstandard_settings \
                controls if the annotations copied are pushed to the Catma backend.

            Args:
                classification_result (List[Union[Tuple[List[Annotation], List[int], List[int]]]]): Designed to take results from any classification sub function.
            """
            cwd: str = os.getcwd()
            gold_uuid: str = ac_gold.uuid
            gold_annotation_directory: str = f'{self.project.projects_directory}{self.project.uuid}/collections/{gold_uuid}/annotations/'

            if not os.path.isdir(gold_annotation_directory):
                    os.mkdir(gold_annotation_directory)
            else:
                for f in os.listdir(gold_annotation_directory):
                    # removes all files in gold annotation collection to prevent double gold annotations:
                    os.remove(f'{gold_annotation_directory}{f}')

            def _copy(
                    an: Annotation,
                    ac: AnnotationCollection,
                    compare_annotation: Union[Annotation, None] = None,
                    uuid_override: Union[str, None] = None,
                    timestamp_override: Union[str, None] = None
            ) -> str:
                new_properties = deepcopy(an.properties)

                # remove property values from new_properties unless we have a compare_annotation whose corresponding property values match
                for property_name in new_properties.keys():
                    if compare_annotation is None or new_properties.get(property_name) != compare_annotation.properties.get(property_name, []):
                        new_properties[property_name] = []

                document_uuid = an.data['target']['items'][0]['source']
                document_title = [text for text in an.project.texts if text.uuid == document_uuid][0].title

                start_points = [item['selector']['start'] for item in an.data['target']['items']]
                end_points = [item['selector']['end'] for item in an.data['target']['items']]

                return write_annotation_json_with_ac_object(
                    project=an.project,
                    text_title=document_title,
                    annotation_collection=ac,
                    tagset_name=an.project.tagset_dict[get_tagset_uuid(an.data)].name,
                    tag_name=an.tag.name,
                    start_points=start_points,
                    end_points=end_points,
                    property_annotations=new_properties,
                    author='auto_gold',
                    uuid_override=uuid_override,
                    timestamp_override=timestamp_override
                )
            
            copied_annotations: int = 0
            for match in classification_result:
                copied_file_path = _copy(an=match[0][0], ac=ac_gold)
                copied_annotations += 1
                logger.info(f'Wrote file: {copied_file_path}.')

            logger.info(f'Wrote {copied_annotations} gold annotations in Annotation Collection {ac_gold.name}.')

            if create_goldstandard_settings['push_to_gitlab']:
                # upload gold annotations via git
                os.chdir(f'{self.project.projects_directory}{self.project.uuid}/collections/{gold_uuid}')
                subprocess.run(['git', 'add', '.'])
                subprocess.run(['git', 'commit', '-m', f'{create_goldstandard_settings["commit_message"]}'])
                subprocess.run(['git', 'push', 'origin', 'HEAD:master'])
                logger.info(f'Pushed gold standard annotation collection files to Catma backend.')

            os.chdir(cwd)

        if matches:
            _copy_matches_to_gold_ac(matches)
            return
        
        logger.info('No matches were found. Did not copy any annotations to gold standard annotation collection.')

        # überlegungen
        #
        # jede annotation einer ac mit jeder annotation der anderen acs abgleichen:
        #   überlappungen feststellen
        #       pro überlappung:
        #           wie stark ist die überlappung?
        #           gleiche klasse?
        #           gleiche kategorie?
        #           diskontinuierliche annotation beteiligt?

        def _test_overlap(
                df_row_1: pd.DataFrame,
                df_row_2: pd.DataFrame) -> bool:
            """Auxiliary function to execute annotation text segment comparison between 2 annotations.
            Annotation data is delivered in form of 2 Dataframes containing 1 row.
            Test is configured by dict in the methods create_goldstandard_settings parameter or in self.default_create_goldstandard_settings.
            
            Args:
                df_row_1 (pd.Dataframe): Data for single annotation containing start and end points of corresponding text segments.
                df_row_2 (pd.Dataframe): Data for single annotation containing start and end points of corresponding text segments.

            Returns:
                Bool: If the text criteria defined in the test setting dict are matched, it returns True.
            """
            # work in progress
            for df_1_index, df_1_text_pointer in enumerate(df_row_1.iloc[0]):
                for df_2_index, df_2_text_pointer in enumerate(df_row_2.iloc[0]):
                    pass

            return True

        # https://gitma.readthedocs.io/en/latest/class_project.html?highlight=gold#gitma.CatmaProject.create_gold_annotations
