import copy
import pickle
import random
from pathlib import Path

import streamlit as st
import torch

from db.load_data import DatasetEntry
from model.module import CoverModel, load_cover_model
from model.tensor import parse_output_tensor, parse_input_tensor, convert_from_prediction
from util import const
from datetime import datetime

class ModelDisplay:

    selected_entry_index: int
    selected_entry: DatasetEntry
    selected_datetime: datetime
    mutable_entry: DatasetEntry = None
    eval_mode: bool = False
    show_db_results: bool = False
    model: CoverModel

    def __init__(self):

        data_file = Path(const.TRAINING_SAVE_PATH)
        model_file = Path(const.MODEL_SAVE_PATH)
        if not data_file.exists():
            raise FileNotFoundError(f"Model input file {data_file} not found.")
        if not model_file.exists():
            raise FileNotFoundError(f"Model parameter file {data_file} not found.")
        # Load the data file from disk
        with open(data_file, 'rb') as f:
            self.data_dict: dict[datetime, DatasetEntry] = pickle.load(f)
            self.model: CoverModel = load_cover_model(str(model_file))

        self.selected_entry_index = 0
        self.pick_entry(self.selected_entry_index)


    def get_random_entry(self):
        index = random.randint(0, len(self.data_dict) - 1)
        self.pick_entry(index)

    def pick_entry(self, entry_index: int):
        self.selected_entry_index = entry_index
        self.selected_entry = list(self.data_dict.values())[self.selected_entry_index]
        self.selected_datetime = list(self.data_dict.keys())[self.selected_entry_index]
        #set the session state to the values we picked.
        print(f"ERROR TESTING {self.selected_datetime}")
        st.session_state.dtpicker = self.selected_datetime
        st.session_state.elevation = self.selected_entry.sun_data.elevation
        st.session_state.azimuth = self.selected_entry.sun_data.azimuth
        st.session_state.temperature = self.selected_entry.weather_data.temperature
        st.session_state.cc = self.selected_entry.weather_data.cloud_coverage
        for key,is_home in self.selected_entry.person_data.person_states.items():
            st.session_state[key] = is_home
        for val in self.selected_entry.temperature_data.values():
            st.session_state[val.entity_id] = val.temperature

        self.set_eval_mode(False)
        #set the db results only if we are not showing model results.
        if self.show_db_results:
            print("Showing DB results")
            self.evaluate_db_results()
        else:
            #show the model results.
            print("Showing Model results")
            self.evaluate_model_results()

    def evaluate_db_results(self):
        for val in self.selected_entry.shutter_data.values():
            st.session_state[f"{val.entity_id}_pos"] = val.position
            st.session_state[f"{val.entity_id}_tilt"] = val.tilt_position

    def evaluate_model_results(self):
        if self.show_db_results:
            return
        tensor_parse: dict[datetime, DatasetEntry] = {self.selected_datetime: self.selected_entry}
        in_tensor = parse_input_tensor(tensor_parse)
        with torch.no_grad():
            pred = self.model(in_tensor)
            print(f"Model prediction: {pred}")
            new_shutters = convert_from_prediction(pred, self.model.data_schema)
            for shutter in new_shutters:
                st.session_state[f"{shutter.entity_id}_pos"] = shutter.position
                st.session_state[f"{shutter.entity_id}_tilt"] = shutter.tilt_position

    def toggle_eval_mode(self):
        enabled = st.session_state["eval_mode"]
        self.set_eval_mode(enabled)

    def set_eval_mode(self, enabled: bool):
        if enabled == self.eval_mode:
            return
        if st.session_state.eval_mode != enabled:
            st.session_state.eval_mode = enabled
        self.eval_mode = enabled
        if self.eval_mode:
            self.set_show_db_results(False)
            #we need to deep copy the object for modification.
            self.mutable_entry = copy.deepcopy(self.selected_entry)
            self.selected_entry = self.mutable_entry
        else:
            del self.mutable_entry
            self.pick_entry(self.selected_entry_index)

    def toggle_db_results(self):
        show = st.session_state["db_results"]
        self.set_show_db_results(show)

    def set_show_db_results(self, show: bool):
        if show == self.show_db_results:
            return
        if st.session_state.db_results != show:
            st.session_state.db_results = show
        self.show_db_results = show

        if self.show_db_results:
            self.evaluate_db_results()
        else:
            self.evaluate_model_results()



    def custom_datetime(self):
        self.set_eval_mode(True)
        self.selected_datetime = st.session_state.dtpicker
        self.evaluate_model_results()

    def custom_sun_elev(self):
        self.set_eval_mode(True)
        self.mutable_entry.sun_data.elevation = st.session_state.elevation
        self.evaluate_model_results()

    def custom_sun_azimuth(self):
        self.set_eval_mode(True)
        self.mutable_entry.sun_data.azimuth = st.session_state.azimuth
        self.evaluate_model_results()

    def custom_weather_temp(self):
        self.set_eval_mode(True)
        self.mutable_entry.weather_data.temperature = st.session_state.temperature
        self.evaluate_model_results()

    def custom_weather_cc(self):
        self.set_eval_mode(True)
        self.mutable_entry.weather_data.cloud_coverage = st.session_state.cc
        self.evaluate_model_results()

    def custom_person_info(self, person: str):
        self.set_eval_mode(True)
        self.mutable_entry.person_data.update_states(person, st.session_state[person])
        self.evaluate_model_results()

    def custom_temperature_info(self, temp_id: str):
        self.set_eval_mode(True)
        self.mutable_entry.temperature_data[temp_id].temperature = st.session_state[temp_id]
        self.evaluate_model_results()

def get_model_display() -> ModelDisplay:
    return st.session_state.display_obj

# initialize the session state values.

if "display_obj" not in st.session_state:
    st.session_state.display_obj = ModelDisplay()


st.header("Data Visualization")
st.write(f"{len(get_model_display().data_dict)} data points loaded. Model ready.")
st.divider()

control_container = st.container(
    horizontal=True,
    horizontal_alignment="center",
    vertical_alignment="top",
    width="stretch",
)

main_container = st.container(
    horizontal=True,
    horizontal_alignment="distribute",
    vertical_alignment="center",
    width="stretch",
)

with control_container:
    if not get_model_display().eval_mode:
        st.write(f"Entry #{get_model_display().selected_entry_index}")
    st.toggle(
        label="Eval Mode",
        on_change=get_model_display().toggle_eval_mode,
        key="eval_mode"
    )
    st.button(
        label="Random",
        on_click=get_model_display().get_random_entry
    )

entry: DatasetEntry = get_model_display().selected_entry


col1, col2 = st.columns(2, border=True)
with col1:
    st.subheader("Date&Time")
    st.datetime_input(label="Date&Time", key="dtpicker")
    st.button(label="Set Date", key="date_set", on_click=get_model_display().custom_datetime)
    st.subheader("Sun")
    st.slider("Elevation", -90.0, 90.0, step=0.5, key="elevation", on_change=get_model_display().custom_sun_elev)
    st.slider("Azimuth", 0.0, 359.99, step=0.5, key="azimuth", on_change=get_model_display().custom_sun_azimuth)

    st.subheader("Weather")
    st.slider("Temperature", -80.0, 80.0, step=0.5, key="temperature", on_change=get_model_display().custom_weather_temp)
    st.slider("Cloud Coverage", 0.0, 100.0, step=1.0, key="cc", on_change=get_model_display().custom_weather_cc)

    st.subheader("Person Information")
    st.checkbox("Csaba Home", key="person.csaba_varga", on_change=get_model_display().custom_person_info, args=("person.csaba_varga",))
    st.checkbox("Bence Home", key="person.bence_varga", on_change=get_model_display().custom_person_info, args=("person.bence_varga",))
    st.text(f"At Home: {entry.person_data.home_count}")

    st.subheader("Temperature Data")
    for value in entry.temperature_data.values():
        st.slider(value.name.rpartition(" ")[0], -80.0, 80.0, step=0.5, key=value.entity_id, on_change=get_model_display().custom_temperature_info, args=(value.entity_id,))

with col2:
    st.subheader("Cover Results")
    st.toggle(label="Show Database Results", key="db_results", on_change=get_model_display().toggle_db_results, disabled=get_model_display().eval_mode)
    for value in entry.shutter_data.values():
        st.text(value.name)
        st.slider("Position", 0.0, 100.0, step=1.0, key=f"{value.entity_id}_pos", disabled=True)
        st.slider("Tilt", 0.0, 100.0, step=1.0, key=f"{value.entity_id}_tilt", disabled=True)