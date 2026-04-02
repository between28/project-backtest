from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

for candidate in (ROOT, SRC):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from backtesting.config import get_secret
from backtesting.data.fetch import sync_symbol_catalog
from backtesting.domain.instruments import build_instrument_key
from backtesting.services.compare import build_comparison
from backtesting.services.explorer import build_market_explorer


DEFAULT_EXPLORER_KEYS = [
    build_instrument_key("VOO", instrument_type="ETF"),
    build_instrument_key("QQQ", instrument_type="ETF"),
    build_instrument_key("GLD", instrument_type="ETF"),
]


def main() -> None:
    if get_secret("TWELVE_DATA_API_KEY"):
        counts = sync_symbol_catalog()
        for dataset, count in counts.items():
            print(f"synced {dataset}: {count}")
    else:
        print("TWELVE_DATA_API_KEY not set; skipping Twelve Data symbol sync.")

    actual = build_comparison(mode="actual", monthly_amount=1000)
    proxy_extended = build_comparison(mode="proxy_extended", monthly_amount=1000)
    explorer = build_market_explorer(
        selected_keys=DEFAULT_EXPLORER_KEYS,
        start="2019-01-01",
        end=None,
        interval="1day",
    )

    print(f"warmed actual comparison: {actual.comparison_prices.shape}")
    print(f"warmed proxy comparison: {proxy_extended.comparison_prices.shape}")
    print(f"warmed explorer view: {explorer.prices.shape}")


if __name__ == "__main__":
    main()
