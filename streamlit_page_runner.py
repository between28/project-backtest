from __future__ import annotations

from pathlib import Path
import runpy
import sys


ROOT = Path(__file__).resolve().parent


def run_dashboard_page(filename: str) -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    target = ROOT / "apps" / "dashboard" / "pages" / filename
    runpy.run_path(str(target), run_name="__main__")
