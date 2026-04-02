from __future__ import annotations

import pandas as pd
import yfinance as yf

from backtesting.data.normalize import normalize_price_frame


def download_adjusted_close(
    tickers: list[str],
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    data = yf.download(
        tickers=tickers,
        start=start,
        end=end,
        auto_adjust=False,
        progress=False,
        group_by="ticker",
        actions=False,
        threads=True,
    )

    if isinstance(data.columns, pd.MultiIndex):
        if "Adj Close" in data.columns.get_level_values(0):
            adj_close = data["Adj Close"].copy()
        else:
            pieces = {}
            for ticker in tickers:
                if (ticker, "Adj Close") in data.columns:
                    pieces[ticker] = data[(ticker, "Adj Close")]
            adj_close = pd.DataFrame(pieces)
    else:
        if "Adj Close" not in data.columns:
            raise ValueError("Adjusted close not found in downloaded dataset.")
        adj_close = data[["Adj Close"]].rename(columns={"Adj Close": tickers[0]})

    return normalize_price_frame(adj_close)

