import pandas as pd

from backtesting.analytics.alignment import common_window
from backtesting.analytics.returns import monthly_dca_terminal_values


def test_common_window_starts_at_latest_first_valid_observation():
    dates = pd.date_range("2024-01-01", periods=4, freq="D")
    prices = pd.DataFrame(
        {
            "AAA": [10.0, 11.0, 12.0, 13.0],
            "BBB": [None, 20.0, 21.0, 22.0],
        },
        index=dates,
    )

    aligned = common_window(prices)

    assert aligned.index.min() == dates[1]
    assert list(aligned.columns) == ["AAA", "BBB"]
    assert aligned.isna().sum().sum() == 0


def test_monthly_dca_terminal_values_ranks_higher_growth_asset_first():
    dates = pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31"])
    prices = pd.DataFrame(
        {
            "AAA": [10.0, 10.0, 10.0],
            "BBB": [10.0, 20.0, 40.0],
        },
        index=dates,
    )

    terminal_values = monthly_dca_terminal_values(prices, monthly_amount=100)

    assert terminal_values.index[0] == "BBB"
    assert terminal_values.loc["BBB", "rank"] == 1
    assert terminal_values.loc["BBB", "terminal_value"] > terminal_values.loc["AAA", "terminal_value"]

