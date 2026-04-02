from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from apps.dashboard.common import configure_page, get_active_history_provider, get_asset_metadata, get_proxy_rules


configure_page("ETF Backtesting Dashboard")

assets = pd.DataFrame(get_asset_metadata())
proxies = pd.DataFrame(get_proxy_rules())

st.title("Long-Term ETF Comparison Dashboard")
st.caption("Popular US ETFs, proxy-extended histories, and simple DCA comparisons.")

metric_columns = st.columns(4)
metric_columns[0].metric("Assets", int(len(assets)))
metric_columns[1].metric("Proxy Rules", int(len(proxies)))
metric_columns[2].metric(
    "Lowest Fee",
    f"{assets['expense_ratio_pct'].dropna().min():.2f}%",
)
metric_columns[3].metric(
    "History Provider",
    get_active_history_provider(),
)

left, right = st.columns([1.2, 1.0])

with left:
    st.subheader("What This Repo Owns")
    st.markdown(
        """
        - `config/assets.yaml` defines the investable universe.
        - `config/proxies.yaml` extends newer ETFs with older proxy histories.
        - `src/backtesting` contains reusable analytics and data access.
        - `apps/dashboard` is the Streamlit UI layer.
        - `scripts/update_data.py` exports processed tables for later reuse.
        - `pages/5_market_explorer.py` adds ticker search and ad-hoc comparison.
        """
    )

    st.subheader("Default Universe")
    st.dataframe(
        assets[["ticker", "name", "category", "expense_ratio_pct", "proxy_ticker", "tags"]],
        use_container_width=True,
        hide_index=True,
    )

with right:
    st.subheader("Proxy Rules")
    st.dataframe(
        proxies[["target", "proxy", "notes"]],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Next Build-Out")
    st.markdown(
        """
        - Add more low-fee broad-market ETFs and reference benchmarks.
        - Add annualized return windows such as 3Y, 5Y, 10Y, and since inception.
        - Add inflation-adjusted views and monthly contribution scenarios.
        - Add metadata refresh for fees and inception dates.
        """
    )
