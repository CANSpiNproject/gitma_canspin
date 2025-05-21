# gitma-CANSpiN
![version](https://img.shields.io/badge/version-1.6.4-blue)
[![License: GPL v3](https://img.shields.io/badge/License-GPL_v3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0.html)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15388462.svg)](https://doi.org/10.5281/zenodo.15388462)

The repository is used to adapt [GitMA](https://github.com/forTEXT/gitma) 2.0.1 for the CANSpiN project. The adapted version is available as a Python package here as *gitma_canspin* and can be used in the project pipeline for export, analysis, visualization and the creation of a gold standard of annotations from Catma.

**This package is still a work in progress and is currently not being tested for use in project scenarios other than the CANSpiN project. If you discover problems in your application scenario, please do not hesitate to contact us.**

## Customizations in GitMA
- added *canspin* module with the classes `CanspinProject`, `AnnotationExporter`, `AnnotationAnalyzer` and `AnnotationManipulator`
- added *_helper* module
- added *pytest* setup
- added a *streamlit* app to control the functions of the *canspin* module in a GUI:
  - added a *gui_start* module
  - added a *gui* package with app modules
  - added a `gui-start` script to start the streamlit app
- adjusted the `AnnotationCollection` class in the *annotation_collection* module and the *_export_annotations* module:
  - added `create_basic_token_tsv()` to the `AnnotationCollection` class and in the *_export_annotations* module
  - added `create_annotated_token_tsv()` to the `AnnotationCollection` class and in the *_export_annotations* module
  - added `create_annotated_tei()` to the `AnnotationCollection` class and in the *_export_annotations* module
  - adapted `get_spacy_df()` in the *_export_annotations* module
  - adepted `to_stanford_tsv()` in the `AnnotationCollection` class and in the *_export_annotations* module
- added `print_annotation_collections_list()` to the `CatmaProjekt` class
- added `write_annotation_json_with_ac_object()` in the *_write_annotation* module
- removed documentation, demos and docker template

## Installation
### Technical prerequisites
- at least 2 GB of free hard disk space
- Python 3.10 or [Anaconda/Miniconda with Python 3.10 support](https://docs.anaconda.com/miniconda/system-requirements/)
- [Git](https://git-scm.com/downloads)

### Windows
- Create and activate a virtual environment via `conda` with Python 3.10: `conda create -n name_environment python=3.10` and `conda activate name_environment`.
- Update `pip` and `setuptools`: `pip install -U pip setuptools`.
- Clone the repository into a project folder: `git clone https://github.com/CANSpiNproject/gitma_canspin.git`.
- Change to the repository folder in the terminal and install the necessary packages as well as the packages itself: `pip install -e .`.
- If there are problems with the `cvxopt` package, install it via `conda` and the package resource `conda-forge`:
  - Add `conda-forge` as a package resource in your `conda`: `conda config --add channels conda-forge`.
  - Set the priority for the `conda-forge` channel: `conda config --set channel_priority strict`.
  - Install `cvxopt` via `conda`: `conda install cvxopt==1.3.2`.
  - Retry installing `gitma_CANSpiN` as described in step 4.

### Ubuntu
- Proceed in the same way as for the Windows installation. If you do not want to use `conda`, but `venv`, for example, make sure you use Python version 3.10.
- If you use a non-`conda` installation and you encounter problems with the `cvxopt` package, you probably lack the prerequisites to compile C or C++ code. Make sure you have the Build Essential packages and the Python-Dev package installed: `sudo apt install python3-dev && sudo apt install build-essential`.

## Updates
If there is a new version in the online repository, download the changes (`git pull`). The updated state is then immediately available in the pip package. The kernel of a previously loaded Jupyter Notebook accessing the package would need to be restarted. Only to update the version number displayed with `pip list` is it necessary to re-execute `pip install -e .` in the package folder.

## Testing
The unit and integration tests are currently being developed. To run the tests, install the optional testing packages in the repository folder `gitma-canspin`: `pip install -e .[testing]`. After that, you can start pytest from the same folder: `pytest`.

## Getting started
The package *gitma_canspin* is designed to handle multi-class annotations, i.e. every token of a text can only be assigned to one class. Based on that, you can use *gitma_canspin* for exporting [Catma](https://catma.de/) annotation data into `.tsv` and TEI-conform `.xml` files with inline annotations, for computing statistical data about annotations, creating visualizations, calculating inter-annotator agreements and creating goldstandard annotation collections.

Currently, a **Streamlit** app is being added to the package that allows all the features of the *canspin* module to be used in a GUI. Once the virtual environment is activated, the app can be started from every folder in the terminal: `gui-start`. Independently of the reference to the Streamlit app, step-by-step instructions for creating your own Jupyter Notebooks and scripts now follow. Three classes are currently provided for working with the package: [AnnotationExporter](#annotationexporter), [AnnotationAnalyzer](#annotationanalyzer) and [AnnotationManipulator](#annotationmanipulator). All three depend on a Catma project being loaded first. This is demonstrated below using the loading of an exporter.

- To code along, first of all place the folders of the [DH2025 repository](https://github.com/CANSpiNproject/dh2025.git) inside your project folder. Then create a new Python script or a Jupyter Notebook in the project folder. The folder structure should look like this:
    ```
    <project folder>
      <CATMA_4AA4ADC0-4C28-54F9-B6A1-5DCEFF34B90B_DH2025_CANSpiN>
      <canspin-deu-19>
      <canspin-deu-20>
      <canspin-spa-19>
      <canspin-lat-19>
      <gitma-canspin>
      <results>
      my_script.py
      my_notebook.ipynb
    ```
- In the new Python file: Import the `AnnotationExporter` class from *canspin* module of *gitma_canspin*:
    ```python
    from gitma_canspin.canspin import AnnotationExporter
    ```
- Define the initialization settings for the exporter, here for the Catma project DH2025 CANSpiN data:
    ```python
    my_exporter_init_settings = {
      'project_name': 'CATMA_4AA4ADC0-4C28-54F9-B6A1-5DCEFF34B90B_DH2025_CANSpiN',
      'selected_annotation_collection': None,
      'load_from_gitlab': False,
      'gitlab_access_token': None
    }
    ```
  - `project_name` (str, default: `'CATMA_4AA4ADC0-4C28-54F9-B6A1-5DCEFF34B90B_DH2025_CANSpiN'`) is defined in Catma and corresponds to the folder name of a project, which can be obtained by logging into the Catma backend ([https://git.catma.de](https://git.catma.de)), if you have a Catma account. The default value is the folder name of the Catma project for the DH2025 data of the CANSpiN project.
  - `selected_annotation_collection` (str or list\[str\], default: `None`) allows you to filter by the name of annotation collections to load only a selection of annotation collections into the exporter. The delivered strings must match exactly the names of the annotation collections. This is only an optional step: The command for executing the export (`exporter.run()`) uses an index value as an argument, which is needed to select the annotation collection to be exported from the collections loaded in the exporter. With the help of `exporter.print_projects_annotation_collection_list()`, you can view the list of all loaded collections and find out the corresponding index values. By filtering via the `filter_for_text` parameter, the possibly long list of annotation collections can also be reduced to those in the printout that refer to a specific text. Previously, the list of annotation collections in the project can already be reduced for a better overview when initializing the exporter via the `selected_annotation_collection` setting.
  - `load_from_gitlab` (bool, default: `False`) indicates whether the data should be downloaded from the Catma backend or used locally from an already downloaded folder (which would then be located in the project folder). By default, a local folder in the project folder is being searched for. If the data is to be downloaded, the `gitlab_access_token` is required to get access to the project data at Catma, and the corresponding folder with the data is created in the project folder.

      **ATTENTION**: If the data has already been downloaded, i.e. the data folder already exists in the project folder, downloading again will raise an error: The old folder will not be overwritten by *gitma*, but must first be deleted manually if desired. An existing local project can, however, also be updated without deleting the existing one using the method `exporter.update_project()`: Load the exporter accordingly with `load_from_gitlab = False` and then run the update method after loading.
  - `gitlab_access_token` (str, default: `None`) is the key that allows you to download data from the Catma backend. To get a token from Catma, login into Catma, click on the avatar icon in the upper right corner, select *Get Access Token*, follow the instructions and insert the token string into the init settings here.
- Create an `AnnotationExporter` instance with the initialization settings we just defined:
    ```python
    exporter = AnnotationExporter(init_settings=my_exporter_init_settings)
    ```
    If the exporter has received the correct init values, a list of all loaded annotation collections of the project `CATMA_4AA4ADC0-4C28-54F9-B6A1-5DCEFF34B90B_DH2025_CANSpiN` is displayed in the terminal. In addition, all TSV annotation data of the folders `canspin-deu-19/cs1-tsv`, `canspin-deu-20/cs1-tsv`, `canspin-spa-19/cs1-tsv`, and `canspin-lat-19/cs1-tsv` is loaded. You can check it by executing the line:
    ```python
    exporter.print_tsv_annotations_overview()
    ```
    To get the list of the loaded Catma Annotation Collections execute:
    ```python
    exporter.print_projects_annotation_collection_list()
    ```
    Here you can see the annotation indices, which will are necessary to know for the export. We want to export the collection `Nils -- CS1 V.1.1.0 (Gold:1-1-1)` refering to the document `DEU-19_030`. Its index should be `4`.

All three of the classes described below have a class property `project` in which the loaded Catma project is stored as a `CanspinProject` instance:
```python
exporter.project
```

### AnnotationExporter
This class is designed to export CATMA annotations into `.tsv` and TEI-conform `.xml` files. This step is part of the project pipeline: preparing the annotations for usage in training classifiers.

#### Getting started
- In the processing settings, select the text segment that is to be selected from the document of the annotation collection to be exported:
    ```python
    exporter.processing_settings['text_borders'] = (478, 42466)
    exporter.processing_settings
    ```
    The `text_borders` are passed as tuples. To determine suitable `text_borders` values yourself or to test them before exporting, use the method `exporter.get_text_border_values_by_string_search(annotation_collection_index=0, substrings=('Ein ansehnlicher Theil der beiden Lausitzen', 'an die Wohnstube stoßende Schlafkammer.'))`, which can be used to determine the `text_borders` values by delivering text passages of the beginning and the end of the desired text segment. Furthermore you can use `exporter.test_text_borders(text_borders=(420,640), text_snippet_length=30, annotation_collection_index =0)` to test the determined values: It displays text snippets of length `text_snippet_length` from the starting value of `text_borders` and towards the end value of `text_borders` from the annotation collection selected via `annotation_collection_index`. Overall, the step of determining text_borders values is necessary because the texts loaded into CATMA also contain metadata from the TEI header. It is also necessary if only the annotations of a specific chapter of a whole text are to be exported.
- Start the export pipeline. If multiple annotation collections are loaded, make sure to select the desired one using the `annotation_collection_index` parameter. In our example, we want to export :
    ```python
    exporter.run(annotation_collection_index=4)
    ```
    With this, apart from the `text_borders`, the default settings (stored in exporter.processing_settings) are used and three files are created in the project folder: `basic_token_table.tsv`, `annotated_token_table.tsv` and `annotated_tei.xml`.
    ```
    <project folder>
      <CATMA_4AA4ADC0-4C28-54F9-B6A1-5DCEFF34B90B_DH2025_CANSpiN>
      <canspin-deu-19>
      <canspin-deu-20>
      <canspin-spa-19>
      <canspin-lat-19>
      <gitma-canspin>
      <results>
      annotated_tei.xml
      annotated_token_table.tsv
      basic_token_table.tsv
      my_script.py
      my_notebook.ipynb
    ```

#### All configuration options
- `exporter.processing_settings`:
  - `spacy_model_lang` (str, default: `'German'`) is the language of the spacy language model used to tokenize the text of the selected annotation collection. The default language is `'German'` and is obviously suitable for German texts. Spacy language models are handled as pip packages: if the selected model is not yet installed locally, it will be downloaded automatically. Select `'Spanish'` for Spanish texts.
  - `nlp_max_text_len` (int, default: `2000000`) indicates the maximum length of a text that spacy tokenizes.
  - `text_borders` (tuple[int, int], default: `None`) allows you to select a text snippet from the text belonging to the annotation collection for processing. For example, the correct value for selecting chapter 1 of DEU030 (Gustav Freytag: *Die verlorene Handschrift*) would be `(478, 42466)`. To determine the values for a desired text segment, the method `exporter.get_text_border_values_by_string_search(annotation_collection_index=0, substrings=('Ein ansehnlicher Theil der beiden Lausitzen', 'an die Wohnstube stoßende Schlafkammer.'))` can be used. Furthermore there is a method `exporter.test_text_borders(text_borders (tuple[int, int]), text_snippet_length (int), annotation_collection_index (int))` returns the text snippet for a given `text_borders` area, where `text_snippet_length` indicates the number of characters shown at the borders and `annotation_collection_index` indicates the index of the annotation collection to select.
  - `insert_paragraphs` (bool, default: `True`) determines whether paragraphs (`<p></p>`) should be created when generating TEI.
  - `paragraph_recognition_text_class` (str, default: `'eltec-deu'`) determines the conditions by which the individual tokens are checked when creating TEI to decide where a new paragraph begins. Currently, there are the following classes and associated encodings of paragraph breaks in plain text:
    - `eltec-deu`: line breaks without a following space (or with only one space between punctuation marks or a few more) mark the end of a paragraph, while line breaks with 15 spaces within a paragraph are considered line breaks.
  - `use_all_text_selection_segments` (bool, default: `True`) sets the processing mode for text selection segments. There are two processing modes: consider all text selection segments of an annotation for export (`True`: used for short, discontinuous annotations) or consider only the start and end points of an annotation and treat this as a single text selection segment, even if there are several segments in the data (`False`: used for longer, contiguous annotations). This mode distinction is necessary for processing longer annotations, since CATMA divides longer contiguous annotations internally into several text selection segments and this division should not be transferred to the exported data.
- `exporter.steps`:
  - `create_basic_token_tsv`:
    - `activated` (bool, default: `True`): Activate the generation of a basal token file without annotations.
    - `output_tsv_file_name` (str, default: `'basic_token_table'`): Name of the file created in the project folder without the extension.
  - `create_annotated_token_tsv`:
    - `activated` (bool, default: `True`): Activate the creation of an annotated token file.
    - `input_tsv_file_name` (str, default: `'basic_token_table'`): Name of the basal token file without annotations required in the project folder.
    - `output_tsv_file_name` (str, default: `'annotated_token_table'`): Name of the file created in the project folder without the extension.
  - `create_annotated_tei`:
    - `activated` (bool, default: `True`): Activate the generation of an annotated XML TEI file.
    - `input_tsv_file_name` (str, default: `'annotated_token_table'`): Name of the annotated token file required in the project folder.
    - `output_tsv_file_name` (str, default: `'annotated_tei'`): Name of the file created in the project folder without the extension.

### AnnotationAnalyzer
The class is used to determine statistics from and generate visualizations of TSV and CATMA annotations. Currently, pie charts can be generated to show the quantity of annotation class instances (`analyzer.render_overview_pie_chart()`) and bar charts to show the distribution (`analyzer.render_progression_bar_chart()`). A method for determining an inter-annotator agreement based on the gamma metric using two or more annotation collections is also implemented (`analyzer.get_iaa()`). In addition, various statistical values can be determined using loaded annotation tsv files (`analyzer.get_corpus_annotation_statistics()`). All methods except `get_iaa()` require the corpus repositories to be located in the project folder, as the TSV data in it is loaded from these repositories on initialization of the `AnnotationAnalyzer` instance.

#### Getting started
tba

#### All configuration options
tba

### AnnotationManipulator
The class is used to modify or create CATMA annotations. A method for creating a gold standard for the annotation of a document based on existing annotation collections is implemented (`manipulator.create_gold_standard_ac()`), but at the moment only in a strict mode: Annotations must exactly match in selection and classification in order to be included in the gold standard collection.

#### Getting started
tba

#### All configuration options
tba
