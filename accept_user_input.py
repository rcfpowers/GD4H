import streamlit as st
import pandas as pd
import csv

import upload_data

def process_data(df, weight_1, weight_2):
    upload_data.calculate_carreaus(df, weight_1, weight_2)
    
def detect_delimiter(file):
    sample = file.read(1024).decode("utf-8")
    file.seek(0)
    sniffer = csv.Sniffer()
    return sniffer.sniff(sample).delimiter

text = st.text_input("Enter text")
number = st.number_input("Enter a number")
file = st.file_uploader("Upload a file", type=["txt", "csv", "xls", "xlsx"])
checked = st.checkbox("Add new location data to the base amenity dataset?")
weight_1 = st.slider("Select a weight", 0, 100, key="weight_slider_1")
weight_2 = st.slider("Select a weight", 0, 100, key="weight_slider_2")

if st.button("Submit"):
    if file:
        file_name = file.name.lower()
        
        if file_name.endswith((".xls", ".xlsx")):
            df = pd.read_excel(file, engine="openpyxl")
        elif file_name.endswith(".csv"):
            df = pd.read_csv(file)
        elif file_name.endswith(".txt"):
            delimiter = detect_delimiter(file)
            df = pd.read_csv(file, delimiter=delimiter)
        st.write("File uploaded successfully!")        
        process_data(df, weight_1, weight_2)

    else:
        st.write("Please upload a file.")