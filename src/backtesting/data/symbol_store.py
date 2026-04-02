from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

from backtesting.config import DATA_DIR, load_assets_config
from backtesting.domain.instruments import Instrument, build_instrument_key, parse_instrument_key


SYMBOL_STORE_PATH = DATA_DIR / "cache" / "symbols.db"
PREFERRED_EXCHANGES = {"NASDAQ", "NYSE", "NYSE ARCA", "AMEX", "ARCA"}


def _connect() -> sqlite3.Connection:
    SYMBOL_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(SYMBOL_STORE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_symbol_store() -> None:
    with _connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS symbols (
                symbol TEXT NOT NULL,
                exchange TEXT,
                instrument_type TEXT,
                name TEXT,
                country TEXT,
                currency TEXT,
                mic_code TEXT,
                source TEXT NOT NULL,
                normalized_symbol TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                last_seen_utc TEXT NOT NULL,
                PRIMARY KEY (symbol, exchange, instrument_type)
            );

            CREATE INDEX IF NOT EXISTS idx_symbols_symbol ON symbols(normalized_symbol);
            CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(normalized_name);

            CREATE TABLE IF NOT EXISTS sync_state (
                provider TEXT NOT NULL,
                dataset TEXT NOT NULL,
                synced_at_utc TEXT NOT NULL,
                PRIMARY KEY (provider, dataset)
            );
            """
        )


def seed_curated_assets() -> None:
    rows = []
    for asset in load_assets_config():
        if not asset.get("enabled", True):
            continue
        name = asset["name"]
        inferred_type = "ETF" if "ETF" in name.upper() or "TRUST" in name.upper() else "Stock"
        rows.append(
            Instrument(
                symbol=str(asset["ticker"]).upper(),
                name=name,
                instrument_type=inferred_type,
                country="United States",
                currency="USD",
                source="curated",
            )
        )
    upsert_instruments(rows)


def upsert_instruments(instruments: list[Instrument]) -> None:
    if not instruments:
        return

    initialize_symbol_store()
    now = datetime.now(timezone.utc).isoformat()
    payload = [
        (
            instrument.symbol.upper(),
            (instrument.exchange or None),
            instrument.instrument_type or None,
            instrument.name or instrument.symbol.upper(),
            instrument.country or None,
            instrument.currency or None,
            instrument.mic_code or None,
            instrument.source,
            instrument.symbol.upper(),
            (instrument.name or instrument.symbol).casefold(),
            now,
        )
        for instrument in instruments
    ]
    with _connect() as connection:
        connection.executemany(
            """
            INSERT INTO symbols (
                symbol, exchange, instrument_type, name, country, currency, mic_code,
                source, normalized_symbol, normalized_name, last_seen_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, exchange, instrument_type) DO UPDATE SET
                name=excluded.name,
                country=excluded.country,
                currency=excluded.currency,
                mic_code=excluded.mic_code,
                source=excluded.source,
                normalized_symbol=excluded.normalized_symbol,
                normalized_name=excluded.normalized_name,
                last_seen_utc=excluded.last_seen_utc
            """,
            payload,
        )


def search_local_instruments(
    query: str,
    limit: int = 12,
    instrument_types: list[str] | None = None,
    exchanges: list[str] | None = None,
) -> list[Instrument]:
    initialize_symbol_store()
    seed_curated_assets()

    normalized_query = query.strip().casefold()
    if not normalized_query:
        return list_recent_instruments(limit=limit, instrument_types=instrument_types, exchanges=exchanges)

    type_clause = ""
    exchange_clause = ""
    parameters: list[object] = [
        normalized_query.upper(),
        f"{normalized_query.upper()}%",
        f"{normalized_query}%",
        f"%{normalized_query}%",
        f"{normalized_query.upper()}%",
        f"%{normalized_query}%",
    ]

    if instrument_types:
        placeholders = ", ".join(["?"] * len(instrument_types))
        type_clause = f" AND instrument_type IN ({placeholders})"
        parameters.extend(instrument_types)

    if exchanges:
        placeholders = ", ".join(["?"] * len(exchanges))
        exchange_clause = f" AND COALESCE(exchange, '') IN ({placeholders})"
        parameters.extend(exchanges)

    parameters.append(limit)

    with _connect() as connection:
        rows = connection.execute(
            f"""
            SELECT
                symbol, exchange, instrument_type, name, country, currency, mic_code, source,
                CASE
                    WHEN normalized_symbol = ? THEN 0
                    WHEN normalized_symbol LIKE ? THEN 1
                    WHEN normalized_name LIKE ? THEN 2
                    WHEN normalized_name LIKE ? THEN 3
                    ELSE 4
                END AS score
            FROM symbols
            WHERE (
                normalized_symbol LIKE ? OR normalized_name LIKE ?
            )
            {type_clause}
            {exchange_clause}
            ORDER BY
                score ASC,
                CASE WHEN COALESCE(exchange, '') IN ('NASDAQ', 'NYSE', 'NYSE ARCA', 'AMEX', 'ARCA') THEN 0 ELSE 1 END ASC,
                symbol ASC
            LIMIT ?
            """,
            parameters,
        ).fetchall()

    return [_row_to_instrument(row) for row in rows]


def list_recent_instruments(
    limit: int = 12,
    instrument_types: list[str] | None = None,
    exchanges: list[str] | None = None,
) -> list[Instrument]:
    initialize_symbol_store()
    seed_curated_assets()
    type_clause = ""
    exchange_clause = ""
    parameters: list[object] = []

    if instrument_types:
        placeholders = ", ".join(["?"] * len(instrument_types))
        type_clause = f"WHERE instrument_type IN ({placeholders})"
        parameters.extend(instrument_types)

    if exchanges:
        placeholders = ", ".join(["?"] * len(exchanges))
        joiner = "AND" if type_clause else "WHERE"
        exchange_clause = f" {joiner} COALESCE(exchange, '') IN ({placeholders})"
        parameters.extend(exchanges)

    parameters.append(limit)

    with _connect() as connection:
        rows = connection.execute(
            f"""
            SELECT symbol, exchange, instrument_type, name, country, currency, mic_code, source
            FROM symbols
            {type_clause}
            {exchange_clause}
            ORDER BY
                CASE WHEN source = 'curated' THEN 0 ELSE 1 END ASC,
                CASE WHEN COALESCE(exchange, '') IN ('NASDAQ', 'NYSE', 'NYSE ARCA', 'AMEX', 'ARCA') THEN 0 ELSE 1 END ASC,
                symbol ASC
            LIMIT ?
            """,
            parameters,
        ).fetchall()
    return [_row_to_instrument(row) for row in rows]


def list_known_instrument_types(limit: int = 20) -> list[str]:
    initialize_symbol_store()
    seed_curated_assets()
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT DISTINCT instrument_type
            FROM symbols
            WHERE instrument_type IS NOT NULL AND instrument_type <> ''
            ORDER BY instrument_type ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [str(row["instrument_type"]) for row in rows]


def list_known_exchanges(limit: int = 30) -> list[str]:
    initialize_symbol_store()
    seed_curated_assets()
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT DISTINCT COALESCE(exchange, '') AS exchange
            FROM symbols
            WHERE COALESCE(exchange, '') <> ''
            ORDER BY
                CASE WHEN exchange IN ('NASDAQ', 'NYSE', 'NYSE ARCA', 'AMEX', 'ARCA') THEN 0 ELSE 1 END ASC,
                exchange ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [str(row["exchange"]) for row in rows]


def load_instruments_by_keys(keys: list[str]) -> list[Instrument]:
    initialize_symbol_store()
    if not keys:
        return []

    resolved: list[Instrument] = []
    with _connect() as connection:
        for key in keys:
            symbol, exchange, instrument_type = parse_instrument_key(key)
            row = connection.execute(
                """
                SELECT symbol, exchange, instrument_type, name, country, currency, mic_code, source
                FROM symbols
                WHERE symbol = ? AND COALESCE(exchange, '') = COALESCE(?, '') AND COALESCE(instrument_type, '') = COALESCE(?, '')
                """,
                (symbol, exchange, instrument_type),
            ).fetchone()
            if row is not None:
                resolved.append(_row_to_instrument(row))
                continue

            resolved.append(
                Instrument(
                    symbol=symbol,
                    exchange=exchange,
                    instrument_type=instrument_type,
                    source="manual",
                )
            )
    return resolved


def record_sync(provider: str, dataset: str) -> None:
    initialize_symbol_store()
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO sync_state (provider, dataset, synced_at_utc)
            VALUES (?, ?, ?)
            ON CONFLICT(provider, dataset) DO UPDATE SET
                synced_at_utc=excluded.synced_at_utc
            """,
            (provider, dataset, datetime.now(timezone.utc).isoformat()),
        )


def get_last_sync(provider: str, dataset: str) -> str | None:
    initialize_symbol_store()
    with _connect() as connection:
        row = connection.execute(
            "SELECT synced_at_utc FROM sync_state WHERE provider = ? AND dataset = ?",
            (provider, dataset),
        ).fetchone()
    return row["synced_at_utc"] if row else None


def _row_to_instrument(row: sqlite3.Row) -> Instrument:
    return Instrument(
        symbol=row["symbol"],
        name=row["name"],
        exchange=row["exchange"],
        instrument_type=row["instrument_type"],
        country=row["country"],
        currency=row["currency"],
        mic_code=row["mic_code"],
        source=row["source"],
    )
