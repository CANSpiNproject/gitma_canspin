import os
import math
from typing import Union, Dict, List, Tuple, Literal, Generator, Any

# defines some frequently used file paths
module_path: str = os.path.dirname(os.path.abspath(__file__))
abs_local_save_path: str = os.path.dirname(os.path.dirname(module_path))
projects_json_filepath: str = os.path.join(abs_local_save_path, "gui_configs", "projects.json")

# maps catma project names to corpora repo folders and languages
canspin_catma_projects: Dict[str, Union[Dict[Literal['corpora_folders'], List[str]], Dict[Literal['language'], Union[Literal['deu'], Literal['spa']]]]] = {
    'CATMA_5D2A90F0-4428-41CB-9D3A-E649CD1702C2_CANSpiN': 
        {
            'corpora_folders': ['canspin-deu-19', 'canspin-deu-20'], 
            'languages': ['deu']
        },
    'CATMA_3AA4ADC0-3C28-43F8-B5A0-9DCEFF23B90B_CANSpiN_Pilotanotationen_Spanisch': 
        {
            'corpora_folders': ['canspin-spa-19'], 
            'languages': ['spa']
        },
    'CATMA_3CA874CD-7E86-4FEA-9A33-0AB75CD9F374_CANSpiN_Annotationen_LAT19': 
        {
            'corpora_folders': ['canspin-lat-19'], 
            'languages': ['spa']
        },
    'CATMA_43E182B8-1908-413D-A1FE-EDDCDDE97A34_Space_DH_25': 
        {
            'corpora_folders': ['canspin-lat-19', 'canspin-spa-19'], 
            'languages': ['spa']
        },
    'CATMA_4AA4ADC0-4C28-54F9-B6A1-5DCEFF34B90B_DH2025_CANSpiN': 
        {
            'corpora_folders': ['canspin-deu-19', 'canspin-deu-20', 'canspin-lat-19', 'canspin-spa-19'], 
            'languages': ['deu', 'spa']
        }
}

# lists the column titles of annotation tsv files in the canspin project
canspin_annotation_tsv_columns: List[str] = [
    'Token_ID',
    'Text_Pointer',
    'Token',
    'Tag',
    'Annotation_ID',
    'Multi_Token_Annotation'
]

# maps annotation schema designations to a category and class system designation defined in AnnotationAnalyzer.category_and_class_systems
# different versions are not represented, it is assumed that always the newest version will be used
canspin_annotation_schema_mapping: Dict[str, Tuple[str]] = {
    'cs1': ('CS1 v1.1.0 deu', 'CS1 v1.1.0 spa'),
    'spaceAN': ('spaceAN v1.0.0')
}

# translation dicts for German to English and Spanish to Englisch,
# used in translate_dict function
key_translation: dict = {
    'CS1 v1.1.0 deu': {
        'Ort-Container': 'Place-Container',
        'Ort-Container-BK': 'Place-Container-MC',
        'Ort-Objekt': 'Place-Object',
        'Ort-Objekt-BK': 'Place-Object-MC',
        'Ort-Abstrakt': 'Place-Abstract',
        'Ort-Abstrakt-BK': 'Place-Abstract-MC',
        'Ort-ALT': 'Place-ALT',
        'Bewegung-Subjekt': 'Movement-Subject',
        'Bewegung-Objekt': 'Movement-Object',
        'Bewegung-Licht': 'Movement-Light',
        'Bewegung-Schall': 'Movement-Sound',
        'Bewegung-Geruch': 'Movement-Smell',
        'Bewegung-ALT': 'Movement-ALT',
        'Dimensionierung-Groesse': 'Dimensioning-Size',
        'Dimensionierung-Abstand': 'Dimensioning-Distance',
        'Dimensionierung-Menge': 'Dimensioning-Amount',
        'Dimensionierung-ALT': 'Dimensioning-ALT',
        'Positionierung': 'Positioning',
        'Positionierung-ALT': 'Positioning-ALT',
        'Richtung': 'Direction',
        'Richtung-ALT': 'Direction-ALT'
    },
    'CS1 v1.1.0 spa': {
        'Lugar-Contenedor': 'Place-Container',
        'Lugar-Contenedor-CM': 'Place-Container-MC',
        'Lugar-Objeto': 'Place-Object',
        'Lugar-Objeto-CM': 'Place-Object-MC',
        'Lugar-Abstracto': 'Place-Abstract',
        'Lugar-Abstracto-CM': 'Place-Abstract-MC',
        'Lugar-ALT': 'Place-ALT',
        'Movimiento-Sujeto': 'Movement-Subject',
        'Movimiento-Objeto': 'Movement-Object',
        'Movimiento-Luz': 'Movement-Light',
        'Movimiento-Sonido': 'Movement-Sound',
        'Movimiento-Olfato': 'Movement-Smell',
        'Movimiento-ALT': 'Movement-ALT',
        'Dimensionamiento-Tamaño': 'Dimensioning-Size',
        'Dimensionamiento-Distancia': 'Dimensioning-Distance',
        'Dimensionamiento-Cantitad': 'Dimensioning-Amount',
        'Dimensionamiento-ALT': 'Dimensioning-ALT',
        'Posicionamiento': 'Positioning',
        'Posicionamiento-ALT': 'Positioning-ALT',
        'Dirección': 'Direction',
        'Dirección-ALT': 'Direction-ALT'
    }
}

# helper functions
def makedir_if_necessary(directory: str) -> None:
    if not os.path.isdir(directory):
        os.makedirs(directory)

def dict_travel_generator(d: dict, type) -> Generator[Any, None, None]:
    for value in d.values():
        if isinstance(value, dict):
            yield from dict_travel_generator(value, type)
        elif isinstance(value, type):
            yield value

def reduce_decimal_place(f: float, length: int) -> float:
    length = 1 if length < 1 else length
    return math.floor(f * (10 ** length)) / (10 ** length)

def prevent_division_by_zero(a: int, b: int) -> Union[float, int]:
    return a / b if b else 0

def translate_dict(input: dict, translation: dict) -> dict:
    translated: dict = dict([(translation.get(k, k), v) for k, v in input.items()])
    for key, value in translated.items():
        if isinstance(value, dict):
            translated[key] = translate_dict(value, translation)
    return translated
