from __future__ import annotations

from dataclasses import dataclass


INSTRUMENT_KEY_SEPARATOR = "::"


def build_instrument_key(
    symbol: str,
    exchange: str | None = None,
    instrument_type: str | None = None,
) -> str:
    return INSTRUMENT_KEY_SEPARATOR.join(
        [
            symbol.upper(),
            (exchange or "").upper(),
            instrument_type or "",
        ]
    )


def parse_instrument_key(key: str) -> tuple[str, str | None, str | None]:
    symbol, exchange, instrument_type = (key.split(INSTRUMENT_KEY_SEPARATOR, 2) + ["", ""])[:3]
    return symbol, exchange or None, instrument_type or None


@dataclass(frozen=True, slots=True)
class Instrument:
    symbol: str
    name: str | None = None
    exchange: str | None = None
    instrument_type: str | None = None
    country: str | None = None
    currency: str | None = None
    mic_code: str | None = None
    source: str = "local"
    column_name: str | None = None

    @property
    def key(self) -> str:
        return build_instrument_key(self.symbol, self.exchange, self.instrument_type)

    @property
    def display_symbol(self) -> str:
        if self.exchange:
            return f"{self.symbol}:{self.exchange}"
        return self.symbol

    @property
    def resolved_column_name(self) -> str:
        return self.column_name or self.display_symbol

    @property
    def label(self) -> str:
        name = self.name or self.symbol
        details = [part for part in [self.exchange, self.instrument_type, self.currency] if part]
        if details:
            return f"{self.display_symbol} - {name} ({', '.join(details)})"
        return f"{self.display_symbol} - {name}"

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "symbol": self.symbol,
            "name": self.name,
            "exchange": self.exchange,
            "instrument_type": self.instrument_type,
            "country": self.country,
            "currency": self.currency,
            "mic_code": self.mic_code,
            "source": self.source,
            "column_name": self.column_name,
            "label": self.label,
        }


def instrument_from_dict(payload: dict) -> Instrument:
    return Instrument(
        symbol=str(payload["symbol"]).upper(),
        name=payload.get("name"),
        exchange=(payload.get("exchange") or None),
        instrument_type=payload.get("instrument_type") or payload.get("type"),
        country=payload.get("country"),
        currency=payload.get("currency"),
        mic_code=payload.get("mic_code"),
        source=payload.get("source", "local"),
        column_name=payload.get("column_name"),
    )
