import logging

from typing import List, Tuple, Union

import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
from streamlit_annotation_tools import text_labeler

from subprocess import Popen
import os

from gitma_canspin._helper import abs_local_save_path
from gitma_canspin.canspin import AnnotationExporter

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logging.getLogger("streamlit.runtime.caching.cache_data_api").setLevel(logging.ERROR) # added to supress streamlit warning about selected cache module, originating from the way of starting the gui app

class Annotationexporter():
    def __init__(self, args) -> None:
        self.show(args)

    # init session state methods used in self.show
    def init_session_state(self) -> None:
        if not 'exporter_text' in st.session_state:
            st.session_state['exporter_text'] = """Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet."""

    # content methods used in self.show

    # core method for annotationexporter page display
    def show(self, args) -> None:
        # init session_state for projects page
        self.init_session_state()
        
        # create content of projects page
        st.write('# AnnotationExporter')
        labels = text_labeler(
            text=st.session_state['exporter_text'],
            labels={"text_borders": [{"start":6,"end":345,"label":"ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing"}]}
        )
        st.json(labels)
        # todo: add export configuration system (per tsv file to create) and add streamlit select element for selection existing configurations to use for export
        
        # content elements functionality

    # misc helper methods
    