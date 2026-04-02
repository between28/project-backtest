from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class Asset:
    ticker: str
    name: str
    category: str
    benchmark: str | None = None
    expense_ratio_pct: float | None = None
    tags: tuple[str, ...] = ()
    proxy_ticker: str | None = None

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "category": self.category,
            "benchmark": self.benchmark,
            "expense_ratio_pct": self.expense_ratio_pct,
            "tags": ", ".join(self.tags),
            "proxy_ticker": self.proxy_ticker,
        }


def build_assets(asset_rows: list[dict], proxy_map: dict[str, str]) -> list[Asset]:
    assets: list[Asset] = []
    for row in asset_rows:
        if not row.get("enabled", True):
            continue
        ticker = str(row["ticker"]).upper()
        assets.append(
            Asset(
                ticker=ticker,
                name=row["name"],
                category=row["category"],
                benchmark=row.get("benchmark"),
                expense_ratio_pct=row.get("expense_ratio_pct"),
                tags=tuple(row.get("tags", [])),
                proxy_ticker=proxy_map.get(ticker),
            )
        )
    return assets


def asset_metadata_frame(assets: list[Asset]) -> pd.DataFrame:
    frame = pd.DataFrame([asset.to_dict() for asset in assets])
    return frame.set_index("ticker").sort_index()

