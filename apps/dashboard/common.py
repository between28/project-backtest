from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

for candidate in (ROOT, SRC):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

import streamlit as st

from backtesting.config import load_proxy_rules, load_settings
from backtesting.data.fetch import get_search_filter_options, resolve_history_provider_name
from backtesting.services.explorer import build_market_explorer, search_explorer_universe
from backtesting.services.compare import build_comparison, load_asset_universe


def configure_page(title: str) -> None:
    st.set_page_config(page_title=title, page_icon=":material/show_chart:", layout="wide")
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(205, 91, 69, 0.18), transparent 30%),
                linear-gradient(180deg, #f7f1e6 0%, #efe5d3 100%);
            color: #1f1a17;
        }
        h1, h2, h3 {
            font-family: Georgia, "Times New Roman", serif;
            letter-spacing: 0.02em;
        }
        [data-testid="stMetricValue"] {
            color: #7c2d12;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
        }
        .stDataFrame, .stTable {
            background: rgba(255, 252, 247, 0.75);
            border-radius: 18px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=3600, show_spinner=False)
def get_asset_metadata():
    assets = load_asset_universe()
    return [asset.to_dict() for asset in assets]


@st.cache_data(ttl=3600, show_spinner=False)
def get_proxy_rules():
    return load_proxy_rules()


@st.cache_data(ttl=3600, show_spinner=False)
def get_settings():
    return load_settings()


@st.cache_data(ttl=3600, show_spinner=True)
def get_comparison(mode: str, monthly_amount: int):
    result = build_comparison(mode=mode, monthly_amount=monthly_amount)
    return {
        "mode": result.mode,
        "monthly_amount": result.monthly_amount,
        "prices": result.comparison_prices,
        "summary": result.summary,
        "dca": result.dca_terminal,
        "metadata": result.metadata,
        "raw_prices": result.raw_prices,
        "provider_name": result.provider_name,
    }


@st.cache_data(ttl=300, show_spinner=False)
def get_market_search_results(
    query: str,
    limit: int,
    instrument_types: tuple[str, ...] = (),
    exchanges: tuple[str, ...] = (),
):
    results = search_explorer_universe(
        query=query,
        limit=limit,
        instrument_types=list(instrument_types),
        exchanges=list(exchanges),
    )
    return [instrument.to_dict() for instrument in results]


@st.cache_data(ttl=3600, show_spinner=True)
def get_market_explorer(selected_keys: tuple[str, ...], start: str | None, end: str | None, interval: str):
    result = build_market_explorer(selected_keys=list(selected_keys), start=start, end=end, interval=interval)
    return {
        "prices": result.prices,
        "summary": result.summary,
        "provider_name": result.provider_name,
        "interval": result.interval,
        "start": result.start,
        "end": result.end,
        "instruments": [instrument.to_dict() for instrument in result.instruments],
    }


def get_active_history_provider() -> str:
    settings = load_settings()
    return resolve_history_provider_name(settings.get("history_provider"))


@st.cache_data(ttl=3600, show_spinner=False)
def get_search_filter_options_cached():
    return get_search_filter_options()


def render_data_attribution(provider_name: str) -> None:
    if provider_name == "twelvedata":
        st.caption("Data provided by [Twelve Data](https://twelvedata.com)")
    elif provider_name == "yahoo":
        st.caption("Historical data fetched from Yahoo Finance via yfinance.")
