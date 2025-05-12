from gitma_canspin import CatmaProject
from gitma_canspin.canspin import AnnotationExporter

class TestCanspinProjectInit:
    def test_create_project_instance(self, create_canspin_project_1ac):
        canspin_project = create_canspin_project_1ac
        assert isinstance(canspin_project.project, CatmaProject)

    def test_tsv_annotations_property(self, create_canspin_project_1ac):
        canspin_project = create_canspin_project_1ac
        assert isinstance(canspin_project.tsv_annotations, dict)
        assert 'cs1' in canspin_project.tsv_annotations
        assert len(canspin_project.tsv_annotations['cs1']) == 1

    def test_unify_plain_text_line_endings(self, create_canspin_project_1ac):
        auxiliary_exporter = AnnotationExporter(imported_project=create_canspin_project_1ac.project)
        extracted_text = auxiliary_exporter.test_text_borders(annotation_collection_index=0, text_borders=(898, 35443))
        assert (extracted_text.startswith('"Ein ansehnlicher Theil') and extracted_text.endswith('stoßende Schlafkammer."'))

    def test_get_text_border_values_by_string_search(self, create_canspin_project_1ac):
        canspin_project = create_canspin_project_1ac
        assert canspin_project.get_text_border_values_by_string_search(annotation_collection_index=0, substrings=('Ein ansehnlicher Theil der beiden Lausitzen', ', in die an die Wohnstube stoßende Schlafkammer.')) == (898, 35443)
