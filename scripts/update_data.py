from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

for candidate in (ROOT, SRC):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from backtesting.services.compare import build_comparison


def export_mode(mode: str, output_dir: Path) -> None:
    result = build_comparison(mode=mode)
    mode_dir = output_dir / mode
    mode_dir.mkdir(parents=True, exist_ok=True)
    result.metadata.to_csv(mode_dir / "metadata.csv")
    result.raw_prices.to_csv(mode_dir / "raw_prices.csv")
    result.comparison_prices.to_csv(mode_dir / "comparison_prices.csv")
    result.summary.to_csv(mode_dir / "summary.csv")
    result.dca_terminal.to_csv(mode_dir / "dca_terminal.csv")


def main() -> None:
    output_dir = ROOT / "data" / "processed"
    export_mode("actual", output_dir)
    export_mode("proxy_extended", output_dir)
    print(f"Saved processed datasets to {output_dir}")


if __name__ == "__main__":
    main()

