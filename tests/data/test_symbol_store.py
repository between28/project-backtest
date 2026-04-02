from backtesting.data import symbol_store
from backtesting.domain.instruments import Instrument, build_instrument_key


def test_search_local_instruments_prefers_exact_symbol_match(tmp_path, monkeypatch):
    monkeypatch.setattr(symbol_store, "SYMBOL_STORE_PATH", tmp_path / "symbols.db")

    symbol_store.initialize_symbol_store()
    symbol_store.upsert_instruments(
        [
            Instrument(symbol="QQQ", name="Invesco QQQ Trust", exchange="NASDAQ", instrument_type="ETF"),
            Instrument(symbol="QQQM", name="Invesco NASDAQ 100 ETF", exchange="NASDAQ", instrument_type="ETF"),
            Instrument(symbol="SCHG", name="Schwab U.S. Large-Cap Growth ETF", exchange="NYSE ARCA", instrument_type="ETF"),
        ]
    )

    results = symbol_store.search_local_instruments("qqq", limit=3)

    assert results[0].symbol == "QQQ"
    assert {item.symbol for item in results} >= {"QQQ", "QQQM"}


def test_load_instruments_by_keys_falls_back_to_manual_instrument(tmp_path, monkeypatch):
    monkeypatch.setattr(symbol_store, "SYMBOL_STORE_PATH", tmp_path / "symbols.db")
    symbol_store.initialize_symbol_store()

    key = build_instrument_key("MSFT")
    instruments = symbol_store.load_instruments_by_keys([key])

    assert instruments[0].symbol == "MSFT"
    assert instruments[0].source == "manual"


def test_search_local_instruments_applies_type_and_exchange_filters(tmp_path, monkeypatch):
    monkeypatch.setattr(symbol_store, "SYMBOL_STORE_PATH", tmp_path / "symbols.db")
    symbol_store.initialize_symbol_store()
    symbol_store.upsert_instruments(
        [
            Instrument(symbol="QQQ", name="Invesco QQQ Trust", exchange="NASDAQ", instrument_type="ETF"),
            Instrument(symbol="MSFT", name="Microsoft Corporation", exchange="NASDAQ", instrument_type="Stock"),
            Instrument(symbol="SPY", name="SPDR S&P 500 ETF Trust", exchange="NYSE ARCA", instrument_type="ETF"),
        ]
    )

    results = symbol_store.search_local_instruments(
        query="",
        limit=10,
        instrument_types=["ETF"],
        exchanges=["NASDAQ"],
    )

    assert [item.symbol for item in results] == ["QQQ"]
