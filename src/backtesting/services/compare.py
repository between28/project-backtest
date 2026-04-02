from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from backtesting.analytics.alignment import common_window
from backtesting.analytics.risk import summarize_prices
from backtesting.analytics.returns import monthly_dca_terminal_values
from backtesting.config import load_assets_config, load_proxy_rules, load_settings
from backtesting.data.fetch import fetch_price_history, resolve_history_provider_name
from backtesting.domain.assets import Asset, asset_metadata_frame, build_assets
from backtesting.domain.proxy_rules import build_proxy_map


@dataclass(slots=True)
class ComparisonResult:
    assets: list[Asset]
    raw_prices: pd.DataFrame
    comparison_prices: pd.DataFrame
    summary: pd.DataFrame
    dca_terminal: pd.DataFrame
    metadata: pd.DataFrame
    mode: str
    monthly_amount: float
    provider_name: str


def load_asset_universe() -> list[Asset]:
    asset_rows = load_assets_config()
    proxy_rows = load_proxy_rules()
    proxy_map = build_proxy_map(proxy_rows)
    return build_assets(asset_rows, proxy_map)


def extend_history_with_proxy(
    actual_prices: pd.Series,
    proxy_prices: pd.Series,
    series_name: str,
) -> pd.Series:
    actual = actual_prices.dropna()
    proxy = proxy_prices.dropna()

    if actual.empty:
        raise ValueError(f"No live history found for {series_name}.")
    if proxy.empty:
        return actual.rename(series_name)

    shared_dates = proxy.index.intersection(actual.index)
    shared_dates = shared_dates[shared_dates >= actual.index.min()]
    if shared_dates.empty:
        return actual.rename(series_name)

    join_date = shared_dates.min()
    scale = actual.loc[join_date] / proxy.loc[join_date]
    proxy_prior = proxy.loc[proxy.index < join_date] * scale

    combined = pd.concat([proxy_prior, actual.loc[actual.index >= join_date]])
    combined = combined[~combined.index.duplicated(keep="last")]
    combined.name = series_name
    return combined


def build_comparison(
    mode: str | None = None,
    monthly_amount: float | None = None,
) -> ComparisonResult:
    settings = load_settings()
    comparison_mode = mode or settings["default_mode"]
    monthly_contribution = monthly_amount or settings["default_monthly_dca"]
    provider_name = resolve_history_provider_name(settings.get("history_provider"))
    if comparison_mode not in {"actual", "proxy_extended"}:
        raise ValueError(f"Unsupported comparison mode: {comparison_mode}")

    assets = load_asset_universe()
    tickers_to_download = sorted(
        {
            asset.ticker
            for asset in assets
        }
        | {
            asset.proxy_ticker
            for asset in assets
            if asset.proxy_ticker
        }
    )

    raw_prices = fetch_price_history(
        tickers=tickers_to_download,
        start=settings.get("start_date"),
        end=settings.get("end_date"),
        provider=provider_name,
        cache_ttl_hours=int(settings.get("cache_ttl_hours", 24)),
        interval=settings.get("default_interval", "1day"),
    )

    comparison_series: dict[str, pd.Series] = {}
    for asset in assets:
        if asset.ticker not in raw_prices.columns:
            raise ValueError(f"Ticker {asset.ticker} was not returned by the price provider.")

        actual_series = raw_prices[asset.ticker]
        if comparison_mode == "proxy_extended" and asset.proxy_ticker:
            proxy_series = raw_prices[asset.proxy_ticker]
            comparison_series[asset.ticker] = extend_history_with_proxy(actual_series, proxy_series, asset.ticker)
        else:
            comparison_series[asset.ticker] = actual_series.dropna().rename(asset.ticker)

    comparison_prices = common_window(pd.DataFrame(comparison_series))
    summary = summarize_prices(comparison_prices)
    dca_terminal = monthly_dca_terminal_values(comparison_prices, monthly_amount=monthly_contribution)
    metadata = asset_metadata_frame(assets)

    return ComparisonResult(
        assets=assets,
        raw_prices=raw_prices,
        comparison_prices=comparison_prices,
        summary=summary,
        dca_terminal=dca_terminal,
        metadata=metadata,
        mode=comparison_mode,
        monthly_amount=monthly_contribution,
        provider_name=provider_name,
    )
