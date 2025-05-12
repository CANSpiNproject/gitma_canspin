# gitma_CANSpiN
![version](https://img.shields.io/badge/version-1.6.2-blue)
[![License: GPL v2](https://img.shields.io/badge/License-GPL_v3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0.html)

*Read this file in different languages: [English](README.en.md)*

Das Repository dient der Anpassung von GitMA 2.0.1 für das CANSpiN-Projekt. Die angepasste Version steht als *gitma_canspin* hier als Python-Paket zur Verfügung und kann entsprechend in der Projekt-Pipeline für den Export, die Analyse, die Visualisierung und die Erstellung eines Goldstandards von Annotationen aus Catma genutzt werden.

## Anpassungen in GitMA
- *canspin*-Modul hinzugefügt mit `CanspinProject`-, `AnnotationExporter`-, `AnnotationAnalyzer` und `AnnotationManipulator`-Klasse
- *_helper*-Modul hinzugefügt
- *pytest*-Setup hinzugefügt
- *streamlit*-App zur Steuerung der Funktionen des *canspin*-Moduls in einer GUI hinzugefügt:
  - *gui_start*-Modul hinzugefügt
  - *gui*-Paket mit App-Modulen hinzugefügt
  - `gui-start`-Skript zum Start der Streamlit-App hinzugefügt
- `AnnotationCollection`-Klasse im *annotation_collection*-Modul und das *_export_annotations*-Modul angepasst:
  - `create_basic_token_tsv()` zur Klasse `AnnotationCollection` und im *_export_annotations*-Modul hinzugefügt
  - `create_annotated_token_tsv()` zur Klasse `AnnotationCollection` und im *_export_annotations*-Modul hinzugefügt
  - `create_annotated_tei()` zur Klasse `AnnotationCollection` und im *_export_annotations*-Modul hinzugefügt
  - `get_spacy_df()` im *_export_annotations*-Modul angepasst
  - `to_stanford_tsv()` in der Klasse `AnnotationCollection` und im *_export_annotations*-Modul angepasst
- `print_annotation_collections_list()` zur Klasse `CatmaProjekt` hinzugefügt
- `write_annotation_json_with_ac_object()` im *_write_annotation*-Modul hinzugefügt
- Dokumentation, Demos, Docker-Template entfernt

## Installation
### Voraussetzungen
- mindestens 2 GB freien Festplatten-Speicher
- Python 3.10 oder [Anaconda/Miniconda mit Python 3.10-Unterstützung](https://docs.anaconda.com/miniconda/system-requirements/)
- [Git](https://git-scm.com/downloads)

### Windows
- Erzeuge und aktivierte eine virtuelle Umgebung via `conda` mit Python 3.10: `conda create -n name_environment python=3.10` und `conda activate name_environment`.
- Klone das Repository in einen Projekt-Ordner: `git clone https://cls-gitlab.phil.uni-wuerzburg.de/canspin/gitma-canspin.git`.
- Wechsel im Terminal in den Repository-Ordner und installiere die benötigten Pakete und das Paket selbst: `pip install -r requirements.txt && pip install -e .`.
- Falls es Probleme mit dem Paket `cvxopt` gibt, installiere es via `conda` und der Paketresource `conda-forge`:
  - Füge `conda-forge` als Paketresource in dein `conda` ein: `conda config --add channels conda-forge`.
  - Setze die Priorität für den `conda-forge`-Channel: `conda config --set channel_priority strict`.
  - Installiere `cvxopt` via `conda`: `conda install cvxopt==1.3.2`.
  - Versuche erneut die Installation von `gitma_CANSpiN` wie in Schritt 3 beschrieben.

### Ubuntu
- Gehe analog zur Windows-Installation vor. Falls du kein `conda` verwenden möchtest, sondern beispielsweise `venv`, sorge dafür, Python in Version 3.10 zu benutzen.
- Falls es ohne `conda` zu Problemen mit dem Paket `cvxopt` kommt, fehlen wahrscheinlich Voraussetzungen, C- bzw. C++-Code zu compilen. Stelle sicher, dass die Build Essential-Pakete und das Python-Dev-Paket installiert sind: `sudo apt install python3-dev && sudo apt install build-essential`.

## Updates
Gibt es eine neue Version im Online-Repository, lade die Änderungen herunter (`git pull`). Der aktualisierte Stand ist danach sofort im pip-Paket verfügbar. Der Kernel eines bereits zuvor geladenes Jupyter Notebooks, was auf das Paket zugreift, müsste neugestartet werden. Einzig um auch die mit `pip list` angezeigte Versionsnummer zu aktualisieren, ist erneutes Ausführen von `pip install -e .` im Paket-Ordner notwendig.

## Testing
Die Unit- und Integration-Tests befinden sich im Moment im Aufbau. Um die Tests auszuführen, starte pytest im Paket-Ordner `gitma-canspin`: `pytest`.

## Getting started
Neben den folgenden Step-by-Step-Anweisungen und -Erläuterungen findet ihr im Repo `CANSpiN-scripts` im Ordner `Templates/gitma_canspin` bereits fertige Skripte und Jupyter Notebooks für verschiedene Aufgaben. Diese Dateien sind dafür vorgesehen, in den Projekt-Ordner kopiert und dort ausgeführt zu werden. Es müssen dafür zuvor notwendige Einstellungen in den Vorlagen vorgenommen werden, bevor sie funktionieren (unter anderem die Eingabe eines usergebundenen persönlichen Tokens für den Zugriff auf das CATMA-Backend und Dateinamen für den In- und Export).

Work in Progress: Momentan wird eine **Streamlit**-App dem Paket hinzugefügt, mit der alle Funktionen des *canspin*-Moduls in einer GUI benutzt werden können. Ist die virtuelle Umgebung aktiviert, kann die App von jedem Ordner aus im Terminal gestartet werden: `gui-start`.

Unabhängig des Hinweises auf die vorbereiteten Dateien im Repo `CANSpiN-scripts` und des Hinweises auf die Streamlit-App folgen nun Step-by-Step-Anweisungen zum Anlegen eigener Notebooks und Skripte. Zur Arbeit mit dem Paket sind momentan drei Klassen vorgesehen: [AnnotationExporter](#annotationexporter), [AnnotationAnalyzer](#annotationanalyzer) und [AnnotationManipulator](#annotationmanipulator). Alle drei sind darauf angewiesen, zunächst ein Catma-Projekt zu laden. Anhand des Ladens eines Exporters wird das im Folgenden demonstriert.

- Lege im Projekt-Ordner ein neues Python-Skript oder ein Jupyter Notebook an. So sollte die Ordnerstruktur aussehen:
    ```
    <Projekt-Ordner>
      <gitma-canspin>
      mein_skript.py
      mein_notebook.ipynb
    ```
- In der neuen Python-Datei: Importiere die `AnnotationExporter`-Klasse vom *canspin*-Modul des *gitma_canspin*-Pakets:
    ```python
    from gitma_canspin.canspin import AnnotationExporter
    ```
- Definiere die Initialisierungseinstellungen des Exporters, hier für das Catma-Projekt mit den deutschen CANSpiN-Texten:
    ```python
    my_exporter_init_settings = {
      'project_name': 'CATMA_5D2A90F0-4428-41CB-9D3A-E649CD1702C2_CANSpiN',
      'selected_annotation_collection': None,
      'load_from_gitlab': True,
      'gitlab_access_token': '<dein_access_token>'
    }
    ```
  - `project_name` (str, default: `'CATMA_5D2A90F0-4428-41CB-9D3A-E649CD1702C2_CANSpiN'`) ist in Catma definiert, entspricht dem Ordner-Namen des Projekts, der mit Hilfe einer Funktion im Anfangsbereich der oben genannten Jupyter Notebook-Templates im `CANSpiN-scripts`-Repo oder über den Login in das Catma-Backend ([https://git.catma.de](https://git.catma.de)) zu erfahren ist. Der Default-Wert ist der Ordner-Name des Catma-Projekts für die deutschen Texte im CANSpiN-Projekt.
  - `selected_annotation_collection` (str oder list\[str\], default: `None`) ermöglicht es gefiltert nach dem Namen von Annotation Collections gezielt nur eine Auswahl an Annotation Collections in den Exporter zu laden. Die gelieferten Strings müssen exakt den Namen der Annotation Collections entsprechen. Dies ist nur ein optionaler Schritt: Dem Befehl zum Ausführen des Exportierens (`exporter.run()`) wird als Argument ein Index-Wert übergeben, mit dem die zu exportierende Annotation Collection aus den im Exporter geladenen Collections ausgewählt wird. Mit Hilfe von `exporter.print_projects_annotation_collection_list()` kann man die Liste aller geladenen Collections anschauen und die entsprechenden Index-Werte erfahren. Durch das Filtern via den `filter_for_text`-Parameter kann hier ebenfalls die womöglich lange Liste an Annotation Collections auf die im Printout reduziert werden, die sich auf einen bestimmten Text beziehen. Zuvor kann via das `selected_annotation_collection`-Setting bereits beim Initialisieren des Exporters die Liste an Annotation Collections im Projekt initial für eine bessere Übersicht reduziert werden.
  - `load_from_gitlab` (bool, default: `False`) gibt an, ob die Daten vom Catma-Backend heruntergeladen oder lokal aus einem bereits heruntergeladenen Ordner (der sich dann im Projekt-Ordner befinden würde) verwendet werden soll. Standardmäßig wird nach einem lokalen Ordner im Projekt-Ordner gesucht. Wenn die Daten heruntergeladen werden sollen, wird der `gitlab_access_token` benötigt, um Zugriff auf die Projektdaten bei Catma zu bekommen, und der entsprechende Ordner mit den Daten im Projekt-Ordner angelegt.

      **ACHTUNG**: Falls die Daten schon einmal heruntergeladen worden sind, der Daten-Ordner im Projekt-Ordner also bereits existiert, führt erneutes Herunterladen zu einem Fehler: Der alte Ordner wird von *gitma* nicht überschrieben, sondern muss, wenn gewollt, zunächst händisch gelöscht werden. Ein vorhandenes lokales Projekt kann allerdings auch mit Hilfe der Methode `exporter.update_project()` aktualisiert werden ohne es löschen zu müssen: Lade den Exporter entsprechend mit `load_from_gitlab = False` und führe nach dem Laden die Update-Methode aus.
  - `gitlab_access_token` (str, default: `None`) ist der Schlüssel, mit dem die Daten vom Catma-Backend heruntergeladen werden können. Um einen Token von Catma zu bekommen, log dich in Catma ein, klicke rechts oben auf das Avatar-Symbol, wähle *Get Access Token*, folge den Hinweisen und füge den Token-String hier in die init-Settings ein.
- Erzeuge eine `AnnotationExporter`-Instanz mit den eben definierten Initialisierungseinstellungen:
    ```python
    exporter = AnnotationExporter(init_settings=my_exporter_init_settings)
    ```
    Wenn der Exporter korrekte Init-Werte bekommen hat und der Download des Projekts funktioniert hat, wird im Terminal eine Liste aller geladenen Annotation Collections angezeigt und die Ordnerstruktur sieht nun so aus:
    ```
    <Projekt-Ordner>
      <CATMA_5D2A90F0-4428-41CB-9D3A-E649CD1702C2_CANSpiN>
      <gitma-canspin>
      mein_skript.py
      mein_notebook.ipynb
    ```

Alle drei der im Folgenden genannten Klassen besitzen eine Klassenvariable `project`, in der das geladene Catma-Projekt als `CanspinProject`-Instanz gespeichert ist: `exporter.project`.

### AnnotationExporter
Die Klasse dient dem Export von CATMA-Annotationen in `.tsv`- und TEI-konforme `.xml`-Dateien. Dieser Schritt ist Teil der Projekt-Pipeline: die Vorbereitung der Annotationen zur Verwendung zum Training von Classifiern mittels NTEE.

#### Getting started
- Stelle in den Processing-Settings den Textausschnitt ein, der vom Dokument der zu exportierenden Annotation Collection ausgewählt werden soll: `exporter.processing_settings['text_borders'] = (420, 640)`. Die `text_borders` werden als Tupel übergeben. Du findest die für die einzelnen Kapitel eines Textes korrekten Werte in der Readme-Datei der Korpora. Um geeignete `text_borders`-Werte selbst zu ermitteln, benutze die Methode `exporter.get_text_border_values_by_string_search(annotation_collection_index=0, substrings=('Ein ansehnlicher Theil der beiden Lausitzen', 'an die Wohnstube stoßende Schlafkammer.'))`, um anhand von Textstellen am Beginn und Ende des gewünschten Textausschnittes die Werte ermitteln zu lassen. Um vor dem Export ermittelte Werte zu testen, verwende die Methode `exporter.test_text_borders(text_borders=(420,640), text_snippet_length=30, annotation_collection_index=0)`: Sie zeigt von der via `annotation_collection_index` gewählten Annotation Collection Textauschnitte der Länge `text_snippet_length` vom Anfangswert von `text_borders` ausgehend und zum Endwert von `text_borders` hingehend an. Da in den in CATMA geladenen Texten auch Metadaten des TEI-Headers sich befinden, ist dieser Schritt der `text_borders`-Ermittlung notwendig, ebenso, wenn nur die Annotationen eines speziellen Kapitels eines ganzen Textes exportiert werden sollen.
- Starte die Export-Pipeline. Achte dabei darauf, dass du, falls mehrere Annotation Collections geladen sind, du die gewünschte mit Hilfe des Parameters `annotation_collection_index` auswählst:
    ```python
    exporter.run(annotation_collection_index=0)
    ```
    Damit werden abgesehen von den `text_borders` die Standardeinstellungen (gespeichert in exporter.processing_settings) verwendet und drei Dateien im Projekt-Ordner erzeugt: `basic_token_table.tsv`, `annotated_token_table.tsv` und `annotated_tei.xml`.
    ```
    <Projekt-Ordner>
      <CATMA_5D2A90F0-4428-41CB-9D3A-E649CD1702C2_CANSpiN>
      <gitma-canspin>
      annotated_tei.xml
      annotated_token_table.tsv
      basic_token_table.tsv
      mein_skript.py
      mein_notebook.ipynb
    ```

#### Alle Einstellungsmöglichkeiten
- `exporter.processing_settings`:
  - `spacy_model_lang` (str, default: `'German'`) ist die Sprache des spacy-Sprachmodells, das verwendet wird, um den Text der ausgewählten Annotation Collection zu tokenisieren. Die Standard-Sprache ist `'German'` und offensichtlich entsprechend für deutsche Texte geeignet. Spacy-Sprachmodelle werden als pip-Pakete gehandhabt: Sollte das gewählte Modell noch nicht lokal installiert sein, wird es automatisch heruntergeladen. Wählt für spanische Texte die Einstellung `'Spanish'`.
  - `nlp_max_text_len` (int, default: `2000000`) gibt an, wie lang ein Text maximal sein darf, den spacy tokenisiert.
  - `text_borders` (tuple[int, int], default: `None`) erlaubt es, einen Textausschnitt des zur Annotation Collection gehörigen Textes zur Verarbeitung auszuwählen. Der korrekte Wert, um beispielsweise Kapitel 1 von DEU030 (Gustav Freytag: *Die verlorene Handschrift*) auszuwählen, wäre `(478, 42466)`. Um die Werte für einen gewünschten Textabschnitt zu ermittelt, kann die Methode `exporter.get_text_border_values_by_string_search(annotation_collection_index=0, substrings=('Ein ansehnlicher Theil der beiden Lausitzen', 'an die Wohnstube stoßende Schlafkammer.'))` verwendet werden, um anhand von Textstellen am Beginn und Ende des gewünschten Textausschnittes die Werte ermitteln zu lassen. Mit `exporter.test_text_borders(text_borders (tuple[int, int]), text_snippet_length (int), annotation_collection_index (int))` kann der Textabschnitt für einen bestimmten `text_borders`-Bereich ausgegeben werden, wobei `text_snippet_length` die Anzahl der gezeigten Zeichen an den Grenzen und `annotation_collection_index` den Index der auszuwählenden Annotation Collection angibt.
  - `insert_paragraphs` (bool, default: `True`) legt fest, ob beim Erzeugen von TEI Absätze (`<p></p>`) angelegt werden sollen.
  - `paragraph_recognition_text_class` (str, default: `'eltec-deu'`) bestimmt die Bedingungen, nach denen beim Erzeugen von TEI die einzelnen Token geprüft werden, um zu entscheiden, wo ein neuer Absatz beginnt. Aktuell gibt es folgende Klassen und daran gebundene Codierungen von Absatzwechseln im plain text:
    - `eltec-deu`: Zeilenumbrüche ohne nachfolgendes Leerzeichen (oder mit nur einem Leerzeichen zwischen Satzzeichen oder ein paar mehr) markieren das Ende eines Absatzes, während Zeilenumbrüche mit 15 Leerzeichen innerhalb eines Absatzes als Zeilenumbrüche gelten.
  - `use_all_text_selection_segments` (bool, default: `True`) stellt den Verarbeitungsmodus für Textauswahl-Segmente ein. Es gibt zwei Verarbeitungsmodi: Berücksichtige alle Textauswahl-Segmente einer Annotation für den Export (`True`: wird für kurze, diskontinuierliche Annotationen verwendet) oder berücksichtige nur den Start- und Endpunkt einer Annotation und behandle dies wie ein einziges Textauswahl-Segment, auch wenn mehrere Segmente in den Daten vorhanden sind (`False`: wird für längere, zusammenhängende Annotationen verwendet). Diese Modus-Unterscheidung ist für die Verarbeitung längerer Annotationen nötig, da CATMA längere zusammenhängende Annotationen intern in mehrere Textauswahl-Segmente unterteilt und diese Unterteilung nicht in die exportierten Daten übertragen werden soll.
- `exporter.steps`:
  - `create_basic_token_tsv`:
    - `activated` (bool, default: `True`): Aktiviere die Erzeugung einer basalen Token-Datei ohne Annotationen.
    - `output_tsv_file_name` (str, default: `'basic_token_table'`): Name der im Projekt-Ordner erzeugten Datei ohne Endung.
  - `create_annotated_token_tsv`:
    - `activated` (bool, default: `True`): Aktiviere die Erzeugung einer annotierten Token-Datei.
    - `input_tsv_file_name` (str, default: `'basic_token_table'`): Name der im Projekt-Ordner benötigten basalen Token-Datei ohne Annotationen.
    - `output_tsv_file_name` (str, default: `'annotated_token_table'`): Name der im Projekt-Ordner erzeugten Datei ohne Endung.
  - `create_annotated_tei`:
    - `activated` (bool, default: `True`): Aktiviere die Erzeugung einer annotierten XML-TEI-Datei.
    - `input_tsv_file_name` (str, default: `'annotated_token_table'`): Name der im Projekt-Ordner benötigten annotierten Token-Datei.
    - `output_tsv_file_name` (str, default: `'annotated_tei'`): Name der im Projekt-Ordner erzeugten Datei ohne Endung.

### AnnotationAnalyzer
Die Klasse dient dem Ermitteln von Statistiken aus und dem Erzeugen von Visualisierungen von TSV-Annotationsdaten und CATMA-Annotationen. Aktuell können Kreisdiagramme zur Mengendarstellung von Annotationsklassen-Instanzen erzeugt werden (`analyzer.render_overview_pie_chart()`) und Balkendiagramme zur Verteilungsdarstellung (`analyzer.render_progression_bar_chart()`). Eine Methode zur Ermittlung eines Inter-Annotator-Agreements anhand der Gamma-Metrik ausgehend von zwei oder mehreren Annotation Collections ist ebenfalls implementiert (`analyzer.get_iaa()`). Zudem können verschiedene statistische Kennwerte über geladene TSV-Annotationsdateien ermittelt werden (`analyzer.get_corpus_annotation_statistics()`). Für alle Methoden mit Ausnahme von `get_iaa()` ist es notwendig, dass die Korpus-Repositories sich im Projekt-Ordner befinden, da die TSV-Annotationsdaten mit der Initialisierung einer `AnnotationAnalyzer`-Instanz aus den Korpus-Repositorien geladen werden.

#### Getting started
tba

#### Weitere Einstellungsmöglichkeiten
tba

### AnnotationManipulator
Die Klasse dient dem Verändern oder Neuanlegen von CATMA-Annotationen. Eine Methode zur Erzeugung eines Goldstandards für die Annotation eines Dokuments ausgehend von vorhandenen Annotation Collections ist implementiert (`manipulator.create_gold_standard_ac()`), im Moment jedoch ausschließlich in einem strikten Modus: Annotationen müssen in Selektion und Klassifizierung exakt übereinstimmen, um in die Goldstandard-Collection übernommen zu werden.

#### Getting started
tba

#### Weitere Einstellungsmöglichkeiten
tba

