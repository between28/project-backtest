# ETF Backtesting Dashboard

Long-term ETF comparison workspace for building a dashboard around popular US ETFs and proxies. The current scaffold separates data access, analytics, configuration, and UI so you can expand the asset universe without rewriting the app.

## Structure

```text
apps/dashboard      Streamlit entrypoint and pages
config/             Asset universe, proxy rules, app settings
src/backtesting     Reusable package for data, analytics, services, charts
scripts/            Local helpers for running the dashboard and exporting datasets
tests/              Network-free tests for core calculations
data/               Raw, cache, and processed outputs
```

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
python scripts/run_dashboard.py
```

For a one-off export of comparison tables:

```bash
python scripts/update_data.py
```

To prefill the local SQLite symbol catalog for faster search in production:

```bash
python scripts/sync_symbol_catalog.py
```

To validate deploy readiness and warm common caches:

```bash
python scripts/predeploy_check.py
python scripts/warm_cache.py
```

For Twelve Data-backed search and history in the dashboard, set a root-level secret or environment variable:

```toml
# .streamlit/secrets.toml
TWELVE_DATA_API_KEY = "your_api_key"
```

If no Twelve Data key is configured, the app falls back to Yahoo for historical prices and keeps local curated search working.

## Deploy

For Streamlit Community Cloud:

1. Push the repository to GitHub.
2. Create a new app with entrypoint `streamlit_app.py`.
3. In "Advanced settings", choose Python `3.11` to match the local and CI environment.
4. Add `TWELVE_DATA_API_KEY` in the app secrets if you want Twelve Data search and price history.
5. Leave `requirements.txt` at the repo root so Community Cloud installs the runtime dependencies correctly.

Notes:

- Community Cloud looks for dependency files near the entrypoint and at the repo root. This repository includes `requirements.txt` for deployment compatibility.
- A root-level `streamlit_app.py` is included so deployment does not depend on a nested entrypoint path.
- The Market Explorer page stores the current basket and period in the page URL so you can share the current view directly.
- The Market Explorer basket order controls line order, legend order, and color assignment without requiring any third-party drag-and-drop component.
- If you plan to serve this publicly with Twelve Data, review their attribution and commercial usage terms before launch.

## App Modes

- Curated comparison pages use `config/assets.yaml` and `config/proxies.yaml`.
- Market Explorer lets users search symbols, add several tickers to a basket, and compare them on one chart.
- Price history is cached per symbol in `data/cache/prices`.
- Search suggestions are stored in a local SQLite catalog at `data/cache/symbols.db`.

## Notes

- `config/assets.yaml` is the main place to add or remove ETFs.
- `config/proxies.yaml` controls synthetic history such as `QQQM -> QQQ` and `VOO -> SPY`.
- `src/backtesting` contains reusable analytics, providers, search, and caching.
- Twelve Data attribution is required for publicly displayed data when using their feed.
- Metadata such as expense ratios should be reviewed periodically before using the dashboard for real investment decisions.
- The original `etf_backtest.py` remains in the repository as a single-file prototype reference.
