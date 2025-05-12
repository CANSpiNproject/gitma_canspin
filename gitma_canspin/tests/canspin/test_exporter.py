import os
import csv
import codecs
from lxml import etree
from gitma_canspin.canspin import AnnotationExporter

class TestExporter:
    def test_test_text_borders(
            self,
            create_canspin_project_1ac):
        exporter = AnnotationExporter(imported_project=create_canspin_project_1ac.project)
        assert exporter.test_text_borders(annotation_collection_index=0, text_borders=(898, 901)) == '"Ein"'

    def test_complete_pipeline(
            self, 
            request, 
            create_canspin_project_1ac, 
            folder_cleanup):
        # create tsv and tei files
        exporter = AnnotationExporter(imported_project=create_canspin_project_1ac.project)
        exporter.processing_settings = {
            'spacy_model_lang': 'German',
            'nlp_max_text_len': 2000000,
            'text_borders': (898, 35443),
            'insert_paragraphs': True,
            'paragraph_recognition_text_class': 'eltec-deu',
            'use_all_text_selection_segments': True
        }
        exporter.run()

        # check tsv and tei files
        for filename in ['basic_token_table.tsv', 'annotated_token_table.tsv', 'annotated_tei.xml']:
            filepath = os.path.join(request.fspath.dirname, filename)
            assert os.path.exists(filepath)
        for filename in ['basic_token_table.tsv', 'annotated_token_table.tsv']:
            filepath = os.path.join(request.fspath.dirname, filename)
            with open(filepath) as file_stream:
                tsv_data = [row for row in csv.reader(file_stream, delimiter="\t")]
                assert tsv_data[0][0] == 'Token_ID'
                assert tsv_data[0][1] == 'Text_Pointer'
                assert tsv_data[0][2] == 'Token'
                assert tsv_data[1][0] == '0'
                assert tsv_data[1][1] == '0'
                assert tsv_data[1][2] == 'Ein'
        for filename in ['annotated_tei.xml']:
            filepath = os.path.join(request.fspath.dirname, filename)
            with codecs.open(filepath, 'r', encoding='utf-8', errors='ignore') as file_stream:
                root = etree.fromstring(file_stream.read().encode('utf-8'))
                assert root.tag == '{http://www.tei-c.org/ns/1.0}TEI'
                menge_elements = root.xpath('//CS1:Dimensionierung-Menge', namespaces={'CS1': 'https://www.canspin.uni-rostock.de/ns/CS1/110'})
                assert len(menge_elements) == 2
                assert menge_elements[0].get('{https://www.canspin.uni-rostock.de/ns/CS1/110}annotation') in ['ED4DC66A-AB87-11EF-946B-4E82A94C69C5', 'ED5FB49F-AB87-11EF-856F-4E82A94C69C5']
                assert menge_elements[1].get('{https://www.canspin.uni-rostock.de/ns/CS1/110}annotation') in ['ED4DC66A-AB87-11EF-946B-4E82A94C69C5', 'ED5FB49F-AB87-11EF-856F-4E82A94C69C5']

        # delete tsv and tei files
        folder_cleanup()
