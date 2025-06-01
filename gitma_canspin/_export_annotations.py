import pandas as pd
import spacy
from lxml import etree
import re

from gitma_canspin.annotation import Annotation

from typing import Union, Tuple, List, Dict

import logging
logger = logging.getLogger(__name__)

def get_spacy_df(text: str, spacy_model_lang: str = 'German', nlp_max_text_len: int = None) -> pd.DataFrame:
    """Generates a table with the token and their position in the given text by using `spacy`.

    Args:
        text (str): Any text.
        spacy_model_lang (str, optional): a spacy model selected by language ('German', 'English', 'Multilingual', 'French', 'Spanish'). Defaults to 'German'.
        nlp_max_text_len (str, optional): a custom value for spacys max_length property defining how long a text could be which is to be tokenized. Defaults to None, spacys default value is 1000000.
        
    Returns:
        pd.DataFrame: `pandas.DataFrame` with 3 columns:\n
            - 'Token_ID': index of token in tokenized text
            - 'Token_Index': a text pointer for the start point of the token
            - 'Token': the token
    """
    def _fix_spanish_tokenization(loaded_model: spacy.Language) -> None:
        """Helper function to fix tokenization of spanish texts by adding recognition of leading hyphens as tokens.

        Args:
            loaded_model (spacy.Language): The model loaded with spacys load method whose tokenization you want to customize.
        """
        all_prefixes_re = spacy.util.compile_prefix_regex(tuple(list(nlp.Defaults.prefixes) + ['-','‐','˗','‒','–','—','―','−','─']))
        loaded_model.tokenizer.prefix_search = all_prefixes_re.search
    
    lang_dict = {
        'German': {'model': 'de_core_news_sm', 'customizations': None},
        'English': {'model': 'en_core_web_sm', 'customizations': None},
        'Multilingual': {'model': 'xx_ent_wiki_sm', 'customizations': None},
        'French': {'model': 'fr_core_news_sm', 'customizations': None},
        'Spanish': {'model': 'es_core_news_sm', 'customizations': _fix_spanish_tokenization}
    }
    
    try:
        nlp = spacy.load(lang_dict[spacy_model_lang]['model'])
    except OSError:
        logger.info('Downloading spacy model "' + lang_dict[spacy_model_lang]['model'] + '" for tokenization...')
        from spacy.cli import download
        download(lang_dict[spacy_model_lang]['model'])
        nlp = spacy.load(lang_dict[spacy_model_lang]['model'])
    if spacy_model_lang == "Multilingual":
        nlp.add_pipe("sentencizer")
    nlp.max_length = nlp_max_text_len if nlp_max_text_len else nlp.max_length
    
    if lang_dict[spacy_model_lang]['customizations']:
        lang_dict[spacy_model_lang]['customizations'](nlp)
    
    doc = nlp(text)

    tok_exp = nlp.tokenizer.explain(text)
    assert [t.text for t in doc if not t.is_space] == [t[1] for t in tok_exp]
    for t in tok_exp:
        logger.debug(f'{t[1]} --- {t[0]}')

    lemma_list = []

    for token in doc:
        lemma_list.append((
            token.i,          # Token ID
            token.idx,        # Start Pointer in Document
            token.text,       # Token
        ))

    columns = ['Token_ID', 'Text_Pointer', 'Token']
    return pd.DataFrame(lemma_list, columns=columns)

def to_stanford_tsv(
        ac,
        tags: list,
        file_name: str = None,
        spacy_model_lang: str = 'German') -> None:
    """Takes a CATMA `AnnotationCollection` and writes a tsv file which can be used to train a stanford NER model.
    Every token in the collection's text gets a tag if it lays in an annotated text segment. 

    Args:
        ac (gitma_canspin.AnnotationCollection): `AnnotationCollection` object
        tags (list): List of tags, that should be considered.
        file_name (str, optional): name of the tsv-file. Defaults to None.
        spacy_model_lang (str, optional): a spacy model selected by language ('German', 'English', 'Multilingual', 'French', 'Spanish'). Defaults to 'German'.
    """

    filtered_ac_df = ac.df[ac.df.tag.isin(tags)].copy()

    if len(filtered_ac_df) < 1:
        print(
            f"Couldn't find any annotations with given tags in AnnotationCollection {ac.name}")
    else:
        lemma_df = get_spacy_df(text=ac.text.plain_text,
                                spacy_model_lang=spacy_model_lang)
        tsv_tags = []
        for _, row in lemma_df.iterrows():
            l_df = filtered_ac_df[
                (filtered_ac_df['start_point'] <= row['Text_Pointer']) &
                (filtered_ac_df['end_point'] > row['Text_Pointer'])
            ].copy().reset_index(drop=True)

            if len(l_df) > 0:
                tsv_tags.append(l_df.tag[0])
            else:
                tsv_tags.append('O')

        lemma_df['Tag'] = tsv_tags

        lemma_df.to_csv(
            path_or_buf=f'{file_name}.tsv' if file_name else f'{ac.name}.tsv',
            sep='\t',
            index=False
        )

def create_basic_token_tsv(
        ac,
        created_file_name: str = 'basic_token_table',
        spacy_model_lang: str = 'German',
        text_borders: Union[Tuple[int, int], None] = None,
        nlp_max_text_len: Union[int, None] = None) -> None:
    """Takes a CATMA `AnnotationCollection` and writes a basic token tsv file with Token_ID, Text_Pointer and Token columns.

    Args:
        ac (gitma_canspin.AnnotationCollection): `AnnotationCollection` object
        created_file_name (str): name of the tsv file to be created. Defaults to 'basic_token_table'.
        spacy_model_lang (str, optional): a spacy model selected by language ('German', 'English', 'Multilingual', 'French', 'Spanish'). Defaults to 'German'.
        text_borders (tuple, optional): cut off delivered text by begin and end value of text string. Defaults to None.
        nlp_max_text_len (int, optional): specify spacys accepted max text length for tokenization. Defaults to None.
    """
    text = ac.text.plain_text[text_borders[0]:text_borders[1]] if text_borders else ac.text.plain_text

    lemma_df: pd.DataFrame = get_spacy_df(text=text,
                                          spacy_model_lang=spacy_model_lang,
                                          nlp_max_text_len=nlp_max_text_len)
        
    # keep linebreaks for tsv export
    lemma_df.loc[:, 'Token'] = lemma_df['Token'].apply(lambda x: x.replace('\n', '\\n'))

    lemma_df.to_csv(
        path_or_buf=f'{created_file_name}.tsv' if created_file_name else 'basic_token_table.tsv',
        sep='\t',
        index=False
    )

def create_annotated_token_tsv(
    ac,
    basic_token_file_name: str = 'basic_token_table',
    created_file_name: str = 'annotated_token_table',
    text_borders: Union[Tuple[int, int], None] = None,
    use_all_text_selection_segments: bool = True) -> None:
    """Takes a CATMA `AnnotationCollection` and basic token tsv file and writes a annotated token tsv file with Token_ID, Text_Pointer, Token, Tag, Annotation_ID and Multi_Token_Annotation columns.
    
    Args:
        ac (gitma_canspin.AnnotationCollection): `AnnotationCollection` object.
        basic_token_file_name (str): name of existing basic token tsv file.
        created_file_name (str): name of the tsv file to be created. Defaults to 'annotated_token_table'.
        text_borders (tuple, optional): cut off delivered text by begin and end value of text string. It must have the same value as it had when creating the delivered basic token tsv file.
        use_all_text_selection_segments (bool, optional): the parameter sets the processing mode for text selection segments. There are two processing modes: Consider all text selection segments of an annotation for the export (True: used for short, discontinuous annotations) or consider only the start and end point of an annotation and treat this as a single text selection segment, even if several segments are present in the data (False: used for longer, contiguous annotations). This mode distinction is necessary because CATMA divides longer, contiguous annotations internally into several text selection segments and this division should not be passed on to the exported data.
    """ 
    tsv_data_df: pd.DataFrame = pd.read_csv(filepath_or_buffer=f'{basic_token_file_name}.tsv', sep='\t')
    ac_data_df: pd.DataFrame = ac.df.copy()
    annotation_list: List[Annotation] = ac.annotations.copy()

    if use_all_text_selection_segments:
        ac_data_df['start_point'] = ac_data_df['start_point'].astype('object')
        ac_data_df['end_point'] = ac_data_df['start_point'].astype('object')

        for index, annotation in enumerate(annotation_list):
            start_points: List[int] = []
            end_points: List[int] = []
            for item in annotation.data['target']['items']:
                start_points.append(item['selector']['start'])
                end_points.append(item['selector']['end'])
            ac_data_df.at[index, 'start_point'] = start_points
            ac_data_df.at[index, 'end_point'] = end_points

        ac_data_df = ac_data_df.explode(['start_point', 'end_point'])

    new_iob2_tags: List[str] = []
    for _, row in tsv_data_df.iterrows():
        filtered_row_df_beginning: pd.DataFrame = ac_data_df[
            (ac_data_df['start_point'] == row['Text_Pointer'] + (text_borders[0] if text_borders else 0)) &
            ('\\n' not in row['Token'])
        ].copy().reset_index(drop=True)

        filtered_row_df_inner: pd.DataFrame = ac_data_df[
            (ac_data_df['start_point'] < row['Text_Pointer'] + (text_borders[0] if text_borders else 0)) &
            (ac_data_df['end_point'] > row['Text_Pointer'] + (text_borders[0] if text_borders else 0)) &
            ('\\n' not in row['Token'])
        ].copy().reset_index(drop=True)

        new_iob2_tag: str = (
            f'B-{filtered_row_df_beginning.tag[0]}' if len(filtered_row_df_beginning) else 
            (f'I-{filtered_row_df_inner.tag[0]}' if len(filtered_row_df_inner) else 'O')
        )

        new_iob2_tags.append(new_iob2_tag)

    tsv_data_df['Tag'] = new_iob2_tags

    annotation_ids: List[str] = []
    multi_token_annotation: List[int] = []

    for _, row in tsv_data_df.iterrows():
        if (row['Tag'] == 'O') or ('\\n' in row['Token']):
            annotation_ids.append('none')
            multi_token_annotation.append(0)
        else:
            filtered_row_df: pd.DataFrame = ac_data_df[
                (ac_data_df['start_point'] - (text_borders[0] if text_borders else 0) <= row['Text_Pointer']) &
                (ac_data_df['end_point'] - (text_borders[0] if text_borders else 0) > row['Text_Pointer'])
            ].copy()

            annotation_id = annotation_list[filtered_row_df.iloc[0].name].data['id'].split('/')[-1].split('_')[-1]

            found_token_indices: List[int] = [i for i, e in enumerate(annotation_ids) if e == annotation_id]
            amount_of_found_token: int = len(found_token_indices)

            multi_token_annotation = [e + 1 if i in found_token_indices else e for i, e in enumerate(multi_token_annotation)]
            multi_token_annotation_value = amount_of_found_token + 1

            annotation_ids.append(annotation_id)
            multi_token_annotation.append(multi_token_annotation_value)

    tsv_data_df['Annotation_ID'] = annotation_ids
    tsv_data_df['Multi_Token_Annotation'] = multi_token_annotation

    tsv_data_df.to_csv(
                path_or_buf=f'{created_file_name}.tsv' if created_file_name else 'annotated_token_table.tsv',
                sep='\t',
                index=False
            )

def create_annotated_tei(
    annotated_token_file_name: str = 'annotated_token_table',
    created_file_name: str = 'annotated_tei',
    insert_paragraphs: bool = True,
    paragraph_recognition_text_class: str = 'eltec-deu') -> None:
    """Takes an annotated token tsv file with Token_ID, Text_Pointer, Token, Tag, Annotation_ID and Multi_Token_Annotation columns and writes a tei xml file.
    
    Args:
        annotated_token_file_name (str): name of existing annotated token tsv file. Defaults to 'annotated_token_table'.
        created_file_name (str): name of the tei xml file to be created. Defaults to 'annotated_tei'.
        insert_paragraphs (bool): controls if file text is put directly into body element or in childen-p elements, if paragraphs were delivered originally when the text was imported into CATMA. Defaults to True.
        paragraph_recognition_text_class (str): selects a condition against which token are checked against in xml creation process to decide where a new paragraph begins. Defaults to 'eltec-deu'.
    """
    tsv_data_df = pd.read_csv(filepath_or_buffer=f'{annotated_token_file_name}.tsv', sep='\t', encoding='utf-8')

    TEI_NS = 'http://www.tei-c.org/ns/1.0'
    TEI = f'{{{TEI_NS}}}'

    CS1_NS = 'https://www.canspin.uni-rostock.de/ns/CS1/110'
    CS1 = f'{{{CS1_NS}}}'

    NSMAP = {None: TEI_NS, 'CS1': CS1_NS}

    tei_el = etree.Element(TEI + 'TEI', nsmap=NSMAP)
    tei_header_el = etree.SubElement(tei_el, TEI + 'teiHeader')
    text_el = etree.SubElement(tei_el, TEI + 'text')
    body_el = etree.SubElement(text_el, TEI + 'body')

    _paragraph_list: List[etree.Element] = []
    _last_sibling_element: Union[etree.Element, None] = None

    def _prettyprint(tree_or_element: Union[etree.ElementTree, etree.Element], fix_punctuation: bool = True) -> None:
        """Helper function to print a string representation of an etree Element or ElementTree.
        Used to print a string, which equals the output string saved to file.
        For debug purposes only.

        Args:
            tree_or_element (etree.Elementree or etree.Element): LXML xml element object.
            fix_punctuation (bool, optional): Apply punctuation correction function, which is also used when output string is saved to file.
        """
        xml = etree.tostring(element_or_tree=tree_or_element, pretty_print=True, xml_declaration=True, encoding='utf-8').decode()
        xml = _fix_punctuation(xml) if fix_punctuation else xml
        print(xml, end='')

    def _fix_punctuation(xml_string: str) -> str:
        """Helper function to delete spaces that were added to the string in the previous processing step 
        because punctuation marks are also tokens and tokens are usually seperated by spaces.

        Args:
            xml_string (str): Input string representation of xml tree or element.
        
        Returns:
            str: Input xml string with corrections applied.
        """
        corrections = [
            (r' \.', '.'),
            (r' ,', ','),
            (r' :', ':'),
            (r' ;', ';'),
            (r'» ', '»'),
            (r' «', '«'),
            (r' \?', '?'),
            (r' \!', '!'),
            (r' <\/p>', '</p>')
        ]

        for correction in corrections:
            xml_string = re.sub(correction[0], correction[1], xml_string)
        
        return xml_string

    def _paragraph_recognition(token: str, text_class: str) -> bool:
        """Helper function to apply different routines for paragraph recognition in xml creation process.
        Selecting a routing depends on text_class, which represents a specific way of encoding paragraphs in the projects plain text.

        Args:
            token (str): Token that is checked against conditions.
            text_class (str): Key that is mapped to a specific condition, which the token is checked against.

        Returns:
            bool: Result of checking token against the text_class specific condition.
        """

        # current patterns:
        # - eltec-deu: line breaks without a following space (or with only one space between punctuation marks or a few more)
        #              mark the end of a paragraph, whereas line breaks with 15 spaces following are line breaks within a paragraph

        patterns: Dict[str, bool] = {
            'eltec-deu': (('\\n' in token) and (len(token) < 10))
        }

        return patterns[text_class]

    # build header
    file_desc_el = etree.SubElement(tei_header_el, TEI + 'fileDesc')
    profile_desc_el = etree.SubElement(tei_header_el, TEI + 'profileDesc')
    revision_desc_el = etree.SubElement(tei_header_el, TEI + 'revisionDesc')

    # build body
    for idx, row in tsv_data_df.iterrows():
        if insert_paragraphs:
            if (idx == 0) or _paragraph_recognition(token=row['Token'], text_class=paragraph_recognition_text_class):
                _paragraph_list.insert(idx, etree.SubElement(body_el, TEI + 'p'))
                _last_sibling_element = None
        if '\\n' in row['Token']:
            continue
        if row['Tag'] != 'O':
            if row['Tag'].startswith('B-'):
                _last_sibling_element = etree.SubElement((_paragraph_list[-1] if insert_paragraphs else body_el), CS1 + row['Tag'][2:], attrib={CS1 + 'annotation': row['Annotation_ID']})
                if idx < (len(tsv_data_df.index) - 1):
                    if tsv_data_df.iloc[idx + 1]['Tag'].startswith('I-'):
                        _last_sibling_element.text = f"{row['Token']} " if _last_sibling_element.text is None else _last_sibling_element.text + f"{row['Token']} "
                    else:
                        _last_sibling_element.text = f"{row['Token']}" if _last_sibling_element.text is None else _last_sibling_element.text + f"{row['Token']}"
                        _last_sibling_element.tail = ' ' if _last_sibling_element.tail is None else _last_sibling_element.tail + ' '
                else:
                    _last_sibling_element.text = f"{row['Token']}" if _last_sibling_element.text is None else _last_sibling_element.text + f"{row['Token']}"
                    _last_sibling_element.tail = ' ' if _last_sibling_element.tail is None else _last_sibling_element.tail + ' '
            else:
                if idx < (len(tsv_data_df.index) - 1):
                    if tsv_data_df.iloc[idx + 1]['Tag'].startswith('I-'):
                        _last_sibling_element.text = f"{row['Token']} " if _last_sibling_element.text is None else _last_sibling_element.text + f"{row['Token']} "
                    else:
                        _last_sibling_element.text = f"{row['Token']}" if _last_sibling_element.text is None else _last_sibling_element.text + f"{row['Token']}"
                        _last_sibling_element.tail = ' ' if _last_sibling_element.tail is None else _last_sibling_element.tail + ' '
                else:
                    _last_sibling_element.text = f"{row['Token']}" if _last_sibling_element.text is None else _last_sibling_element.text + f"{row['Token']}"
                    _last_sibling_element.tail = ' ' if _last_sibling_element.tail is None else _last_sibling_element.tail + ' '
        else:
            if _last_sibling_element is not None:
                _last_sibling_element.tail = f"{row['Token']} " if _last_sibling_element.tail is None else _last_sibling_element.tail + f"{row['Token']} "
            else:
                if insert_paragraphs:
                    _paragraph_list[-1].text = f"{row['Token']} " if _paragraph_list[-1].text is None else _paragraph_list[-1].text + f"{row['Token']} "
                else:
                    body_el.text = f"{row['Token']} " if body_el.text is None else body_el.text + f"{row['Token']} "

    tree = etree.ElementTree(tei_el)
    tree_string = etree.tostring(element_or_tree=tree, pretty_print=True, xml_declaration=True, encoding='utf-8').decode()
    tree_string = _fix_punctuation(tree_string)

    with open(f'{created_file_name}.xml', 'w', encoding='utf-8') as export_file:
        export_file.write(tree_string)
