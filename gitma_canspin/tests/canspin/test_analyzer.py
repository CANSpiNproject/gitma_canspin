import pytest
import numpy as np
import pandas as pd
from gitma_canspin.canspin import AnnotationAnalyzer

class TestAnalyzer:
    def test_get_iaa(
            self,
            create_canspin_project_2acs):
        analyzer = AnnotationAnalyzer(imported_project=create_canspin_project_2acs.project)

        # value error test for missing list
        with pytest.raises(ValueError, match='There are less than two AnnotationCollections delivered to get_iaa method or they are not delivered inside a list.'):
            analyzer.get_iaa(annotation_collections=None)

        # value error test for insufficient ac amount in list
        with pytest.raises(ValueError, match='There are less than two AnnotationCollections delivered to get_iaa method or they are not delivered inside a list.'):
            analyzer.get_iaa(annotation_collections=[ac for ac in analyzer.project.annotation_collections if ac.name == 'Gold AC Gold-Annotation-Test'])

        # TODO: add more annotation collections to test data to test raise of value error in case the collections refer to different texts and tagsets

        # test gamma calculation result with default get_iaa_settings values
        result = analyzer.get_iaa(annotation_collections=analyzer.project.annotation_collections)
        assert isinstance(result, np.float32)
        assert result > 0.95 and result < 0.96

    def test_load_tsv_files(
            self,
            create_canspin_project_2acs):
        analyzer = AnnotationAnalyzer(imported_project=create_canspin_project_2acs.project)

        correct_tsv_filepath_list = ['canspin-deu-19/cs1-tsv/CANSpiN-deu-19_030_1-1-1.tsv']
        wrong_tsv_filepath_list = ['canspin-deu-19/CANSpiN-deu-19_030_1-1-1.tsv']
        correct_render_settings = {'category_and_class_system_name': 'CS1 v1.1.0 deu'}
        wrong_render_settings = {'category_and_class_system_name': 'CS1 v1.0.0 deu'}

        # value error tests for tsv_filepath_list argument is neither a dataframe nor a list of strings
        with pytest.raises(ValueError, match='Input data is neither a dataframe nor a list of strings.'):
            analyzer._load_tsv_files(tsv_filepath_list='', render_settings=correct_render_settings)
        with pytest.raises(ValueError, match='Input data is neither a dataframe nor a list of strings.'):
            analyzer._load_tsv_files(tsv_filepath_list=[], render_settings=correct_render_settings)
        with pytest.raises(ValueError, match='Input data is neither a dataframe nor a list of strings.'):
            analyzer._load_tsv_files(tsv_filepath_list=[1], render_settings=correct_render_settings)
        
        # file not found error test in case of passed tsv_filepath_list argument value error tests
        with pytest.raises(FileNotFoundError, match='A filepath given in the input data is not valid.'):
            analyzer._load_tsv_files(tsv_filepath_list=wrong_tsv_filepath_list, render_settings=correct_render_settings)

        # TODO: add value error tests for failed tsv data structures

        # value error test for the category and class system specified with the render_settings argument
        with pytest.raises(ValueError, match='The tsv file does contain tags which does not belong to the class system selected in the render settings.'):
            analyzer._load_tsv_files(tsv_filepath_list=correct_tsv_filepath_list, render_settings=wrong_render_settings)

        # correct return test in case a single tsv filepath is provided
        result = analyzer._load_tsv_files(tsv_filepath_list=correct_tsv_filepath_list, render_settings=correct_render_settings)
        assert isinstance(result, pd.DataFrame)
        assert len(result.index) == 199

    def test_get_corpus_annotation_statistics(
            self,
            create_canspin_project_2acs):
        analyzer = AnnotationAnalyzer(imported_project=create_canspin_project_2acs.project)

        default_corpus_annotation_statistics_result: dict = analyzer.get_corpus_annotation_statistics()
        corpus_annotation_statistics_result_with_text_borders: dict = analyzer.get_corpus_annotation_statistics(
            {
                'calculations': {
                    'amount_of_annotations': True,
                    'amount_of_annotations_by_class': True,
                    'amount_of_token': True,
                    'amount_of_annotated_token': True,
                    'amount_of_annotated_token_by_class': True,
                    'ratios': True,
                    'word_lists_by_class': True
                },
                'custom_grouping': None,
                'text_borders': (0, 100)
            }
        )
        corpus_annotation_statistics_result_with_custom_grouping: dict = analyzer.get_corpus_annotation_statistics(
            {
                'calculations': {
                    'amount_of_annotations': True,
                    'amount_of_annotations_by_class': True,
                    'amount_of_token': True,
                    'amount_of_annotated_token': True,
                    'amount_of_annotated_token_by_class': True,
                    'ratios': False,
                    'word_lists_by_class': True
                },
                'custom_grouping': {
                    'group_a': {
                        'subgroup': [('cs1', 'CANSpiN-deu-19_030_1-1-1.tsv')]
                    },
                    'group_b': [('cs1', 'CANSpiN-deu-19_030_1-1-1.tsv')]
                },
                'text_borders': None
            }
        )

        assert isinstance(default_corpus_annotation_statistics_result, dict)
        assert len(default_corpus_annotation_statistics_result) == 7
        assert 'cs1' in default_corpus_annotation_statistics_result['amount_of_token']
        assert 'canspin-deu-19' in default_corpus_annotation_statistics_result['amount_of_token']['cs1']
        assert 'CANSpiN-deu-19_030_1-1-1.tsv' in default_corpus_annotation_statistics_result['amount_of_token']['cs1']['canspin-deu-19']
        assert default_corpus_annotation_statistics_result['amount_of_token']['cs1']['canspin-deu-19']['CANSpiN-deu-19_030_1-1-1.tsv'] == 199
        assert 'cs1' in default_corpus_annotation_statistics_result['amount_of_annotated_token']
        assert 'canspin-deu-19' in default_corpus_annotation_statistics_result['amount_of_annotated_token']['cs1']
        assert 'CANSpiN-deu-19_030_1-1-1.tsv' in default_corpus_annotation_statistics_result['amount_of_annotated_token']['cs1']['canspin-deu-19']
        assert default_corpus_annotation_statistics_result['amount_of_annotated_token']['cs1']['canspin-deu-19']['CANSpiN-deu-19_030_1-1-1.tsv'] == 64
        assert 'cs1' in default_corpus_annotation_statistics_result['amount_of_annotated_token_by_class']
        assert 'canspin-deu-19' in default_corpus_annotation_statistics_result['amount_of_annotated_token_by_class']['cs1']
        assert 'CANSpiN-deu-19_030_1-1-1.tsv' in default_corpus_annotation_statistics_result['amount_of_annotated_token_by_class']['cs1']['canspin-deu-19']
        assert isinstance(default_corpus_annotation_statistics_result['amount_of_annotated_token_by_class']['cs1']['canspin-deu-19']['CANSpiN-deu-19_030_1-1-1.tsv'], dict)
        assert len(list(default_corpus_annotation_statistics_result['amount_of_annotated_token_by_class']['cs1']['canspin-deu-19']['CANSpiN-deu-19_030_1-1-1.tsv'].keys())) == 21

        assert isinstance(corpus_annotation_statistics_result_with_text_borders, dict)
        assert len(corpus_annotation_statistics_result_with_text_borders) == 7
        assert 'cs1' in corpus_annotation_statistics_result_with_text_borders['amount_of_token']
        assert 'canspin-deu-19' in corpus_annotation_statistics_result_with_text_borders['amount_of_token']['cs1']
        assert 'CANSpiN-deu-19_030_1-1-1.tsv' in corpus_annotation_statistics_result_with_text_borders['amount_of_token']['cs1']['canspin-deu-19']
        assert corpus_annotation_statistics_result_with_text_borders['amount_of_token']['cs1']['canspin-deu-19']['CANSpiN-deu-19_030_1-1-1.tsv'] == 100
        assert 'cs1' in corpus_annotation_statistics_result_with_text_borders['amount_of_annotated_token']
        assert 'canspin-deu-19' in corpus_annotation_statistics_result_with_text_borders['amount_of_annotated_token']['cs1']
        assert 'CANSpiN-deu-19_030_1-1-1.tsv' in corpus_annotation_statistics_result_with_text_borders['amount_of_annotated_token']['cs1']['canspin-deu-19']
        assert corpus_annotation_statistics_result_with_text_borders['amount_of_annotated_token']['cs1']['canspin-deu-19']['CANSpiN-deu-19_030_1-1-1.tsv'] == 35
        assert 'cs1' in corpus_annotation_statistics_result_with_text_borders['amount_of_annotated_token_by_class']
        assert 'canspin-deu-19' in corpus_annotation_statistics_result_with_text_borders['amount_of_annotated_token_by_class']['cs1']
        assert 'CANSpiN-deu-19_030_1-1-1.tsv' in corpus_annotation_statistics_result_with_text_borders['amount_of_annotated_token_by_class']['cs1']['canspin-deu-19']
        assert isinstance(corpus_annotation_statistics_result_with_text_borders['amount_of_annotated_token_by_class']['cs1']['canspin-deu-19']['CANSpiN-deu-19_030_1-1-1.tsv'], dict)
        assert len(list(corpus_annotation_statistics_result_with_text_borders['amount_of_annotated_token_by_class']['cs1']['canspin-deu-19']['CANSpiN-deu-19_030_1-1-1.tsv'].keys())) == 21

        assert isinstance(corpus_annotation_statistics_result_with_custom_grouping, dict)
        assert len(corpus_annotation_statistics_result_with_custom_grouping) == 6
        assert 'cs1' in corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotations']
        assert 'cs1' in corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotations_by_class']
        assert 'cs1' in corpus_annotation_statistics_result_with_custom_grouping['amount_of_token']
        assert 'cs1' in corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotated_token']
        assert 'cs1' in corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotated_token_by_class']
        assert 'cs1' in corpus_annotation_statistics_result_with_custom_grouping['word_lists_by_class']
        assert 'group_a' in corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotations_by_class']['cs1']
        assert 'group_a' in corpus_annotation_statistics_result_with_custom_grouping['amount_of_token']['cs1']
        assert 'group_a' in corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotated_token']['cs1']
        assert 'group_a' in corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotated_token_by_class']['cs1']
        assert 'group_a' in corpus_annotation_statistics_result_with_custom_grouping['word_lists_by_class']['cs1']
        assert 'subgroup' in corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotations']['cs1']['group_a']
        assert 'subgroup' in corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotations_by_class']['cs1']['group_a']
        assert 'subgroup' in corpus_annotation_statistics_result_with_custom_grouping['amount_of_token']['cs1']['group_a']
        assert 'subgroup' in corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotated_token']['cs1']['group_a']
        assert 'subgroup' in corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotated_token_by_class']['cs1']['group_a']
        assert 'subgroup' in corpus_annotation_statistics_result_with_custom_grouping['word_lists_by_class']['cs1']['group_a']
        assert 'CANSpiN-deu-19_030_1-1-1.tsv' in corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotations']['cs1']['group_a']['subgroup']
        assert 'CANSpiN-deu-19_030_1-1-1.tsv' in corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotations_by_class']['cs1']['group_a']['subgroup']
        assert 'CANSpiN-deu-19_030_1-1-1.tsv' in corpus_annotation_statistics_result_with_custom_grouping['amount_of_token']['cs1']['group_a']['subgroup']
        assert 'CANSpiN-deu-19_030_1-1-1.tsv' in corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotated_token']['cs1']['group_a']['subgroup']
        assert 'CANSpiN-deu-19_030_1-1-1.tsv' in corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotated_token_by_class']['cs1']['group_a']['subgroup']
        assert 'CANSpiN-deu-19_030_1-1-1.tsv' in corpus_annotation_statistics_result_with_custom_grouping['word_lists_by_class']['cs1']['group_a']['subgroup']
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotations']['cs1']['group_a']['subgroup']['CANSpiN-deu-19_030_1-1-1.tsv'] == 59
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotations']['cs1']['group_a']['subgroup']['TOTAL'] == 59
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotations']['cs1']['group_a']['TOTAL'] == 59
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotations']['cs1']['group_b']['TOTAL'] == 59
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotations']['cs1']['TOTAL'] == 118
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotations_by_class']['cs1']['group_a']['subgroup']['CANSpiN-deu-19_030_1-1-1.tsv']['Ort-Container'] == 9
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotations_by_class']['cs1']['group_a']['subgroup']['CANSpiN-deu-19_030_1-1-1.tsv']['Bewegung-Geruch'] == 0
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotations_by_class']['cs1']['group_a']['subgroup']['TOTAL']['Ort-Container'] == 9
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotations_by_class']['cs1']['group_a']['TOTAL']['Ort-Container'] == 9
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotations_by_class']['cs1']['group_b']['TOTAL']['Ort-Container'] == 9
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotations_by_class']['cs1']['TOTAL']['Ort-Container'] == 18
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_token']['cs1']['group_a']['subgroup']['CANSpiN-deu-19_030_1-1-1.tsv'] == 199
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_token']['cs1']['group_a']['subgroup']['TOTAL'] == 199
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_token']['cs1']['group_a']['TOTAL'] == 199
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_token']['cs1']['group_b']['TOTAL'] == 199
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_token']['cs1']['TOTAL'] == 398
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotated_token']['cs1']['group_a']['subgroup']['CANSpiN-deu-19_030_1-1-1.tsv'] == 64
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotated_token']['cs1']['group_a']['subgroup']['TOTAL'] == 64
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotated_token']['cs1']['group_a']['TOTAL'] == 64
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotated_token']['cs1']['group_b']['TOTAL'] == 64
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotated_token']['cs1']['TOTAL'] == 128
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotated_token_by_class']['cs1']['group_a']['subgroup']['CANSpiN-deu-19_030_1-1-1.tsv']['Ort-Container'] == 9
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotated_token_by_class']['cs1']['group_a']['subgroup']['CANSpiN-deu-19_030_1-1-1.tsv']['Bewegung-Geruch'] == 0
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotated_token_by_class']['cs1']['group_a']['subgroup']['TOTAL']['Ort-Container'] == 9
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotated_token_by_class']['cs1']['group_a']['TOTAL']['Ort-Container'] == 9
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotated_token_by_class']['cs1']['group_b']['TOTAL']['Ort-Container'] == 9
        assert corpus_annotation_statistics_result_with_custom_grouping['amount_of_annotated_token_by_class']['cs1']['TOTAL']['Ort-Container'] == 18
        assert isinstance(corpus_annotation_statistics_result_with_custom_grouping['word_lists_by_class']['cs1']['group_a']['subgroup']['CANSpiN-deu-19_030_1-1-1.tsv']['Ort-Container'], dict)
        assert len(corpus_annotation_statistics_result_with_custom_grouping['word_lists_by_class']['cs1']['group_a']['subgroup']['CANSpiN-deu-19_030_1-1-1.tsv']['Ort-Container']) == 9
        assert 'Stadtwald' in corpus_annotation_statistics_result_with_custom_grouping['word_lists_by_class']['cs1']['group_a']['subgroup']['CANSpiN-deu-19_030_1-1-1.tsv']['Ort-Container']
        assert 'TOTAL' in corpus_annotation_statistics_result_with_custom_grouping['word_lists_by_class']['cs1']
        assert 'TOTAL' in corpus_annotation_statistics_result_with_custom_grouping['word_lists_by_class']['cs1']['group_a']
        assert 'TOTAL' in corpus_annotation_statistics_result_with_custom_grouping['word_lists_by_class']['cs1']['group_a']['subgroup']
        assert len(corpus_annotation_statistics_result_with_custom_grouping['word_lists_by_class']['cs1']['group_a']['subgroup']['TOTAL']['Ort-Container']) == 9

        # TODO: add tests for ratios

        # TODO: add test for equivalence of results of calculation methods for annotation amount in a chapter,
        #       on the one hand with canspin tsv data dataframe:
        #
        #         new_df = tsv_data_df[tsv_data_df['Tag'].str.startswith('B')].drop_duplicates(subset=['Annotation_ID'])
        #
        #       on the other hand with gitma's annotation list dataframe:
        #
        #         annotation_collection_index: int = 0
        #         text_borders_for_chapter: Tuple[int, int] = (450, 42000)
        #         annotations_in_chapter: int = len(
        #             [
        #                 annotation for annotation in analyzer.project.annotation_collections[32].annotations \
        #                 if annotation.start_point > text_borders_for_chapter[0] and annotation.end_point > text_borders_for_chapter[0] and annotation.start_point < text_borders_for_chapter[1] and annotation.end_point < text_borders_for_chapter[1] \
        #                 and annotation.tag.name in ['Bewegung-Subjekt', 'Bewegung-Objekt']
        #             ]
        #         )

    # TODO: add tests for visualization methods
    