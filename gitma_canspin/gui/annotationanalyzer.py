import logging

from typing import List, Tuple, Union

import streamlit as st
import os

from gitma_canspin._helper import abs_local_save_path

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logging.getLogger("streamlit.runtime.caching.cache_data_api").setLevel(logging.ERROR) # added to supress streamlit warning about selected cache module, originating from the way of starting the gui app

class Annotationanalyzer():
    def __init__(self, args) -> None:
        self.show(args)

    # init session state methods used in self.show
    def init_session_state(self) -> None:
        pass

    # content methods used in self.show

    # core method for annotationanalyzer page display
    def show(self, args) -> None:
        # init session_state for projects page
        self.init_session_state()
        
        # create content of projects page
        st.write('# AnnotationAnalyzer')

        # content elements functionality

    # misc helper methods
    