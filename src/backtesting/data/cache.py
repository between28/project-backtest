from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha1
from pathlib import Path

import pandas as pd

from backtesting.config import DATA_DIR


CACHE_DIR = DATA_DIR / "cache"
PRICE_CACHE_DIR = CACHE_DIR / "prices"


def _is_fresh(path: Path, ttl_hours: int) -> bool:
    file_time = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return datetime.now(timezone.utc) - file_time <= timedelta(hours=ttl_hours)


def _series_cache_path(
    provider: str,
    symbol: str,
    exchange: str | None,
    start: str | None,
    end: str | None,
    interval: str,
) -> Path:
    digest = sha1(
        "|".join(
            [
                provider,
                symbol.upper(),
                (exchange or "").upper(),
                str(start),
                str(end),
                interval,
            ]
        ).encode("utf-8")
    ).hexdigest()
    return PRICE_CACHE_DIR / provider / f"{digest}.parquet"


def load_cached_series(
    provider: str,
    symbol: str,
    exchange: str | None,
    start: str | None,
    end: str | None,
    interval: str,
    ttl_hours: int,
) -> pd.Series | None:
    path = _series_cache_path(provider, symbol, exchange, start, end, interval)
    if not path.exists() or not _is_fresh(path, ttl_hours):
        return None

    frame = pd.read_parquet(path)
    if frame.empty:
        return pd.Series(dtype=float, name=symbol)

    series = frame.iloc[:, 0]
    series.index = pd.to_datetime(series.index)
    series.name = frame.columns[0]
    return series.sort_index()


def save_cached_series(
    series: pd.Series,
    provider: str,
    symbol: str,
    exchange: str | None,
    start: str | None,
    end: str | None,
    interval: str,
) -> None:
    path = _series_cache_path(provider, symbol, exchange, start, end, interval)
    path.parent.mkdir(parents=True, exist_ok=True)
    series.to_frame().sort_index().to_parquet(path)
