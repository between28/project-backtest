from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from apps.dashboard.common import configure_page, get_comparison, render_data_attribution
from backtesting.charts.plotly import build_dca_figure, build_wealth_figure


configure_page("ETF Compare")

st.title("Compare Total Return Histories")

with st.sidebar:
    mode = st.selectbox(
        "History mode",
        options=["proxy_extended", "actual"],
        format_func=lambda value: "Proxy-Extended" if value == "proxy_extended" else "Actual Only",
    )
    monthly_amount = int(
        st.number_input("Monthly DCA amount", min_value=100, max_value=100000, value=1000, step=100)
    )

data = get_comparison(mode=mode, monthly_amount=monthly_amount)
summary = data["summary"]
metadata = data["metadata"]
combined = metadata.join(summary, how="right")

st.caption(
    "Proxy-extended mode stitches older proxy ETFs before the target ETF has live history. "
    "Use actual-only mode when you want strict live ETF overlap."
)

top_cols = st.columns(3)
top_cols[0].metric("Assets Compared", int(len(combined)))
top_cols[1].metric("Common Window Start", str(summary["start"].min()))
top_cols[2].metric("Monthly DCA", f"${monthly_amount:,.0f}")

st.plotly_chart(build_wealth_figure(data["prices"]), use_container_width=True)
render_data_attribution(data["provider_name"])

st.subheader("Summary Table")
st.dataframe(
    combined.reset_index().rename(columns={"index": "ticker"}),
    use_container_width=True,
    hide_index=True,
)

st.subheader("DCA Terminal Value")
st.plotly_chart(build_dca_figure(data["dca"], monthly_amount=monthly_amount), use_container_width=True)
