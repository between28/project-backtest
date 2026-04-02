from __future__ import annotations

import pandas as pd


def common_window(prices: pd.DataFrame) -> pd.DataFrame:
    valid_starts = prices.apply(lambda series: series.dropna().index.min())
    start = valid_starts.dropna().max()
    return prices.loc[start:].dropna()

