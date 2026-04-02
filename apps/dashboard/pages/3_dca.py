from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from apps.dashboard.common import configure_page, get_comparison, render_data_attribution
from backtesting.charts.plotly import build_dca_figure


configure_page("ETF DCA")

st.title("Monthly DCA Outcome")

mode = st.selectbox(
    "History mode",
    options=["proxy_extended", "actual"],
    format_func=lambda value: "Proxy-Extended" if value == "proxy_extended" else "Actual Only",
)
monthly_amount = int(
    st.number_input("Monthly contribution", min_value=100, max_value=100000, value=1000, step=100)
)

data = get_comparison(mode=mode, monthly_amount=monthly_amount)

st.plotly_chart(build_dca_figure(data["dca"], monthly_amount=monthly_amount), use_container_width=True)
render_data_attribution(data["provider_name"])
st.dataframe(data["dca"], use_container_width=True)
