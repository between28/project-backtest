from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from apps.dashboard.common import (
    configure_page,
    get_market_explorer,
    get_market_search_results,
    get_search_filter_options_cached,
    get_settings,
    render_data_attribution,
)
from backtesting.charts.plotly import build_market_figure
from backtesting.domain.instruments import build_instrument_key, parse_instrument_key


configure_page("Market Explorer")


DEFAULT_KEYS = [
    build_instrument_key("VOO", instrument_type="ETF"),
    build_instrument_key("QQQ", instrument_type="ETF"),
    build_instrument_key("GLD", instrument_type="ETF"),
]
CHART_MODE_OPTIONS = ["Normalized", "Price", "Return %", "Drawdown"]
INTERVAL_OPTIONS = ["1day", "1week", "1month"]
PERIOD_OPTIONS = ["YTD", "1Y", "3Y", "5Y", "10Y", "MAX", "CUSTOM"]


def _label_for_key(key: str) -> str:
    lookup = st.session_state.setdefault("explorer_lookup", {})
    if key in lookup:
        return lookup[key]
    symbol, exchange, instrument_type = parse_instrument_key(key)
    details = [part for part in [exchange, instrument_type] if part]
    if details:
        return f"{symbol} ({', '.join(details)})"
    return symbol


def _default_custom_dates() -> tuple[date, date]:
    end_value = date.today()
    start_value = date(end_value.year - 5, end_value.month, min(end_value.day, 28))
    return start_value, end_value


def _resolve_period(period: str) -> tuple[str | None, str]:
    today = pd.Timestamp(date.today())
    if period == "MAX":
        return None, today.strftime("%Y-%m-%d")
    if period == "YTD":
        start = pd.Timestamp(year=today.year, month=1, day=1)
    elif period == "1Y":
        start = today - pd.DateOffset(years=1)
    elif period == "3Y":
        start = today - pd.DateOffset(years=3)
    elif period == "5Y":
        start = today - pd.DateOffset(years=5)
    elif period == "10Y":
        start = today - pd.DateOffset(years=10)
    else:
        raise ValueError(f"Unsupported period: {period}")
    return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")


def _coerce_choice(value: str | None, allowed: list[str], fallback: str) -> str:
    if value in allowed:
        return str(value)
    return fallback


def _coerce_date(value: str | None, fallback: date) -> date:
    if not value:
        return fallback
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return fallback


def _coerce_multi(values: list[str], allowed: list[str]) -> list[str]:
    allowed_set = set(allowed)
    return [value for value in values if value in allowed_set]


def _initialize_state_from_query_params(type_options: list[str], exchange_options: list[str]) -> None:
    if st.session_state.get("explorer_initialized"):
        return

    default_start, default_end = _default_custom_dates()
    selected = [value for value in st.query_params.get_all("symbol") if value] or DEFAULT_KEYS.copy()

    st.session_state.explorer_selection = selected
    st.session_state.explorer_chart_mode = _coerce_choice(st.query_params.get("mode"), CHART_MODE_OPTIONS, "Normalized")
    st.session_state.explorer_interval = _coerce_choice(st.query_params.get("interval"), INTERVAL_OPTIONS, "1day")
    st.session_state.explorer_period = _coerce_choice(st.query_params.get("period"), PERIOD_OPTIONS, "5Y")
    st.session_state.explorer_query = st.query_params.get("q", "")
    st.session_state.explorer_custom_start = _coerce_date(st.query_params.get("start"), default_start)
    st.session_state.explorer_custom_end = _coerce_date(st.query_params.get("end"), default_end)
    st.session_state.explorer_type_filters = _coerce_multi(st.query_params.get_all("type"), type_options)
    st.session_state.explorer_exchange_filters = _coerce_multi(st.query_params.get_all("exchange"), exchange_options)
    st.session_state.explorer_initialized = True


def _sync_query_params(
    selected_keys: list[str],
    chart_mode: str,
    interval: str,
    period: str,
    start_date: str | None,
    end_date: str,
    search_query: str,
    type_filters: list[str],
    exchange_filters: list[str],
) -> None:
    desired = {
        "symbol": selected_keys,
        "mode": chart_mode,
        "interval": interval,
        "period": period,
    }
    if search_query.strip():
        desired["q"] = search_query.strip()
    if type_filters:
        desired["type"] = type_filters
    if exchange_filters:
        desired["exchange"] = exchange_filters
    if period == "CUSTOM":
        desired["start"] = start_date or ""
        desired["end"] = end_date

    current = {
        "symbol": st.query_params.get_all("symbol"),
        "mode": st.query_params.get("mode", None),
        "interval": st.query_params.get("interval", None),
        "period": st.query_params.get("period", None),
    }
    if st.query_params.get("q", None):
        current["q"] = st.query_params.get("q")
    if st.query_params.get_all("type"):
        current["type"] = st.query_params.get_all("type")
    if st.query_params.get_all("exchange"):
        current["exchange"] = st.query_params.get_all("exchange")
    if st.query_params.get("start", None):
        current["start"] = st.query_params.get("start")
    if st.query_params.get("end", None):
        current["end"] = st.query_params.get("end")

    if current == desired:
        return

    st.query_params.clear()
    for key, value in desired.items():
        st.query_params[key] = value


def _reset_view() -> None:
    default_start, default_end = _default_custom_dates()
    st.session_state.explorer_selection = DEFAULT_KEYS.copy()
    st.session_state.explorer_chart_mode = "Normalized"
    st.session_state.explorer_interval = "1day"
    st.session_state.explorer_period = "5Y"
    st.session_state.explorer_query = ""
    st.session_state.explorer_custom_start = default_start
    st.session_state.explorer_custom_end = default_end
    st.session_state.explorer_type_filters = []
    st.session_state.explorer_exchange_filters = []
    st.query_params.clear()
    st.rerun()


def _move_selection(direction: int) -> None:
    selected_keys = st.session_state.explorer_selection
    active_key = st.session_state.get("explorer_active_key")
    if not active_key or active_key not in selected_keys:
        return

    current_index = selected_keys.index(active_key)
    target_index = current_index + direction
    if target_index < 0 or target_index >= len(selected_keys):
        return

    reordered = selected_keys.copy()
    reordered[current_index], reordered[target_index] = reordered[target_index], reordered[current_index]
    st.session_state.explorer_selection = reordered
    st.rerun()


def _remove_active_selection() -> None:
    selected_keys = st.session_state.explorer_selection
    active_key = st.session_state.get("explorer_active_key")
    if not active_key or active_key not in selected_keys:
        return

    st.session_state.explorer_selection = [key for key in selected_keys if key != active_key]
    remaining = st.session_state.explorer_selection
    st.session_state.explorer_active_key = remaining[0] if remaining else None
    st.rerun()


settings = get_settings()
search_limit = int(settings.get("search_result_limit", 12))
filter_options = get_search_filter_options_cached()
type_options = filter_options.get("instrument_types", []) or ["ETF", "Stock"]
exchange_options = filter_options.get("exchanges", []) or ["NASDAQ", "NYSE", "NYSE ARCA", "AMEX", "ARCA"]
_initialize_state_from_query_params(type_options, exchange_options)

st.title("Market Explorer")
st.caption("Search tickers, add several symbols to a basket, and compare them on one chart.")

with st.sidebar:
    chart_mode = st.selectbox("Chart mode", options=CHART_MODE_OPTIONS, key="explorer_chart_mode")
    interval = st.selectbox("Interval", options=INTERVAL_OPTIONS, key="explorer_interval")
    period = st.selectbox("Period", options=PERIOD_OPTIONS, key="explorer_period")
    type_filters = st.multiselect("Instrument type", options=type_options, key="explorer_type_filters")
    exchange_filters = st.multiselect("Exchange", options=exchange_options, key="explorer_exchange_filters")

    if period == "CUSTOM":
        custom_start = st.date_input("Start date", key="explorer_custom_start")
        custom_end = st.date_input("End date", key="explorer_custom_end")
        start_date = pd.Timestamp(custom_start).strftime("%Y-%m-%d")
        end_date = pd.Timestamp(custom_end).strftime("%Y-%m-%d")
    else:
        start_date, end_date = _resolve_period(period)

    st.caption("Selections on this page are encoded in the URL.")
    if st.button("Reset view", use_container_width=True):
        _reset_view()

query = st.text_input(
    "Search ticker or fund name",
    placeholder="QQQ, VOO, gold, Schwab...",
    key="explorer_query",
)
search_results = get_market_search_results(
    query=query,
    limit=search_limit,
    instrument_types=tuple(type_filters),
    exchanges=tuple(exchange_filters),
)
for item in search_results:
    st.session_state.setdefault("explorer_lookup", {})[item["key"]] = item["label"]

candidate_options = ["__none__"] + [item["key"] for item in search_results]

search_cols = st.columns([2.1, 1.0, 0.9, 0.8])
with search_cols[0]:
    candidate_key = st.selectbox(
        "Matches",
        options=candidate_options,
        format_func=lambda key: "Select a match" if key == "__none__" else _label_for_key(key),
        label_visibility="collapsed",
    )
with search_cols[1]:
    if st.button("Add ticker", use_container_width=True):
        if candidate_key != "__none__" and candidate_key not in st.session_state.explorer_selection:
            st.session_state.explorer_selection.append(candidate_key)
with search_cols[2]:
    manual_symbol = query.strip().upper()
    if st.button("Add raw", use_container_width=True, disabled=not manual_symbol):
        raw_key = build_instrument_key(manual_symbol)
        st.session_state.setdefault("explorer_lookup", {})[raw_key] = manual_symbol
        if raw_key not in st.session_state.explorer_selection:
            st.session_state.explorer_selection.append(raw_key)
with search_cols[3]:
    st.metric("Matches", len(search_results))

selected_keys = st.multiselect(
    "Current basket",
    options=st.session_state.explorer_selection,
    key="explorer_selection",
    format_func=_label_for_key,
)

if st.session_state.explorer_selection:
    st.session_state.setdefault("explorer_active_key", st.session_state.explorer_selection[0])
    if st.session_state.explorer_active_key not in st.session_state.explorer_selection:
        st.session_state.explorer_active_key = st.session_state.explorer_selection[0]

    basket_cols = st.columns([2.3, 0.8, 0.8, 1.0])
    with basket_cols[0]:
        st.selectbox(
            "Reorder basket",
            options=st.session_state.explorer_selection,
            key="explorer_active_key",
            format_func=_label_for_key,
        )
    with basket_cols[1]:
        st.button("Move up", use_container_width=True, on_click=_move_selection, args=(-1,))
    with basket_cols[2]:
        st.button("Move down", use_container_width=True, on_click=_move_selection, args=(1,))
    with basket_cols[3]:
        st.button("Remove", use_container_width=True, on_click=_remove_active_selection)

    st.caption("Line order follows the basket order. Use Move up/down to control legend and color order.")

_sync_query_params(
    selected_keys=selected_keys,
    chart_mode=chart_mode,
    interval=interval,
    period=period,
    start_date=start_date,
    end_date=end_date,
    search_query=query,
    type_filters=type_filters,
    exchange_filters=exchange_filters,
)

if not selected_keys:
    st.info("Add at least one ticker to build a comparison chart.")
    st.stop()

try:
    explorer = get_market_explorer(tuple(selected_keys), start_date, end_date, interval)
except Exception as exc:
    st.error(str(exc))
    st.stop()

summary = explorer["summary"]
prices = explorer["prices"]

metric_cols = st.columns(4)
metric_cols[0].metric("Symbols", int(len(selected_keys)))
metric_cols[1].metric("Provider", explorer["provider_name"])
metric_cols[2].metric("From", explorer["start"] or str(prices.index.min().date()))
metric_cols[3].metric("To", explorer["end"] or str(prices.index.max().date()))

st.plotly_chart(build_market_figure(prices, chart_mode), use_container_width=True)
render_data_attribution(explorer["provider_name"])

st.subheader("Summary")
st.dataframe(
    summary.reset_index().rename(columns={"index": "ticker"}),
    use_container_width=True,
    hide_index=True,
)
