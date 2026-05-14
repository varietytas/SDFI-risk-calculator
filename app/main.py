from os import path
from pathlib import Path

import pandas as pd

from data import PortfolioLoader, InstrumentFactory
from domain.instruments import FxFwd, FxNdf, FxSwap
from domain.portfolio import Portfolio
from pricing import MarketData, PricingEngine


def get_latest_common_date(data_path: str):  # newest date with full market data
    usd = pd.read_csv(path.join(data_path, 'usd_rates.csv'), sep=';', encoding='utf-8-sig')
    eur = pd.read_csv(path.join(data_path, 'eur_rates.csv'), sep=';', encoding='utf-8-sig')
    cny = pd.read_csv(path.join(data_path, 'cny_rates.csv'), sep=';', encoding='utf-8-sig')
    disc = pd.read_csv(path.join(data_path, 'discount_curves.csv'), encoding='utf-8-sig')

    common = set(usd['data']) & set(eur['data']) & set(cny['data']) & set(disc['Дата'])
    return max(pd.to_datetime(d, format='%d.%m.%Y').date() for d in common)


def main():
    factory = InstrumentFactory()
    loader = PortfolioLoader(factory)

    BASE_DIR = Path(__file__).resolve().parents[1]  # Project root
    market_path = path.join(BASE_DIR, 'data', 'market')

    prtf = loader.from_csv(path.join(BASE_DIR, 'data', 'src', 'trade_test.csv'), 'Test')
    print(prtf.output())

    print('\n\n')

    fx_instruments = Portfolio(prtf.get_by_type((FxFwd, FxNdf, FxSwap)), name='FX Instruments')
    print(fx_instruments.output())

    print('\n\n--- NPV ---')
    val_date = get_latest_common_date(market_path)
    market_data = MarketData.load_from_csv(val_date, market_path)
    engine = PricingEngine(market_data, base_currency='RUB')

    total = 0.0
    for contract in fx_instruments:
        try:
            npv = engine.price(contract, target_currency='RUB')
            print(f'  {repr(contract)}\n    NPV = {npv:,.2f} RUB')
            total += npv
        except Exception as e:
            print(f'  {repr(contract)}\n    ERROR: {e}')

    print(f'\nTotal portfolio NPV: {total:,.2f} RUB')

if __name__ == "__main__":
    main()
