# 📊 SDFI Risk Calculator

*A Streamlit app that takes a portfolio of OTC derivatives and tells you how risky it is.*

Upload a portfolio exported from the «ТКС Сапфир» trading system and the app prices
every trade against historical market data, then computes the numbers that matter —
**NPV, VaR, Expected Shortfall, Liquidation Cost** and **Liquidity-adjusted VaR** — per instrument and for the whole book.

Currently speaks five instrument types: **FX Forwards, FX NDFs, FX Swaps,
Interest Rate Swaps (IRS)** and **Overnight Index Swaps (OIS)**.

**Live demo:** https://sdfi-risk.streamlit.app

## Run locally

```
git clone https://github.com/varietytas/SDFI-risk-calculator
cd SDFI-risk-calculator
pip install -r requirements.txt
streamlit run app/main_srlt.py
```

## Testing the app

Press **📥 Download a test portfolio**. Four ready-made
books are presented. They can be found at `data/src/demo/` as well.

## Under the hood

Extendable layered design:

```
domain/     - instruments & portfolio model
pricing/    - pricers, market data, curves, liquidation cost
risk/       - risk-metrics engine
data/       - CSV loaders & instrument factory
app/        - User Interface
```

## To be done

This is a working prototype, not a finished system. \
Next up:

- more instruments — options, cross-currency & basis swaps
- live market data instead of fixed snapshots
- configurable valuation date
- proper automated test suite
