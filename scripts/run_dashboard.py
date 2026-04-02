from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(ROOT / "streamlit_app.py")],
        check=True,
        cwd=ROOT,
    )


if __name__ == "__main__":
    main()
