from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from backtesting.analytics.risk import summarize_prices
from backtesting.config import load_settings
from backtesting.data.fetch import (
    fetch_instrument_history,
    load_selected_instruments,
    resolve_history_provider_name,
    search_market_symbols,
)
from backtesting.domain.instruments import Instrument


@dataclass(slots=True)
class ExplorerResult:
    instruments: list[Instrument]
    prices: pd.DataFrame
    summary: pd.DataFrame
    provider_name: str
    interval: str
    start: str | None
    end: str | None


def search_explorer_universe(
    query: str,
    limit: int | None = None,
    instrument_types: list[str] | None = None,
    exchanges: list[str] | None = None,
) -> list[Instrument]:
    return search_market_symbols(
        query=query,
        limit=limit,
        instrument_types=instrument_types,
        exchanges=exchanges,
    )


def build_market_explorer(
    selected_keys: list[str],
    start: str | None,
    end: str | None,
    interval: str | None = None,
) -> ExplorerResult:
    settings = load_settings()
    resolved_interval = interval or settings.get("default_interval", "1day")
    provider_name = resolve_history_provider_name(settings.get("history_provider"))
    instruments = load_selected_instruments(selected_keys)
    if not instruments:
        raise ValueError("No instruments selected.")

    prices = fetch_instrument_history(
        instruments=instruments,
        start=start,
        end=end,
        provider=provider_name,
        cache_ttl_hours=int(settings.get("cache_ttl_hours", 24)),
        interval=resolved_interval,
    )
    if prices.empty:
        raise ValueError("No price history was returned for the selected instruments.")

    summary = summarize_prices(prices)
    metadata_rows = []
    for instrument in instruments:
        metadata_rows.append(
            {
                "ticker": instrument.resolved_column_name,
                "name": instrument.name,
                "exchange": instrument.exchange,
                "instrument_type": instrument.instrument_type,
                "country": instrument.country,
                "currency": instrument.currency,
                "source": instrument.source,
            }
        )
    metadata = pd.DataFrame(metadata_rows).set_index("ticker")
    latest_close = prices.ffill().iloc[-1].rename("latest_close")
    ordered_summary = metadata.join(summary, how="right").join(latest_close, how="left")

    return ExplorerResult(
        instruments=instruments,
        prices=prices,
        summary=ordered_summary,
        provider_name=provider_name,
        interval=resolved_interval,
        start=start,
        end=end,
    )
