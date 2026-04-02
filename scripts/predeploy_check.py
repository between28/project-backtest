from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

for candidate in (ROOT, SRC):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from backtesting.config import get_secret, load_assets_config, load_proxy_rules, load_settings
from backtesting.data.fetch import resolve_history_provider_name, resolve_search_provider_name


def main() -> None:
    checks: list[tuple[str, bool, str]] = []

    checks.append(("entrypoint", (ROOT / "streamlit_app.py").exists(), "streamlit_app.py"))
    checks.append(("requirements", (ROOT / "requirements.txt").exists(), "requirements.txt"))
    checks.append(("streamlit config", (ROOT / ".streamlit" / "config.toml").exists(), ".streamlit/config.toml"))
    checks.append(("assets config", bool(load_assets_config()), "config/assets.yaml"))
    checks.append(("proxy config", bool(load_proxy_rules()), "config/proxies.yaml"))

    settings = load_settings()
    checks.append(("history provider", bool(settings.get("history_provider")), f"history_provider={settings.get('history_provider')}"))
    checks.append(("search provider", bool(settings.get("search_provider")), f"search_provider={settings.get('search_provider')}"))

    api_key = get_secret("TWELVE_DATA_API_KEY")
    checks.append(("twelve data key", bool(api_key), "set for production search/history"))

    print("Predeploy check")
    print("===============")
    for label, ok, detail in checks:
        status = "OK" if ok else "WARN"
        print(f"[{status}] {label}: {detail}")

    print()
    print("Resolved providers")
    print("==================")
    try:
        print(f"history: {resolve_history_provider_name(settings.get('history_provider'))}")
    except Exception as exc:
        print(f"history: ERROR - {exc}")
    try:
        print(f"search:  {resolve_search_provider_name(settings.get('search_provider'))}")
    except Exception as exc:
        print(f"search:  ERROR - {exc}")

    print()
    print("Notes")
    print("=====")
    print("- Streamlit Community Cloud entrypoint should be streamlit_app.py")
    print("- Choose Python 3.11 in Streamlit Community Cloud Advanced settings")
    print("- Add TWELVE_DATA_API_KEY in app secrets for Twelve Data-backed search")
    print("- Run scripts/warm_cache.py after changing the default universe if you want faster first loads")


if __name__ == "__main__":
    main()
