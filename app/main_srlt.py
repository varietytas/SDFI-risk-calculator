from pathlib import Path
import streamlit as st
from data import PortfolioLoader, InstrumentFactory

st.set_page_config(page_title="SDFI Risk Calculator", layout="wide")
factory  = InstrumentFactory()
loader   = PortfolioLoader(factory)
BASE_DIR = Path(__file__).resolve().parents[1]

st.title("SDFI Risk Calculator")

with st.container(border=True):
    uploaded_file = st.file_uploader("Upload a CSV file", type="csv")
    if st.button("Read"):
        if uploaded_file is not None:
            try:
                prtf = loader.from_csv(uploaded_file, "Test")
                st.session_state["prtf"] = prtf
                st.success("File loaded")
            except Exception as e:
                st.error(f"Error reading file: {e}")
        else:
            st.warning("Please, upload a file first")

if "prtf" in st.session_state:
    prtf = st.session_state["prtf"]
    st.write(f"Portfolio loaded: {len(prtf)} contracts")
