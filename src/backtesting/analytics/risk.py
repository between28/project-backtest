from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class Metrics:
    cagr: float
    annual_vol: float
    sharpe_rf0: float
    max_drawdown: float
    calmar: float
    total_return: float
    start: str
    end: str
    years: float


def compute_metrics(prices: pd.Series) -> Metrics:
    clean_prices = prices.dropna()
    if clean_prices.empty:
        raise ValueError("No prices available for metric computation.")

    returns = clean_prices.pct_change().dropna()
    if returns.empty:
        return Metrics(
            cagr=np.nan,
            annual_vol=np.nan,
            sharpe_rf0=np.nan,
            max_drawdown=np.nan,
            calmar=np.nan,
            total_return=0.0,
            start=str(clean_prices.index[0].date()),
            end=str(clean_prices.index[-1].date()),
            years=0.0,
        )

    years = (clean_prices.index[-1] - clean_prices.index[0]).days / 365.25
    total_return = clean_prices.iloc[-1] / clean_prices.iloc[0] - 1
    cagr = (clean_prices.iloc[-1] / clean_prices.iloc[0]) ** (1 / years) - 1 if years > 0 else np.nan
    annual_vol = returns.std() * np.sqrt(252)
    sharpe_rf0 = (returns.mean() * 252) / annual_vol if annual_vol > 0 else np.nan

    wealth = (1 + returns).cumprod()
    drawdowns = wealth.div(wealth.cummax()).sub(1.0)
    max_drawdown = drawdowns.min()
    calmar = cagr / abs(max_drawdown) if max_drawdown < 0 else np.nan

    return Metrics(
        cagr=cagr,
        annual_vol=annual_vol,
        sharpe_rf0=sharpe_rf0,
        max_drawdown=max_drawdown,
        calmar=calmar,
        total_return=total_return,
        start=str(clean_prices.index[0].date()),
        end=str(clean_prices.index[-1].date()),
        years=years,
    )


def summarize_prices(prices: pd.DataFrame) -> pd.DataFrame:
    rows = {}
    for ticker in prices.columns:
        metrics = compute_metrics(prices[ticker])
        rows[ticker] = {
            "start": metrics.start,
            "end": metrics.end,
            "years": round(metrics.years, 2),
            "total_return_pct": round(metrics.total_return * 100, 2),
            "cagr_pct": round(metrics.cagr * 100, 2),
            "annual_vol_pct": round(metrics.annual_vol * 100, 2),
            "sharpe_rf0": round(metrics.sharpe_rf0, 3),
            "max_drawdown_pct": round(metrics.max_drawdown * 100, 2),
            "calmar": round(metrics.calmar, 3),
        }
    return pd.DataFrame(rows).T.sort_values(["cagr_pct", "sharpe_rf0"], ascending=False)
