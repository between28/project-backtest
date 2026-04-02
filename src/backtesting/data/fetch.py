from __future__ import annotations

import pandas as pd

from backtesting.config import get_secret, load_settings
from backtesting.data.cache import load_cached_series, save_cached_series
from backtesting.data.providers.twelvedata import (
    download_adjusted_close as download_adjusted_close_twelvedata,
    fetch_reference_catalog,
    search_instruments as search_instruments_twelvedata,
)
from backtesting.data.providers.yahoo import download_adjusted_close as download_adjusted_close_yahoo
from backtesting.data.symbol_store import (
    list_known_exchanges,
    list_known_instrument_types,
    load_instruments_by_keys,
    record_sync,
    search_local_instruments,
    upsert_instruments,
)
from backtesting.domain.instruments import Instrument


def resolve_history_provider_name(requested_provider: str | None = None) -> str:
    settings = load_settings()
    preferred = requested_provider or settings.get("history_provider", "auto")
    if preferred == "auto":
        return settings.get("preferred_provider", "twelvedata") if get_secret("TWELVE_DATA_API_KEY") else settings.get(
            "fallback_history_provider",
            "yahoo",
        )
    if preferred == "twelvedata" and not get_secret("TWELVE_DATA_API_KEY"):
        raise ValueError("history_provider is set to twelvedata but TWELVE_DATA_API_KEY is missing.")
    return preferred


def resolve_search_provider_name(requested_provider: str | None = None) -> str:
    settings = load_settings()
    preferred = requested_provider or settings.get("search_provider", "auto")
    if preferred == "auto":
        return "twelvedata" if get_secret("TWELVE_DATA_API_KEY") else "local"
    if preferred == "twelvedata" and not get_secret("TWELVE_DATA_API_KEY"):
        raise ValueError("search_provider is set to twelvedata but TWELVE_DATA_API_KEY is missing.")
    return preferred


def fetch_price_history(
    tickers: list[str],
    start: str | None,
    end: str | None,
    provider: str | None,
    cache_ttl_hours: int = 24,
    interval: str = "1day",
) -> pd.DataFrame:
    instruments = [
        Instrument(symbol=ticker.upper(), name=ticker.upper(), column_name=ticker.upper(), source="ticker")
        for ticker in tickers
    ]
    return fetch_instrument_history(
        instruments=instruments,
        start=start,
        end=end,
        provider=provider,
        cache_ttl_hours=cache_ttl_hours,
        interval=interval,
    )


def fetch_instrument_history(
    instruments: list[Instrument],
    start: str | None,
    end: str | None,
    provider: str | None,
    cache_ttl_hours: int = 24,
    interval: str = "1day",
) -> pd.DataFrame:
    resolved_provider = resolve_history_provider_name(provider)
    series_map: dict[str, pd.Series] = {}
    missing: list[Instrument] = []

    for instrument in instruments:
        cached = load_cached_series(
            provider=resolved_provider,
            symbol=instrument.symbol,
            exchange=instrument.exchange,
            start=start,
            end=end,
            interval=interval,
            ttl_hours=cache_ttl_hours,
        )
        if cached is None:
            missing.append(instrument)
            continue
        series_map[instrument.resolved_column_name] = cached.rename(instrument.resolved_column_name)

    if missing:
        fetched_map = _download_missing_instruments(
            instruments=missing,
            start=start,
            end=end,
            provider=resolved_provider,
            interval=interval,
        )
        for instrument in missing:
            series = fetched_map.get(instrument.resolved_column_name, pd.Series(dtype=float, name=instrument.resolved_column_name))
            save_cached_series(
                series=series,
                provider=resolved_provider,
                symbol=instrument.symbol,
                exchange=instrument.exchange,
                start=start,
                end=end,
                interval=interval,
            )
            series_map[instrument.resolved_column_name] = series

    if not series_map:
        return pd.DataFrame()
    return pd.DataFrame(series_map).sort_index().dropna(how="all")


def search_market_symbols(
    query: str,
    limit: int | None = None,
    provider: str | None = None,
    instrument_types: list[str] | None = None,
    exchanges: list[str] | None = None,
) -> list[Instrument]:
    settings = load_settings()
    search_limit = int(limit or settings.get("search_result_limit", 12))
    resolved_provider = resolve_search_provider_name(provider)

    local_results = search_local_instruments(
        query=query,
        limit=search_limit,
        instrument_types=instrument_types,
        exchanges=exchanges,
    )
    if resolved_provider != "twelvedata" or len(query.strip()) < 2:
        return local_results[:search_limit]

    try:
        remote_results = search_instruments_twelvedata(query=query, limit=search_limit)
    except Exception:
        return local_results[:search_limit]

    upsert_instruments(remote_results)
    return search_local_instruments(
        query=query,
        limit=search_limit,
        instrument_types=instrument_types,
        exchanges=exchanges,
    )[:search_limit]


def sync_symbol_catalog(
    provider: str | None = None,
    datasets: tuple[str, ...] = ("stocks", "etf"),
) -> dict[str, int]:
    resolved_provider = resolve_search_provider_name(provider)
    if resolved_provider != "twelvedata":
        raise ValueError("Catalog sync is only supported for the twelvedata search provider.")

    counts: dict[str, int] = {}
    for dataset in datasets:
        instruments = fetch_reference_catalog(dataset)
        upsert_instruments(instruments)
        record_sync("twelvedata", dataset)
        counts[dataset] = len(instruments)
    return counts


def load_selected_instruments(keys: list[str]) -> list[Instrument]:
    return load_instruments_by_keys(keys)


def get_search_filter_options() -> dict[str, list[str]]:
    return {
        "instrument_types": list_known_instrument_types(),
        "exchanges": list_known_exchanges(),
    }


def _download_missing_instruments(
    instruments: list[Instrument],
    start: str | None,
    end: str | None,
    provider: str,
    interval: str,
) -> dict[str, pd.Series]:
    if provider == "twelvedata":
        frame = download_adjusted_close_twelvedata(instruments, start=start, end=end, interval=interval)
        return {column: frame[column].dropna().rename(column) for column in frame.columns}

    if provider == "yahoo":
        frame = download_adjusted_close_yahoo(sorted({instrument.symbol for instrument in instruments}), start=start, end=end)
        results: dict[str, pd.Series] = {}
        for instrument in instruments:
            if instrument.symbol not in frame.columns:
                results[instrument.resolved_column_name] = pd.Series(dtype=float, name=instrument.resolved_column_name)
                continue
            results[instrument.resolved_column_name] = frame[instrument.symbol].dropna().rename(instrument.resolved_column_name)
        return results

    raise ValueError(f"Unsupported provider: {provider}")
