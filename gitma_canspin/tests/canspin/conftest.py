import pytest
import os

from gitma_canspin.canspin import CanspinProject

@pytest.fixture(autouse=True)
def change_test_dir(request, monkeypatch):
    monkeypatch.chdir(request.fspath.dirname)

@pytest.fixture
def folder_cleanup(request):
    def inner_folder_cleanup():
        for filename in ['basic_token_table.tsv', 'annotated_token_table.tsv', 'annotated_tei.xml']:
            filepath = os.path.join(request.fspath.dirname, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
    return inner_folder_cleanup

@pytest.fixture
def create_canspin_project_1ac():
    return CanspinProject(init_settings={
        'project_name': 'CATMA_5D2A90F0-4428-41CB-9D3A-E649CD1702C2_CANSpiN',
        'selected_annotation_collection': 'Gold AC Gold-Annotation-Test',
        'load_from_gitlab': False,
        'gitlab_access_token': None
    })

@pytest.fixture
def create_canspin_project_2acs():
    return CanspinProject(init_settings={
        'project_name': 'CATMA_5D2A90F0-4428-41CB-9D3A-E649CD1702C2_CANSpiN',
        'selected_annotation_collection': ['Gold AC Gold-Annotation-Test', 'AC1 Gold-Annotation-Test'],
        'load_from_gitlab': False,
        'gitlab_access_token': None
    })
