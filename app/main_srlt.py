from pathlib import Path
from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st

from data import PortfolioLoader, InstrumentFactory
from domain.instruments import FxFwd, FxNdf, FxSwap, IRS, OIS
from domain.portfolio import Portfolio
from pricing import MarketData, PricingEngine
from risk import VaRCalculator


st.set_page_config(page_title='SDFI Risk Calculator', layout='wide')

factory  = InstrumentFactory()
loader   = PortfolioLoader(factory)
BASE_DIR = Path(__file__).resolve().parents[1]  # Project root

# Logo + title
_svg = (BASE_DIR / 'app' / 'assets' / 'moex_logo.svg').read_text()
_svg = _svg.replace('width="178"', 'width="100%"').replace('height="51"', 'height="auto"')
st.markdown(
    f'<div style="width: 336px; margin-bottom: 4px;">{_svg}</div>',
    unsafe_allow_html=True,
)
st.title('SDFI Risk Calculator')

# Global style: all st.subheader elements red italic
st.markdown("""
<style>
h3 { color: #EA3426 !important; font-style: italic !important; }
</style>
""", unsafe_allow_html=True)

# File upload section
with st.container(border=True):
    uploaded_file = st.file_uploader('Upload a CSV file', type='csv')
    if st.button('Read'):
        if uploaded_file is not None:
            try:
                prtf = loader.from_csv(uploaded_file, 'Test')
                st.session_state['prtf'] = prtf
                st.success('File loaded')
            except Exception as e:
                st.error(f'Error reading file: {e}')
        else:
            st.warning('Please, upload a file first')


def _contract_to_row(c) -> dict:
    row = {
        'Product':      c.product,
        'Name':         c.name,
        'Direction':    c.direction.value if hasattr(c, 'direction') and c.direction else '',
        'Reg. date':    c.registration_date,
        'Start':        c.start_date,
        'End':          c.end_date,
        'Maturity (d)': c.maturity,
        'CCY 1':        None,
        'Amount 1':     None,
        'CCY 2':        None,
        'Amount 2':     None,
        'Rate':         None,
        'Swap pts':     None,
    }

    if hasattr(c, 'currency_1'):
        row['CCY 1']    = c.currency_1
        row['Amount 1'] = c.amount_1
        row['CCY 2']    = c.currency_2
        row['Amount 2'] = c.amount_2

    if hasattr(c, 'rate') and hasattr(c, 'currency_1'):
        row['Rate']     = c.rate
        row['Swap pts'] = c.price
    elif hasattr(c, 'price') and hasattr(c, 'currency_1'):
        row['Rate']     = c.price

    if hasattr(c, 'currency') and not hasattr(c, 'currency_1'):
        row['CCY 1']    = c.currency
        row['Amount 1'] = c.amount
        row['Rate']     = c.price

    if hasattr(c, 'currency') and not hasattr(c, 'registration_date'):
        row['CCY 1'] = c.currency
        row['Rate']  = c.rate

    return row


def get_available_dates(data_path: Path) -> list[date]:
    usd  = pd.read_csv(data_path / 'usd_rates.csv', sep=';', encoding='utf-8-sig')
    disc = pd.read_csv(data_path / 'discount_curves.csv', encoding='utf-8-sig')
    fwd  = pd.read_csv(data_path / 'forward_curves.csv', encoding='utf-8-sig')

    common = (
        set(usd['data'].tolist())
        & set(disc['Дата'].tolist())
        & set(fwd['Дата'].tolist())
    )
    return sorted([pd.to_datetime(d, format='%d.%m.%Y').date() for d in common])


def fmt(x):
    return f'{x:,.2f} RUB' if x is not None else 'N/A'


if 'prtf' in st.session_state:
    prtf = st.session_state['prtf']

    # -- Portfolio contents --
    st.subheader('Portfolio contents')

    all_types = sorted({c.product for c in prtf})
    selected_types = st.multiselect(
        'Filter by product type', all_types, default=all_types, key='portfolio_filter'
    )

    filtered = (
        list(prtf) if not selected_types
        else [c for c in prtf if c.product in selected_types]
    )
    port_df = pd.DataFrame([_contract_to_row(c) for c in filtered])
    st.dataframe(port_df, use_container_width=True, hide_index=True)

    portfolio = Portfolio(prtf.get_by_type((FxFwd, FxNdf, FxSwap, IRS, OIS)), name='Instruments')

    # -- Net Present Value --
    st.divider()
    st.subheader('Net Present Value')

    if st.button('Calculate NPV'):
        val_date = get_available_dates(BASE_DIR / 'data' / 'market')[-1]
        market_data = MarketData.load_from_csv(val_date, str(BASE_DIR / 'data' / 'market'))
        engine = PricingEngine(market_data, base_currency='RUB')

        npv_rows  = []
        total_npv = 0.0
        for contract in portfolio:
            try:
                npv = engine.price(contract, target_currency='RUB')
            except Exception:
                npv = None
            npv_rows.append({'Instrument': repr(contract), 'Product': contract.product, 'NPV': npv})
            if npv is not None:
                total_npv += npv

        st.session_state['npv_results'] = npv_rows
        st.session_state['npv_total']   = total_npv
        st.session_state['npv_date']    = val_date

    if 'npv_results' in st.session_state:
        st.info(f'Valuation date: {st.session_state["npv_date"]}')

        npv_df = pd.DataFrame(st.session_state['npv_results'])

        # Formatted table
        display_df = npv_df[['Instrument', 'NPV']].copy()
        display_df['NPV'] = display_df['NPV'].apply(
            lambda x: f'{x:,.2f} RUB' if x is not None else 'N/A'
        )
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        st.markdown('<div style="margin-top: 18px;"></div>', unsafe_allow_html=True)
        st.metric('Total Portfolio NPV', f'{st.session_state["npv_total"]:,.2f} RUB')
        st.markdown('<div style="margin-bottom: 18px;"></div>', unsafe_allow_html=True)

        # Pie chart - NPV breakdown by product type
        chart_df = npv_df.dropna(subset=['NPV'])
        if not chart_df.empty:
            product_npv = (
                chart_df.groupby('Product', as_index=False)['NPV']
                .sum()
                .rename(columns={'NPV': 'Total NPV'})
            )
            product_npv['Abs NPV'] = product_npv['Total NPV'].abs()
            has_negative = (product_npv['Total NPV'] < 0).any()

            fig = px.pie(
                product_npv,
                values='Abs NPV',
                names='Product',
                hole=0.4,
                custom_data=['Total NPV'],
            )
            fig.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>NPV: %{customdata[0]:,.0f} RUB<extra></extra>',
            )
            fig.update_layout(
                title=dict(
                    text='NPV Breakdown by Product Type',
                    font=dict(size=22),
                ),
                legend=dict(orientation='v', yanchor='middle', y=0.5),
                margin=dict(t=70, b=20),
            )

            pie_col, _ = st.columns([0.7, 0.3])
            with pie_col:
                st.plotly_chart(fig, use_container_width=True)

            if has_negative:
                st.caption(
                    'Note: pie slice sizes use absolute NPV values. '
                    'Products with negative total NPV are still shown; '
                    'hover to see the signed value.'
                )

    # -- Value at Risk --
    st.divider()
    st.subheader('Value at Risk')

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown('#### Confidence Level')
            confidence_map = {'90%': 0.90, '95%': 0.95, '99%': 0.99}
            confidence_label = st.radio(
                'Confidence level', list(confidence_map.keys()),
                index=1, horizontal=True, label_visibility='collapsed',
            )
            confidence = confidence_map[confidence_label]
    with col2:
        with st.container(border=True):
            st.markdown('#### Holding Period')
            holding_map = {'1 day': 1, '5 days (1W)': 5, '10 days': 10, '21 days (1M)': 21}
            holding_label = st.radio(
                'Holding period', list(holding_map.keys()),
                index=0, horizontal=True, label_visibility='collapsed',
            )
            holding_period = holding_map[holding_label]

    if st.button('Calculate VaR'):
        dates = get_available_dates(BASE_DIR / 'data' / 'market')
        calc  = VaRCalculator(portfolio, base_currency='RUB',
                              data_path=str(BASE_DIR / 'data' / 'market'))
        with st.spinner('Calculating...'):
            per_instrument, portfolio_var = calc.calculate_all_var(dates, confidence)

        if holding_period > 1:
            per_instrument, portfolio_var = VaRCalculator.scale_var(
                per_instrument, portfolio_var, holding_period
            )

        rows = [
            {
                'Instrument':      repr(r['contract']),
                'Historical VaR':  r['historical_var'],
                'Parametric VaR':  r['parametric_var'],
                'Historical ES':   r['historical_es'],
                'Parametric ES':   r['parametric_es'],
                'LC':              r['lc'],
                'Historical LVaR': r['historical_lvar'],
                'Parametric LVaR': r['parametric_lvar'],
            }
            for r in per_instrument
        ]
        st.session_state['var_results']    = rows
        st.session_state['var_portfolio']  = portfolio_var
        st.session_state['var_dates_info'] = (dates[0], dates[-1], len(dates), holding_period)
        st.session_state['var_confidence'] = confidence
        st.session_state['var_conf_label'] = confidence_label

    if 'var_results' in st.session_state:
        d0, d1, n, hp = st.session_state['var_dates_info']
        st.info(f'Based on {n} historical observations ({d0} to {d1}) · {hp}-day holding period')

        results_df = pd.DataFrame(st.session_state['var_results'])
        for col in ['Historical VaR', 'Parametric VaR', 'Historical ES', 'Parametric ES',
                    'LC', 'Historical LVaR', 'Parametric LVaR']:
            results_df[col] = results_df[col].apply(fmt)
        st.dataframe(results_df, use_container_width=True, hide_index=True)

    # -- Portfolio Summary --
    if 'var_portfolio' in st.session_state:
        st.divider()
        st.subheader('Portfolio Summary')

        pv         = st.session_state['var_portfolio']
        conf       = st.session_state.get('var_confidence', confidence)
        conf_pct   = int(conf * 100)
        tail_pct   = 100 - conf_pct
        hp         = st.session_state['var_dates_info'][3]

        total_npv_val = st.session_state.get('npv_total')
        npv_str       = fmt(total_npv_val) if total_npv_val is not None else 'N/A'

        # Summary table
        summary_df = pd.DataFrame({
            'Metric': [
                'NPV',
                'Historical VaR', 'Parametric VaR',
                'Historical ES',  'Parametric ES',
                'LC',
                'Historical LVaR', 'Parametric LVaR',
            ],
            'Value': [
                npv_str,
                fmt(pv['historical_var']), fmt(pv['parametric_var']),
                fmt(pv['historical_es']),  fmt(pv['parametric_es']),
                fmt(pv['lc']),
                fmt(pv['historical_lvar']), fmt(pv['parametric_lvar']),
            ],
        })

        # Bullet-point explanations
        bull_col, tbl_col = st.columns([0.55, 0.45])

        with bull_col:
            npv_bullet = (
                f'The current mark-to-market value of the portfolio is **{npv_str}**.'
                if total_npv_val is not None
                else 'Portfolio NPV has not been calculated yet — run **Calculate NPV** first.'
            )
            st.markdown(
                f'- **NPV:** {npv_bullet}\n'
                f'- **VaR:** With {conf_pct}% probability, the portfolio loss will not exceed '
                f'**{fmt(pv["parametric_var"])}** over the next {hp} day(s).\n'
                f'- **ES:** In the worst {tail_pct}% of scenarios, the average expected portfolio '
                f'loss is **{fmt(pv["parametric_es"])}**.\n'
                f'- **Liquidation Cost (LC):** The estimated one-time cost to fully close and exit '
                f'the portfolio is **{fmt(pv["lc"])}**.\n'
                f'- **LVaR:** Including liquidation costs, the total worst-case loss at {conf_pct}% '
                f'confidence is **{fmt(pv["parametric_lvar"])}** over the next {hp} day(s).'
            )

        with tbl_col:
            st.dataframe(summary_df, hide_index=True, use_container_width=True)
