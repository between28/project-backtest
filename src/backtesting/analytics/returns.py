from __future__ import annotations

import pandas as pd


def wealth_index(prices: pd.DataFrame, initial_value: float = 10_000) -> pd.DataFrame:
    return prices.div(prices.iloc[0]).mul(initial_value)


def drawdown(prices: pd.DataFrame) -> pd.DataFrame:
    wealth = prices.div(prices.iloc[0])
    return wealth.div(wealth.cummax()).sub(1.0)


def monthly_dca_terminal_values(prices: pd.DataFrame, monthly_amount: float = 1_000) -> pd.DataFrame:
    month_ends = prices.resample("ME").last().dropna(how="all")
    share_purchases = month_ends.rdiv(monthly_amount)
    cumulative_shares = share_purchases.cumsum()
    terminal_values = cumulative_shares.mul(month_ends).iloc[-1].sort_values(ascending=False)
    output = terminal_values.rename("terminal_value").to_frame()
    output["rank"] = output["terminal_value"].rank(method="min", ascending=False).astype(int)
    return output

