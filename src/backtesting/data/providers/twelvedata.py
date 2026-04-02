from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from backtesting.config import get_secret
from backtesting.domain.instruments import Instrument


BASE_URL = "https://api.twelvedata.com"
MAX_OUTPUTSIZE = 5000


def _require_api_key() -> str:
    api_key = get_secret("TWELVE_DATA_API_KEY")
    if not api_key:
        raise ValueError("TWELVE_DATA_API_KEY is not configured.")
    return api_key


def _request_json(path: str, params: dict[str, object]) -> dict | list:
    api_key = _require_api_key()
    query = urlencode({**params, "apikey": api_key})
    request = Request(
        f"{BASE_URL}{path}?{query}",
        headers={"User-Agent": "project-backtesting/0.1"},
    )
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if isinstance(payload, dict) and payload.get("status") == "error":
        raise ValueError(payload.get("message", f"Twelve Data request failed for {path}."))

    return payload


def _coerce_records(payload: dict | list) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        records = payload.get("data")
        if isinstance(records, list):
            return records
    return []


def search_instruments(query: str, limit: int = 12) -> list[Instrument]:
    payload = _request_json(
        "/symbol_search",
        {
            "symbol": query.strip(),
            "outputsize": limit,
        },
    )
    instruments: list[Instrument] = []
    for row in _coerce_records(payload):
        symbol = row.get("symbol")
        if not symbol:
            continue
        instruments.append(
            Instrument(
                symbol=str(symbol).upper(),
                name=row.get("instrument_name") or row.get("name"),
                exchange=row.get("exchange"),
                instrument_type=row.get("instrument_type") or row.get("type"),
                country=row.get("country"),
                currency=row.get("currency"),
                mic_code=row.get("mic_code"),
                source="twelvedata",
            )
        )
    return instruments


def fetch_reference_catalog(dataset: str) -> list[Instrument]:
    if dataset not in {"stocks", "etf"}:
        raise ValueError(f"Unsupported Twelve Data dataset: {dataset}")

    params: dict[str, object] = {"format": "JSON"}
    if dataset == "stocks":
        params["country"] = "United States"

    payload = _request_json(f"/{dataset}", params)
    instruments: list[Instrument] = []
    for row in _coerce_records(payload):
        symbol = row.get("symbol")
        if not symbol:
            continue
        instruments.append(
            Instrument(
                symbol=str(symbol).upper(),
                name=row.get("name"),
                exchange=row.get("exchange"),
                instrument_type=row.get("type") or ("ETF" if dataset == "etf" else "Stock"),
                country=row.get("country"),
                currency=row.get("currency"),
                mic_code=row.get("mic_code"),
                source="twelvedata_catalog",
            )
        )
    return instruments


def download_adjusted_close(
    instruments: list[Instrument],
    start: str | None = None,
    end: str | None = None,
    interval: str = "1day",
) -> pd.DataFrame:
    if not instruments:
        return pd.DataFrame()

    series_map: dict[str, pd.Series] = {}
    max_workers = min(4, len(instruments))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_download_single_series, instrument, start, end, interval): instrument
            for instrument in instruments
        }
        for future in as_completed(futures):
            instrument = futures[future]
            series_map[instrument.resolved_column_name] = future.result()

    return pd.DataFrame(series_map).sort_index().dropna(how="all")


def _download_single_series(
    instrument: Instrument,
    start: str | None,
    end: str | None,
    interval: str,
) -> pd.Series:
    frames: list[pd.DataFrame] = []
    current_end = end
    start_timestamp = pd.to_datetime(start) if start else None

    while True:
        params: dict[str, object] = {
            "symbol": instrument.symbol,
            "interval": interval,
            "adjust": "all",
            "format": "JSON",
            "order": "desc",
            "outputsize": MAX_OUTPUTSIZE,
        }
        if instrument.exchange:
            params["exchange"] = instrument.exchange
        if start:
            params["start_date"] = start
        if current_end:
            params["end_date"] = current_end

        payload = _request_json("/time_series", params)
        values = payload.get("values", []) if isinstance(payload, dict) else []
        if not values:
            break

        frame = pd.DataFrame(values)
        if "datetime" not in frame or "close" not in frame:
            break

        frame["datetime"] = pd.to_datetime(frame["datetime"])
        frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
        frame = frame[["datetime", "close"]].dropna().drop_duplicates(subset=["datetime"])
        frame = frame.set_index("datetime").sort_index()
        frames.append(frame)

        earliest = frame.index.min()
        if earliest is pd.NaT:
            break
        if start_timestamp is not None and earliest <= start_timestamp:
            break
        if len(frame) < MAX_OUTPUTSIZE:
            break

        current_end = (earliest - pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    if not frames:
        return pd.Series(dtype=float, name=instrument.resolved_column_name)

    combined = pd.concat(frames).sort_index()
    combined = combined[~combined.index.duplicated(keep="last")]
    if start:
        combined = combined.loc[combined.index >= pd.to_datetime(start)]
    if end:
        combined = combined.loc[combined.index <= pd.to_datetime(end)]
    series = combined["close"].rename(instrument.resolved_column_name)
    return series
