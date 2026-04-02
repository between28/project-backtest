from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from apps.dashboard.common import configure_page, get_comparison, render_data_attribution
from backtesting.charts.plotly import build_drawdown_figure


configure_page("ETF Drawdowns")

st.title("Drawdown Comparison")

mode = st.selectbox(
    "History mode",
    options=["proxy_extended", "actual"],
    format_func=lambda value: "Proxy-Extended" if value == "proxy_extended" else "Actual Only",
)

data = get_comparison(mode=mode, monthly_amount=1000)

st.plotly_chart(build_drawdown_figure(data["prices"]), use_container_width=True)
render_data_attribution(data["provider_name"])
st.dataframe(
    data["summary"][["max_drawdown_pct", "calmar", "start", "end", "years"]],
    use_container_width=True,
)
