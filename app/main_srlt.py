import sys
from pathlib import Path

# Make the project root importable
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


from datetime import date
import math
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data import PortfolioLoader, InstrumentFactory
from domain.instruments import FxFwd, FxNdf, FxSwap, IRS, OIS
from domain.portfolio import Portfolio
from pricing import MarketData, PricingEngine
from risk import VaRCalculator


st.set_page_config(page_title='SDFI Risk Calculator', layout='wide')

factory  = InstrumentFactory()
loader   = PortfolioLoader(factory)

# Logo + title
_svg = (BASE_DIR / 'app' / 'assets' / 'moex_logo.svg').read_text()
_svg = _svg.replace('width="178"', 'width="100%"').replace('height="51"', 'height="auto"')
st.markdown(
    f'<div style="width: 336px; margin-bottom: 4px;">{_svg}</div>',
    unsafe_allow_html=True,
)
st.title('SDFI Risk Calculator')

# Global style
st.markdown("""
<style>
h3 { color: #EA3426 !important; font-style: italic !important; }
.hint-wrap { position: relative; display: inline-block; }
.hint-icon {
    display: inline-flex; align-items: center; justify-content: center;
    width: 15px; height: 15px; background: #999; color: white;
    border-radius: 50%; font-size: 10px; font-weight: bold;
    margin-left: 6px; cursor: help; font-style: normal;
    vertical-align: middle;
}
.hint-tip {
    visibility: hidden; opacity: 0;
    background: #333; color: #fff; font-size: 13px; font-style: normal; font-weight: normal;
    border-radius: 4px; padding: 8px 12px; width: 300px;
    position: absolute; left: 0; bottom: 130%; z-index: 99;
    transition: opacity 0.2s; line-height: 1.5;
}
.hint-wrap:hover .hint-tip { visibility: visible; opacity: 1; }
</style>
""", unsafe_allow_html=True)


def section_header(title: str, hint: str) -> None:
    st.markdown(
        f'<h3>{title}'
        f'<span class="hint-wrap">'
        f'<span class="hint-icon">?</span>'
        f'<span class="hint-tip">{hint}</span>'
        f'</span></h3>',
        unsafe_allow_html=True,
    )


# test portfolios
DEMO_DIR = BASE_DIR / 'data' / 'src' / 'demo'
DEMO_PORTFOLIOS = [
    {
        'file': 'portfolio_test_small.csv',
        'label': 'Small — 10 contracts (~10 M ₽)',
        'desc': 'Small-business book: 5 FX forwards, 3 IRS, 1 OIS, 1 FX swap.',
    },
    {
        'file': 'portfolio_test_medium.csv',
        'label': 'Medium — 30 contracts (~800 M ₽)',
        'desc': 'Mid-size book: 6 of each type (FX Fwd, FX Ndf, FX Swap, IRS, OIS).',
    },
    {
        'file': 'portfolio_test_large.csv',
        'label': 'Large — 100 contracts (~90 B ₽)',
        'desc': 'Large, diversified book: 20 of each of the 5 product types.',
    },
    {
        'file': 'portfolio_test_forwards.csv',
        'label': 'FX Forwards & NDFs — 50 contracts',
        'desc': 'FX-only book: 25 forwards + 25 NDFs across USD/EUR/CNY.',
    },
]


@st.dialog('Download a test portfolio')
def _download_portfolios_dialog() -> None:
    st.markdown(
        'Ready-made portfolios to explore the calculator '
        'without preparing your own data. Download one below, then upload it via '
        '«Upload your portfolio».'
    )
    st.divider()

    for item in DEMO_PORTFOLIOS:
        path = DEMO_DIR / item['file']
        if not path.exists():
            continue
        st.markdown(f'**{item["label"]}**')
        st.caption(item['desc'])
        st.download_button(
            'Download CSV',
            data=path.read_bytes(),
            file_name=item['file'],
            mime='text/csv',
            use_container_width=True,
            key=f'dl_{item["file"]}',
        )
        st.markdown('<div style="margin-bottom: 10px;"></div>', unsafe_allow_html=True)


# File upload section
with st.container(border=True):

    if st.button('📥 Download a test portfolio', width=300):
        _download_portfolios_dialog()

    uploaded_file = st.file_uploader(
        'Upload your portfolio loaded from «ТКС Сапфир» as a file in CSV format',
        type='csv'
    )

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


_GAUGE_COLORS = {
    5: '#2ca02c',
    4: '#90EE90',
    3: '#FFD700',
    2: '#FFA500',
    1: '#DC143C',
}

_GAUGE_CAPTIONS = {
    5: "Risk is well-managed. The 1-day potential loss represents less than 3% of portfolio value — consistent with a properly hedged derivatives book.",
    4: "Risk is within acceptable bounds for an active derivatives portfolio. Continue routine monitoring.",
    3: "Elevated exposure. The portfolio shows meaningful sensitivity to adverse market moves. Review key concentrations and consider partial hedges.",
    2: "High risk exposure. Significant losses are possible on an adverse trading day. Risk reduction or re-hedging is advisable.",
    1: "Critical risk level. Immediate review required — the portfolio is severely exposed to market volatility and may sustain substantial losses within a single day.",
}


def _render_risk_gauge(pv: dict, total_npv):
    if total_npv is None:
        st.info("Run **Calculate NPV** to display the risk level indicator.")
        return

    pnl_mean = pv.get('pnl_mean')
    pnl_std  = pv.get('pnl_std')
    if pnl_mean is None or pnl_std is None:
        return

    raw = pnl_mean - 1.645 * pnl_std
    var_95_1d = abs(raw) if raw < 0 else 0.0

    if total_npv == 0:
        level, ratio = 1, None
    else:
        ratio = var_95_1d / abs(total_npv)
        if   ratio < 0.03: level = 5
        elif ratio < 0.07: level = 4
        elif ratio < 0.15: level = 3
        elif ratio < 0.30: level = 2
        else:              level = 1

    fig = go.Figure(go.Indicator(
        mode='gauge',
        value=level,
        title={'text': f'Risk Level {level} / 5', 'font': {'size': 17, 'color': '#888888'}},
        gauge={
            'axis': {'range': [0, 5], 'visible': False},
            'steps': [
                {'range': [0, 1], 'color': '#DC143C'},
                {'range': [1, 2], 'color': '#FFA500'},
                {'range': [2, 3], 'color': '#FFD700'},
                {'range': [3, 4], 'color': '#90EE90'},
                {'range': [4, 5], 'color': '#2ca02c'},
            ],
            'bar': {'color': "#5C5C5C", 'thickness': 0.20, 'line': {'width': 0}},
            'bgcolor': 'rgba(0,0,0,0)',
            'borderwidth': 0,
        },
    ))
    fig.update_layout(
        height=200,
        margin=dict(l=10, r=10, t=50, b=5),
        paper_bgcolor='rgba(0,0,0,0)',
    )
    st.plotly_chart(fig, use_container_width=True)

    suffix = ''
    if ratio is not None:
        suffix = (
            f' &nbsp;<span style="font-weight:normal; color:#888; font-size:15px;">'
            f'( VaR₉₅/NPV = {ratio * 100:.1f}% )</span>'
        )
    if total_npv < 0:
        suffix += (
            ' &nbsp;<span style="color:#DC143C; font-size:15px;">[portfolio NPV is negative]</span>'
        )

    st.markdown(
        f'<p style="color:{_GAUGE_COLORS[level]}; font-size:17px; margin-top:-8px; text-align:center;">'
        f'{_GAUGE_CAPTIONS[level]}</p>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<p style="text-align:center;">{suffix}</p>', unsafe_allow_html=True)


if 'prtf' in st.session_state:
    prtf = st.session_state['prtf']

    # -- Portfolio contents --
    section_header(
        'Portfolio contents',
        'This section provides basic information on contracts and filtering.',
    )

    all_types = sorted({c.product for c in prtf})
    selected_types = st.multiselect(
        'Filter by product type and sorting', all_types, default=all_types, key='portfolio_filter'
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
    section_header(
        'Net Present Value',
        'This section provides information about the Net Present Value of all assets in the '
        'portfolio, total portfolio cost, and value breakdown by product type.',
    )

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

        # Pie chart
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
    section_header(
        'Value at Risk',
        'Value at Risk (VaR) — the maximum amount of money that can be lost over a given period '
        'at the specified confidence level.\nThis section also includes Expected Shortfall (ES), '
        'Liquidation Cost (LC), and Liquidity-adjusted VaR (LVaR), calculated using both '
        'parametric and historical methods.',
    )

    st.caption('Configure VaR parameters')
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

        # Explanations
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
            _render_risk_gauge(pv, total_npv_val)

        with tbl_col:
            st.dataframe(summary_df, hide_index=True, use_container_width=True)
