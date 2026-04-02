from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

for candidate in (ROOT, SRC):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from backtesting.data.fetch import sync_symbol_catalog


def main() -> None:
    counts = sync_symbol_catalog()
    for dataset, count in counts.items():
        print(f"{dataset}: {count}")


if __name__ == "__main__":
    main()
