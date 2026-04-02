import math

import pandas as pd

from backtesting.services.compare import extend_history_with_proxy


def test_extend_history_with_proxy_scales_proxy_to_join_date():
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    proxy = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0], index=dates)
    actual = pd.Series([100.0, 110.0, 120.0], index=dates[2:])

    combined = extend_history_with_proxy(actual, proxy, "TEST")

    assert combined.name == "TEST"
    assert combined.index.min() == dates[0]
    assert combined.loc[dates[2]] == 100.0
    assert math.isclose(combined.loc[dates[1]], 11.0 * (100.0 / 12.0))

