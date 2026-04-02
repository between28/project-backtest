from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from apps.dashboard.common import configure_page, get_asset_metadata, get_proxy_rules


configure_page("ETF Universe")

st.title("Universe And Proxy Config")

assets = pd.DataFrame(get_asset_metadata())
proxies = pd.DataFrame(get_proxy_rules())

st.subheader("Assets")
st.dataframe(assets, use_container_width=True, hide_index=True)

st.subheader("Proxy Rules")
st.dataframe(proxies, use_container_width=True, hide_index=True)

