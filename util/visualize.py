import pickle
import random
from pathlib import Path

import streamlit as st
import torch

from db.load_data import DatasetEntry
from model.module import CoverModel, load_cover_model
from model.tensor import parse_output_tensor, parse_input_tensor
from util import const

class ModelDisplay:
    def __init__(self):

        data_file = Path(const.TRAINING_SAVE_PATH)
        model_file = Path(const.MODEL_SAVE_PATH)
        if not data_file.exists():
            raise FileNotFoundError(f"Model input file {data_file} not found.")
        if not model_file.exists():
            raise FileNotFoundError(f"Model parameter file {data_file} not found.")
        # Load the data file from disk
        with open(data_file, 'rb') as f:
            self.data_dict: dict[str, DatasetEntry] = pickle.load(f)
            self.model: CoverModel = load_cover_model(str(model_file))


    def get_random_entry(self) -> int:
        index = random.randint(0, len(self.data_dict) - 1)
        return index


model_display = ModelDisplay()

st.header("Data Visualization")
st.write(f"{len(model_display.data_dict)} data points loaded. Model ready.")
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
    vertical_alignment="top",
    width="stretch",
)

selected_index = 0
selected_entry = list(model_display.data_dict.values())[selected_index]

def pick_entry(entry: int):
    global selected_index
    selected_index = entry
    global selected_entry
    selected_entry = list(model_display.data_dict.values())[selected_index]

with control_container:
    st.write(f"Entry {selected_index}:")
    st.button(
        label="Random",
        on_click=pick_entry,
        args=(model_display.get_random_entry(),),
    )

with main_container:
    st.write("Test1")
    st.write("Test2")
