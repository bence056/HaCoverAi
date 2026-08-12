import datetime
import pickle
import random
from pathlib import Path

import streamlit as st
import torch

from db.load_data import DatasetEntry
from model.module import CoverModel, load_cover_model
from model.tensor import parse_output_tensor, parse_input_tensor
from util import const
from datetime import datetime

class ModelDisplay:

    selected_entry_index: int
    selected_entry: DatasetEntry
    selected_datetime: datetime
    eval_mode: bool = False

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
        self.selected_entry = list(self.data_dict.values())[0]
        self.selected_datetime = list(self.data_dict.keys())[0]


    def get_random_entry(self):
        index = random.randint(0, len(self.data_dict) - 1)
        self.pick_entry(index)

    def pick_entry(self, entry_index: int):
        self.selected_entry_index = entry_index
        self.set_eval_mode(False)
        self.selected_entry = list(self.data_dict.values())[self.selected_entry_index]
        self.selected_datetime = list(self.data_dict.keys())[self.selected_entry_index]
        #set the session state to the values we picked.
        st.session_state.date_time = self.selected_datetime
        st.session_state.elevation = self.selected_entry.sun_data.elevation
        st.session_state.azimuth = self.selected_entry.sun_data.azimuth
        st.session_state.temperature = self.selected_entry.weather_data.temperature
        st.session_state.cc = self.selected_entry.weather_data.cloud_coverage
        for key,is_home in self.selected_entry.person_data.person_states.items():
            st.session_state[key] = is_home
        for val in self.selected_entry.temperature_data.values():
            st.session_state[val.entity_id] = val.temperature

    def set_eval_mode(self, enabled: bool):
        self.eval_mode = enabled
        if self.eval_mode:
            #we need to deep copy the object for modification.
            self.selected_datetime = datetime.now()
            self.selected_entry = DatasetEntry()
            #copy the data from the current selection



    def custom_datetime(self):
        self.set_eval_mode(True)
        self.selected_datetime = st.session_state.date_time

    def custom_sun_elev(self):
        self.set_eval_mode(True)
        self.selected_entry.sun_data.elevation = st.session_state.elevation

    def custom_sun_azimuth(self):
        self.set_eval_mode(True)
        self.selected_entry.sun_data.azimuth = st.session_state.azimuth

    def custom_weather_temp(self):
        self.set_eval_mode(True)
        self.selected_entry.weather_data.temperature = st.session_state.temperature

    def custom_weather_cc(self):
        self.set_eval_mode(True)
        self.selected_entry.weather_data.cloud_coverage = st.session_state.cc

    def custom_person_info(self, person: str):
        self.set_eval_mode(True)
        self.selected_entry.person_data.update_states(person, st.session_state[person])

    def custom_temperature_info(self, temp_id: str):
        self.set_eval_mode(True)
        self.selected_entry.temperature_data[temp_id].temperature = st.session_state[temp_id]

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
    st.write(f"Entry #{get_model_display().selected_entry_index}")
    st.toggle(
        label="Eval Mode", value=get_model_display().eval_mode,
        on_change=get_model_display().set_eval_mode,
        args=(not get_model_display().eval_mode,),
    )
    st.button(
        label="Random",
        on_click=get_model_display().get_random_entry
    )

entry: DatasetEntry = get_model_display().selected_entry


col1, col2 = st.columns(2, border=True)
with col1:
    st.subheader("Date&Time")
    st.datetime_input(label="Date&Time", value=get_model_display().selected_datetime, key="date_time", on_change=get_model_display().custom_datetime)
    st.subheader("Sun")
    st.slider("Elevation", -90.0, 90.0, entry.sun_data.elevation, step=0.5, key="elevation", on_change=get_model_display().custom_sun_elev)
    st.slider("Azimuth", 0.0, 359.99, entry.sun_data.azimuth, step=0.5, key="azimuth", on_change=get_model_display().custom_sun_azimuth)

    st.subheader("Weather")
    st.slider("Temperature", -50.0, 50.0, entry.weather_data.temperature, step=0.5, key="temperature", on_change=get_model_display().custom_weather_temp)
    st.slider("Cloud Coverage", 0.0, 100.0, entry.weather_data.cloud_coverage, step=1.0, key="cc", on_change=get_model_display().custom_weather_cc)

    st.subheader("Person Information")
    st.checkbox("Csaba Home", entry.person_data.person_states["person.csaba_varga"], key="person.csaba_varga", on_change=get_model_display().custom_person_info, args=("person.csaba_varga",))
    st.checkbox("Bence Home", entry.person_data.person_states["person.bence_varga"], key="person.bence_varga", on_change=get_model_display().custom_person_info, args=("person.bence_varga",))
    st.text(f"At Home: {entry.person_data.home_count}")

    st.subheader("Temperature Data")
    for value in entry.temperature_data.values():
        st.slider(value.name.rpartition(" ")[0], -50.0, 50.0, value.temperature, step=0.5, key=value.entity_id, on_change=get_model_display().custom_temperature_info, args=(value.entity_id,))

with col2:
    st.subheader("Weather")