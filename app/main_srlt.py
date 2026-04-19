from pathlib import Path
from datetime import date
import pandas as pd
import streamlit as st
from data import PortfolioLoader, InstrumentFactory
from domain.instruments import FxFwd, FxNdf, FxSwap, IRS, OIS
from domain.portfolio import Portfolio

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


def _contract_to_row(c) -> dict:
    row = {
        "Product": c.product, "Name": c.name,
        "Direction": c.direction.value if hasattr(c, "direction") and c.direction else "",
        "Reg. date": c.registration_date, "Start": c.start_date,
        "End": c.end_date, "Maturity (d)": c.maturity,
        "CCY 1": None, "Amount 1": None, "CCY 2": None, "Amount 2": None,
        "Rate": None, "Swap pts": None,
    }
    if hasattr(c, "currency_1"):
        row["CCY 1"] = c.currency_1; row["Amount 1"] = c.amount_1
        row["CCY 2"] = c.currency_2; row["Amount 2"] = c.amount_2
    if hasattr(c, "rate") and hasattr(c, "currency_1"):
        row["Rate"] = c.rate; row["Swap pts"] = c.price
    elif hasattr(c, "price") and hasattr(c, "currency_1"):
        row["Rate"] = c.price
    if hasattr(c, "currency") and not hasattr(c, "currency_1"):
        row["CCY 1"] = c.currency; row["Amount 1"] = c.amount; row["Rate"] = c.price
    return row


def get_available_dates(data_path: Path) -> list[date]:
    usd  = pd.read_csv(data_path / "usd_rates.csv",      sep=";", encoding="utf-8-sig")
    disc = pd.read_csv(data_path / "discount_curves.csv",          encoding="utf-8-sig")
    fwd  = pd.read_csv(data_path / "forward_curves.csv",           encoding="utf-8-sig")
    common = (set(usd["data"].tolist()) & set(disc["Дата"].tolist()) & set(fwd["Дата"].tolist()))
    return sorted([pd.to_datetime(d, format="%d.%m.%Y").date() for d in common])


if "prtf" in st.session_state:
    prtf = st.session_state["prtf"]
    st.subheader("Portfolio contents")
    all_types      = sorted({c.product for c in prtf})
    selected_types = st.multiselect("Filter by product type", all_types, default=all_types,
                                    key="portfolio_filter")
    filtered = [c for c in prtf if c.product in selected_types] if selected_types else list(prtf)
    port_df = pd.DataFrame([_contract_to_row(c) for c in filtered])
    st.dataframe(port_df, use_container_width=True, hide_index=True)
