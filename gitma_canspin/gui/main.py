import logging

from typing import List

import streamlit as st
import os
import json
from time import sleep

from gitma_canspin.gui.projects import Projects
from gitma_canspin.gui.annotationexporter import Annotationexporter
from gitma_canspin.gui.annotationanalyzer import Annotationanalyzer
from gitma_canspin.gui.annotationmanipulator import Annotationmanipulator

from gitma_canspin import __version__
from gitma_canspin._helper import abs_local_save_path, projects_json_filepath, makedir_if_necessary

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(name)s - %(levelname)s - %(message)s', level=logging.INFO)

class Main:
    def __init__(self, args) -> None:
        self.show(args)

    # init session state methods
    def init_session_state(self) -> None:
        # init 'current_main_menu_selection' variable
        if 'current_main_menu_selection' not in st.session_state:
            st.session_state['current_main_menu_selection'] = 0

        # init 'projects' variable and load saved projects from json file into it: List[dict] or []  
        if 'projects' not in st.session_state:
            st.session_state['projects'] = self.load_projects()
        
        # init 'currently_loaded_project' variable
        if 'currently_loaded_project' not in st.session_state:
            st.session_state['currently_loaded_project'] = st.session_state['projects'][0] if len(st.session_state['projects']) else None

    def load_projects(self) -> List[dict]:
        makedir_if_necessary(os.path.join(abs_local_save_path, 'gui_configs'))
        self.make_projects_config_if_necessary()
        with open(projects_json_filepath, 'r', encoding='utf-8') as file:
            return json.load(file)

    # content methods used in self.show
    def build_main_menu(self) -> None:
        st.sidebar.write('## Main Menu')
        with st.sidebar.container(border=True):
            st.button(
                label='Projects', 
                type='primary' if st.session_state['current_main_menu_selection'] == 0 else 'secondary', 
                on_click=self.change_page,
                args=(0,),
                key='main_menu_buttons_projects'
            )
            st.button(
                label='AnnotationExporter', 
                type='primary' if st.session_state['current_main_menu_selection'] == 1 else 'secondary', 
                disabled=not st.session_state['currently_loaded_project'],
                on_click=self.change_page,
                args=(1,),
                key='main_menu_buttons_annotationexporter'
            )
            st.button(
                label='AnnotationAnalyzer', 
                type='primary' if st.session_state['current_main_menu_selection'] == 2 else 'secondary', 
                disabled=not st.session_state['currently_loaded_project'],
                on_click=self.change_page,
                args=(2,),
                key='main_menu_buttons_annotationanalyzer'
            )
            st.button(
                label='AnnotationManipulator', 
                type='primary' if st.session_state['current_main_menu_selection'] == 3 else 'secondary', 
                disabled=not st.session_state['currently_loaded_project'],
                on_click=self.change_page,
                args=(3,),
                key='main_menu_buttons_annotationmanipulator'
            )

    def shutdown_GUI(self) -> None:
        st.info("GUI was closed. You can close the Browser Tab now.")
        logger.info("GUI was terminated.")
        sleep(1)
        os._exit(0)

    # core method for general app display settings and sidebar
    def show(self, args) -> None:
        # init general session_state for the app
        self.init_session_state()

        # set general layout
        st.set_page_config(layout="wide")

        # create sidebar content
        st.sidebar.write("# gitma_CANSpiN")
        st.sidebar.write("Version: " + __version__)
        st.sidebar.button(label="Shutdown GUI", on_click=self.shutdown_GUI)
        st.sidebar.divider()
        self.build_main_menu()

        # display page dependend on the sidebar menu selection
        match st.session_state['current_main_menu_selection']:
            case 0:
                Projects(args)
            case 1:
                Annotationexporter(args)
            case 2:
                Annotationanalyzer(args)
            case 3:
                Annotationmanipulator(args)
        
    # misc helper methods
    def change_page(self, index: int) -> None:
        st.session_state['current_main_menu_selection'] = index

    def make_projects_config_if_necessary(self) -> None:
        if not os.path.isfile(projects_json_filepath):
            with open(projects_json_filepath, 'w', encoding='utf-8') as f:
                json.dump(obj=[], fp=f, ensure_ascii=False, indent=4)
