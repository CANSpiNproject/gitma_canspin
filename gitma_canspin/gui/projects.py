import logging

from typing import List, Union

import streamlit as st
import uuid
import json

from gitlab.exceptions import GitlabAuthenticationError
from gitlab.exceptions import GitlabConnectionError

from gitma_canspin.catma import Catma

from gitma_canspin._helper import projects_json_filepath

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logging.getLogger("streamlit.runtime.caching.cache_data_api").setLevel(logging.ERROR) # added to supress streamlit warning about selected cache module, originating from the way of starting the gui app

class Projects():
    def __init__(self, args) -> None:
        self.show(args)

    # content methods used in self.show
    # 1 - dialog modals
    @st.dialog("Create project")
    def create_project_dialog(self):
        short_project_name = st.text_input(
            label='Enter a project name', 
            help='Just a label in the gui app, any name is allowed here.', 
            key='create_project_dialog__short_project_name_value'
        )
        access_token = st.text_input(
            label='Enter a valid CATMA access token', 
            help='Allows access to the CATMA backend. If you do not have a token yet, login to https://app.catma.de, click on the avatar icon in the upper right corner and get an access token for your CATMA account.', 
            key='create_project_dialog__access_token_value'
        )
        full_project_name = st.empty()
        if access_token:
            with st.spinner('Downloading folder names ...'):
                folder_names_retrieval_result: Union[List[str], str] = self.get_folder_names_from_gitlab(access_token=access_token)
                if type(folder_names_retrieval_result) == str:
                    st.info(f'{folder_names_retrieval_result}', icon="🚫")
                else:
                    full_project_name.radio(
                        label='Select the folder name of your project', 
                        help='This folder list has been downloaded from the CATMA backend. Every folder belongs to a CATMA project you have access to with the access token provided. All the functionalities you find in the gitma_CANSpiN gui refer to a CATMA project and thus to the specific folder with documents and annotation collections you choose here.', 
                        key='create_project_dialog__full_project_name_value', 
                        options=folder_names_retrieval_result
                )
        submit_button = st.button(label='Save project', disabled=not 'create_project_dialog__full_project_name_value' in st.session_state)
        if submit_button and not self.input_check(short_project_name, access_token):
            st.info('Please provide valid input for the two text fields.', icon="🚫")
        if submit_button and self.input_check(short_project_name, access_token) and 'create_project_dialog__full_project_name_value' in st.session_state:
            self.submit_in_create_project_dialog()
            st.rerun()

    @st.dialog("Edit project")
    def edit_project_dialog(self):
        short_project_name = st.text_input(
            label='Enter a project name', 
            value=st.session_state['currently_loaded_project']['short_project_name'],
            help='Just a label in the gui app, any name is allowed here.', 
            key='edit_project_dialog__short_project_name_value'
        )
        access_token = st.text_input(
            label='Enter a valid CATMA access token', 
            value=st.session_state['currently_loaded_project']['access_token'],
            help='Allows access to the CATMA backend. If you do not have a token yet, login to https://app.catma.de, click on the avatar icon in the upper right corner and get an access token for your CATMA account.', 
            key='edit_project_dialog__access_token_value'
        )
        full_project_name = st.empty()
        with st.spinner('Downloading folder names ...'):
            folder_names_retrieval_result: Union[List[str], str] = self.get_folder_names_from_gitlab(access_token=access_token)
            if type(folder_names_retrieval_result) == str:
                st.info(f'{folder_names_retrieval_result}', icon="🚫")
            else:
                full_project_name.radio(
                    label='Select the folder name of your project', 
                    index=self.get_index_of_currently_selected_folder_name(folder_names_retrieval_result),
                    help='This folder list has been downloaded from the CATMA backend. Every folder belongs to a CATMA project you have access to with the access token provided. All the functionalities you find in the gitma_CANSpiN gui refer to a CATMA project and thus to the specific folder with documents and annotation collections you choose here.', 
                    key='edit_project_dialog__full_project_name_value', 
                    options=folder_names_retrieval_result
            )
        submit_button = st.button(label='Save project', disabled=not 'edit_project_dialog__full_project_name_value' in st.session_state)
        if submit_button and not self.input_check(short_project_name, access_token):
            st.info('Please provide valid input for the two text fields.', icon="🚫")
        if submit_button and self.input_check(short_project_name, access_token) and 'edit_project_dialog__full_project_name_value' in st.session_state:
            self.submit_in_edit_project_dialog()
            st.rerun()

    # core method for projects page display
    def show(self, args) -> None:       
        # create content of projects page
        st.write('# Projects')
        projects_container = st.container(border=True, key='projects_container')
        with projects_container:
            left, center, right = st.columns(3)
            with left:
                create_project_button = st.button(
                    label='Create', 
                    help='Create new project', 
                    type='primary', 
                    disabled=False, 
                    use_container_width=True, 
                    on_click=self.create_project_dialog
                )
            with center:
                edit_project_button = st.button(
                    label='Edit', 
                    help='Edit selected project', 
                    type='secondary' if not len(st.session_state['projects']) else 'primary', 
                    disabled=not len(st.session_state['projects']), 
                    use_container_width=True,
                    on_click=self.edit_project_dialog
                )
            with right:
                delete_project_button = st.button(
                    label='Delete', 
                    help='Delete selected project', 
                    type='secondary' if not len(st.session_state['projects']) else 'primary', 
                    disabled=not len(st.session_state['projects']), 
                    use_container_width=True,
                    on_click=self.delete_currently_loaded_project
                )
            select_project_box = st.selectbox(
                label='Select a CATMA project to gain access to gitma_CANSpiN functionalities. If no project exists, simply create one.',
                options=st.session_state['projects'],
                index=self.get_index_of_currently_loaded_project() if len(st.session_state['projects']) else 0,
                disabled=not len(st.session_state['projects']),
                format_func=lambda project: project['short_project_name'],
                key='selected_project',
                on_change=self.set_currently_loaded_project
            )
            # TODO: add access token check on startup if there are valid projects loaded on start
            if st.session_state['currently_loaded_project']:
                st.success(f"Project **{st.session_state['currently_loaded_project']['short_project_name']}** is selected:  \n\n*NAME*: {st.session_state['currently_loaded_project']['short_project_name']}  \n*FOLDER*: {st.session_state['currently_loaded_project']['full_project_name']}  \n*ACCESS TOKEN*: {st.session_state['currently_loaded_project']['access_token']}", icon="✅")
                st.success('You now can switch to other pages in the main menu and use the gitma_CANSpiN functionalities with the data of the selected project.  \nReturn to this page and select another project if you want to use the functionalities with data from another CATMA project.', icon="✅")
            else:
                st.info('Currently no project is selected.', icon="🚫")

            # st.write(f"Passed `start_state` argument from `gui_start` script: {args.start_state}")

    # misc helper methods
    def submit_in_create_project_dialog(self) -> None:
        dict_to_add: dict = {
            'id': self.get_unique_uuid_for_project(), 
            'short_project_name': st.session_state.create_project_dialog__short_project_name_value, 
            'full_project_name': st.session_state.create_project_dialog__full_project_name_value, 
            'access_token': st.session_state.create_project_dialog__access_token_value
        }
        st.session_state['projects'].append(dict_to_add)
        st.session_state['currently_loaded_project'] = st.session_state['projects'][-1]
        self.save_projects_to_json(st.session_state['projects'])
        if not st.session_state.selected_project:
            self.set_selected_project()

    def submit_in_edit_project_dialog(self) -> None:
        new_dict_values: dict = {
            'id': st.session_state['currently_loaded_project']['id'], 
            'short_project_name': st.session_state.edit_project_dialog__short_project_name_value, 
            'full_project_name': st.session_state.edit_project_dialog__full_project_name_value, 
            'access_token': st.session_state.edit_project_dialog__access_token_value
        }
        st.session_state['projects'][self.get_index_of_currently_loaded_project()] = new_dict_values
        st.session_state['currently_loaded_project'] = new_dict_values
        self.save_projects_to_json(st.session_state['projects'])

    def get_unique_uuid_for_project(self) -> str:
        id: str = str(uuid.uuid4())
        if len([project for project in st.session_state['projects'] if project['id'] == id]):
            id = self.get_unique_uuid_for_project()
        return id

    def delete_currently_loaded_project(self) -> None:
        st.session_state['projects'] = [project for project in st.session_state['projects'] if project['id'] != st.session_state['currently_loaded_project']['id']]
        st.session_state['currently_loaded_project'] = st.session_state['projects'][-1] if len(st.session_state['projects']) else None
        self.save_projects_to_json(st.session_state['projects'])

    def set_currently_loaded_project(self) -> None:
        st.session_state['currently_loaded_project'] = st.session_state.selected_project

    def set_selected_project(self) -> None:
        st.session_state.selected_project = st.session_state['currently_loaded_project']

    def get_index_of_currently_loaded_project(self) -> int:
        return [index for index, project in enumerate(st.session_state['projects']) if project['id'] == st.session_state['currently_loaded_project']['id']][0]

    def get_index_of_currently_selected_folder_name(self, folder_names: List[str]) -> int:
        return [index for index, folder_name in enumerate(folder_names) if folder_name == st.session_state['currently_loaded_project']['full_project_name']][0]

    def input_check(self, *args) -> bool:
        """Helper method to check if the given input strings consists of more than whitespace or nothing.
        Return False also when no argument has passed to the method.
        (The method might be extended with further checks in the future.)
        
        Args:
            args (Tuple[str]): a tuple of strings.
        
        Returns:
            Bool: True if the check has passed, False if the check fails.
        """
        if not args:
            return False      
        for arg in args:
            if not len(arg.strip()):
                return False
        return True
    
    def save_projects_to_json(self, projects: List[dict]):
        projects = projects if len(projects) else []
        with open(projects_json_filepath, 'w', encoding='utf-8') as file:
            json.dump(obj=projects, fp=file, ensure_ascii=False, indent=4)

    @st.cache_data
    def get_folder_names_from_gitlab(_self, access_token: str) -> Union[List[str], str]:
        """Helper method to display folder names of projects the user has access to by his:her access token.

        Args:
            access_token (str): The Catma access token which necessary to gain access to Catma's gitlab backend.
        
        Returns:
            Union[List[str], str]: If the access_token is valid, the list of folder names will be returned to which the user has access in Catma.
            If the authentification or the connection fails, the exceptions will be catched and error messages will be returned as strings.
        """
        try:
            catma = Catma(gitlab_access_token=access_token)
            project_folder_list: List[str] = [project_RESTobject.name for project_RESTobject in catma._gitlab_projects]
            return project_folder_list
        except GitlabAuthenticationError:
            return '401: Authentification failed. The access token provided is invalid.'
        except GitlabConnectionError:
            return '404: Connection failed. Currently there is no connection possible to the CATMA backend.'
    