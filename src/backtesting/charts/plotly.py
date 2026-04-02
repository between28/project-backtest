from __future__ import annotations

import plotly.graph_objects as go
import pandas as pd

from backtesting.analytics.returns import drawdown, wealth_index


PLOT_BACKGROUND = "rgba(255,252,247,0.65)"
PAPER_BACKGROUND = "rgba(0,0,0,0)"
GRID_COLOR = "rgba(92, 64, 51, 0.16)"
PALETTE = [
    "#8c2f39",
    "#cc5803",
    "#f4b942",
    "#0f4c5c",
    "#5f0f40",
    "#335c67",
    "#6c584c",
    "#9c6644",
    "#386641",
]


def _base_layout(title: str) -> dict:
    return {
        "title": title,
        "plot_bgcolor": PLOT_BACKGROUND,
        "paper_bgcolor": PAPER_BACKGROUND,
        "font": {"family": "Georgia, serif", "color": "#1f1a17"},
        "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        "margin": {"l": 20, "r": 20, "t": 60, "b": 20},
    }


def build_wealth_figure(prices: pd.DataFrame, initial_value: float = 10_000) -> go.Figure:
    wealth = wealth_index(prices, initial_value=initial_value)
    figure = go.Figure()
    for index, ticker in enumerate(wealth.columns):
        figure.add_trace(
            go.Scatter(
                x=wealth.index,
                y=wealth[ticker],
                mode="lines",
                line={"width": 2.5, "color": PALETTE[index % len(PALETTE)]},
                name=ticker,
            )
        )
    figure.update_layout(**_base_layout(f"Growth of ${initial_value:,.0f}"))
    figure.update_yaxes(type="log", title="Portfolio Value", gridcolor=GRID_COLOR)
    figure.update_xaxes(gridcolor=GRID_COLOR)
    return figure


def build_drawdown_figure(prices: pd.DataFrame) -> go.Figure:
    drawdown_frame = drawdown(prices)
    figure = go.Figure()
    for index, ticker in enumerate(drawdown_frame.columns):
        figure.add_trace(
            go.Scatter(
                x=drawdown_frame.index,
                y=drawdown_frame[ticker],
                mode="lines",
                line={"width": 2.5, "color": PALETTE[index % len(PALETTE)]},
                name=ticker,
            )
        )
    figure.update_layout(**_base_layout("Drawdown History"))
    figure.update_yaxes(title="Drawdown", tickformat=".0%", gridcolor=GRID_COLOR)
    figure.update_xaxes(gridcolor=GRID_COLOR)
    return figure


def build_dca_figure(dca_frame: pd.DataFrame, monthly_amount: float) -> go.Figure:
    ordered = dca_frame.sort_values("terminal_value", ascending=False)
    figure = go.Figure(
        go.Bar(
            x=ordered.index,
            y=ordered["terminal_value"],
            marker={"color": [PALETTE[index % len(PALETTE)] for index in range(len(ordered))]},
        )
    )
    figure.update_layout(**_base_layout(f"Terminal Value From ${monthly_amount:,.0f}/Month"))
    figure.update_yaxes(title="Terminal Value", gridcolor=GRID_COLOR)
    figure.update_xaxes(title="Ticker")
    return figure


def build_market_figure(prices: pd.DataFrame, mode: str) -> go.Figure:
    prepared, yaxis_title, tickformat = _prepare_market_frame(prices, mode)
    figure = go.Figure()
    for index, ticker in enumerate(prepared.columns):
        figure.add_trace(
            go.Scatter(
                x=prepared.index,
                y=prepared[ticker],
                mode="lines",
                line={"width": 2.4, "color": PALETTE[index % len(PALETTE)]},
                name=ticker,
                connectgaps=False,
            )
        )

    figure.update_layout(**_base_layout(mode))
    figure.update_yaxes(title=yaxis_title, tickformat=tickformat, gridcolor=GRID_COLOR)
    figure.update_xaxes(gridcolor=GRID_COLOR)
    return figure


def _prepare_market_frame(prices: pd.DataFrame, mode: str) -> tuple[pd.DataFrame, str, str | None]:
    if mode == "Price":
        return prices, "Adjusted Close", None

    normalized = prices.apply(_normalize_series_to_100)
    if mode == "Normalized":
        return normalized, "Indexed Level (100 = first point)", None
    if mode == "Return %":
        return normalized.div(100.0).sub(1.0), "Total Return", ".0%"
    if mode == "Drawdown":
        drawdown_frame = normalized.apply(_drawdown_series)
        return drawdown_frame, "Drawdown", ".0%"

    raise ValueError(f"Unsupported chart mode: {mode}")


def _normalize_series_to_100(series: pd.Series) -> pd.Series:
    clean = series.dropna()
    if clean.empty:
        return series
    return series / clean.iloc[0] * 100.0


def _drawdown_series(series: pd.Series) -> pd.Series:
    clean = series.dropna()
    if clean.empty:
        return series
    return series / series.cummax() - 1.0
