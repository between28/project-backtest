from __future__ import annotations

import pandas as pd


def normalize_price_frame(prices: pd.DataFrame) -> pd.DataFrame:
    return prices.sort_index().dropna(how="all")

