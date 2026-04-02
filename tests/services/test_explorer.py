import pandas as pd

from backtesting.domain.instruments import Instrument, build_instrument_key
from backtesting.services import explorer


def test_build_market_explorer_returns_summary_for_selected_symbols(monkeypatch):
    selected = [
        Instrument(symbol="VOO", name="Vanguard S&P 500 ETF", instrument_type="ETF"),
        Instrument(symbol="QQQ", name="Invesco QQQ Trust", instrument_type="ETF"),
    ]
    prices = pd.DataFrame(
        {
            "VOO": [100.0, 110.0, 120.0],
            "QQQ": [100.0, 120.0, 140.0],
        },
        index=pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31"]),
    )

    monkeypatch.setattr(explorer, "load_selected_instruments", lambda keys: selected)
    monkeypatch.setattr(explorer, "fetch_instrument_history", lambda **kwargs: prices)
    monkeypatch.setattr(explorer, "resolve_history_provider_name", lambda provider: "yahoo")

    result = explorer.build_market_explorer(
        selected_keys=[build_instrument_key("VOO", instrument_type="ETF"), build_instrument_key("QQQ", instrument_type="ETF")],
        start="2024-01-01",
        end="2024-03-31",
        interval="1day",
    )

    assert result.provider_name == "yahoo"
    assert list(result.summary.index) == ["QQQ", "VOO"]
    assert result.summary.loc["QQQ", "latest_close"] == 140.0
