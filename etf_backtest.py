"""
ETF long-term backtest for life-long investing candidates.

Method:
- Uses Adjusted Close via yfinance (total-return approximation including dividends).
- Compares:
    * VOO  : Vanguard S&P 500 ETF
    * SCHG : Schwab U.S. Large-Cap Growth ETF
    * VUG  : Vanguard Growth ETF
    * FTEC : Fidelity MSCI Information Technology Index ETF
    * VGT  : Vanguard Information Technology ETF
    * QQQM : Invesco NASDAQ 100 ETF
- For QQQM, extends history prior to 2020-10-13 with QQQ as a proxy because both track the NASDAQ-100.
  This is not perfect because fees differ (QQQ higher) and there can be small tracking differences.

Outputs:
- summary_actual_history.csv   : actual ETF histories only
- summary_proxy_extended.csv   : includes QQQ proxy extension for QQQM
- wealth_actual.png            : growth of $10,000 on common actual-history window
- wealth_proxy.png             : growth of $10,000 on proxy-extended window
- drawdown_proxy.png           : drawdown chart on proxy-extended window

Run:
    pip install yfinance pandas numpy matplotlib
    python etf_backtest.py
"""

import warnings
warnings.filterwarnings("ignore")

from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

try:
    import yfinance as yf
except ImportError as e:
    raise SystemExit("Please install yfinance: pip install yfinance") from e


START = "1999-03-10"   # QQQ inception; enables long NASDAQ proxy history
END = None             # today
OUTDIR = Path("etf_backtest_output")
OUTDIR.mkdir(exist_ok=True)

TICKERS = ["VOO", "SCHG", "VUG", "FTEC", "VGT", "QQQM", "QQQ"]


@dataclass
class Metrics:
    cagr: float
    annual_vol: float
    sharpe_rf0: float
    max_drawdown: float
    calmar: float
    total_return: float
    start: str
    end: str
    years: float


def download_adj_close(tickers, start=START, end=END) -> pd.DataFrame:
    data = yf.download(
        tickers=tickers,
        start=start,
        end=end,
        auto_adjust=False,
        progress=False,
        group_by="ticker",
        actions=False,
        threads=True,
    )

    # yfinance shape varies by version; normalize to DataFrame of Adj Close columns.
    if isinstance(data.columns, pd.MultiIndex):
        if "Adj Close" in data.columns.get_level_values(0):
            adj = data["Adj Close"].copy()
        else:
            # format like (ticker, field)
            pieces = {}
            for t in tickers:
                if (t, "Adj Close") in data.columns:
                    pieces[t] = data[(t, "Adj Close")]
            adj = pd.DataFrame(pieces)
    else:
        # single ticker fallback
        if "Adj Close" in data.columns:
            adj = data[["Adj Close"]].rename(columns={"Adj Close": tickers[0]})
        else:
            raise ValueError("Adjusted close not found in downloaded data.")

    adj = adj.sort_index()
    adj = adj.dropna(how="all")
    return adj


def make_qqqm_proxy(adj: pd.DataFrame) -> pd.Series:
    qqq = adj["QQQ"].dropna().copy()
    qqqm = adj["QQQM"].dropna().copy()
    if qqqm.empty:
        raise ValueError("QQQM history not found.")
    if qqq.empty:
        raise ValueError("QQQ history not found.")

    start_qqqm = qqqm.index.min()

    # Scale QQQ history so level matches QQQM at first live day.
    prior = qqq.loc[qqq.index < start_qqqm]
    if prior.empty:
        return qqqm.rename("QQQM_proxy")

    scale = qqqm.iloc[0] / qqq.loc[start_qqqm]
    prior_scaled = prior * scale

    combined = pd.concat([prior_scaled, qqqm])
    combined = combined[~combined.index.duplicated(keep="last")]
    combined.name = "QQQM_proxy"
    return combined


def common_window(df: pd.DataFrame) -> pd.DataFrame:
    valid_starts = df.apply(lambda s: s.dropna().index.min())
    start = valid_starts.max()
    out = df.loc[start:].dropna()
    return out


def compute_metrics(prices: pd.Series) -> Metrics:
    prices = prices.dropna()
    rets = prices.pct_change().dropna()
    n = len(rets)
    if n == 0:
        raise ValueError("No returns available.")
    years = (prices.index[-1] - prices.index[0]).days / 365.25
    total_return = prices.iloc[-1] / prices.iloc[0] - 1
    cagr = (prices.iloc[-1] / prices.iloc[0]) ** (1 / years) - 1 if years > 0 else np.nan
    vol = rets.std() * np.sqrt(252)
    sharpe = (rets.mean() * 252) / vol if vol > 0 else np.nan
    wealth = (1 + rets).cumprod()
    peak = wealth.cummax()
    dd = wealth / peak - 1
    max_dd = dd.min()
    calmar = cagr / abs(max_dd) if max_dd < 0 else np.nan

    return Metrics(
        cagr=cagr,
        annual_vol=vol,
        sharpe_rf0=sharpe,
        max_drawdown=max_dd,
        calmar=calmar,
        total_return=total_return,
        start=str(prices.index[0].date()),
        end=str(prices.index[-1].date()),
        years=years,
    )


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    rows = {}
    for col in df.columns:
        m = compute_metrics(df[col])
        rows[col] = {
            "start": m.start,
            "end": m.end,
            "years": round(m.years, 2),
            "total_return_%": round(m.total_return * 100, 2),
            "CAGR_%": round(m.cagr * 100, 2),
            "vol_%": round(m.annual_vol * 100, 2),
            "Sharpe_rf0": round(m.sharpe_rf0, 3),
            "max_drawdown_%": round(m.max_drawdown * 100, 2),
            "Calmar": round(m.calmar, 3),
        }
    out = pd.DataFrame(rows).T
    out = out.sort_values(["CAGR_%", "Sharpe_rf0"], ascending=False)
    return out


def plot_wealth(df: pd.DataFrame, title: str, filename: Path):
    wealth = df / df.iloc[0] * 10000
    plt.figure(figsize=(11, 6))
    for col in wealth.columns:
        plt.plot(wealth.index, wealth[col], label=col)
    plt.yscale("log")
    plt.title(title)
    plt.ylabel("Portfolio value ($, log scale)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(filename, dpi=180)
    plt.close()


def plot_drawdown(df: pd.DataFrame, title: str, filename: Path):
    plt.figure(figsize=(11, 6))
    for col in df.columns:
        wealth = df[col] / df[col].iloc[0]
        dd = wealth / wealth.cummax() - 1
        plt.plot(dd.index, dd, label=col)
    plt.title(title)
    plt.ylabel("Drawdown")
    plt.legend()
    plt.tight_layout()
    plt.savefig(filename, dpi=180)
    plt.close()


def monthly_dca(prices: pd.DataFrame, monthly_amount=1000) -> pd.Series:
    month_ends = prices.resample("M").last().dropna(how="all")
    shares = pd.DataFrame(index=month_ends.index, columns=month_ends.columns, dtype=float)
    for col in month_ends.columns:
        shares[col] = (monthly_amount / month_ends[col]).where(month_ends[col].notna(), 0.0)
    cumulative_shares = shares.cumsum()
    values = cumulative_shares * month_ends
    return values.iloc[-1]


def main():
    adj = download_adj_close(TICKERS)

    # Actual-history comparison: exclude QQQ proxy, use only actual ETF data on common overlap.
    actual = adj[["VOO", "SCHG", "VUG", "FTEC", "VGT", "QQQM"]].copy()
    actual_common = common_window(actual)
    actual_summary = summarize(actual_common)
    actual_summary.to_csv(OUTDIR / "summary_actual_history.csv")

    # Proxy-extended comparison: replace QQQM with QQQ proxy-extended series.
    qqqm_proxy = make_qqqm_proxy(adj)
    proxy_df = pd.concat(
        [
            adj["VOO"],
            adj["SCHG"],
            adj["VUG"],
            adj["FTEC"],
            adj["VGT"],
            qqqm_proxy,
        ],
        axis=1,
    )
    proxy_df.columns = ["VOO", "SCHG", "VUG", "FTEC", "VGT", "QQQM_proxy"]
    proxy_common = common_window(proxy_df)
    proxy_summary = summarize(proxy_common)
    proxy_summary.to_csv(OUTDIR / "summary_proxy_extended.csv")

    # DCA comparison on proxy-extended common window
    dca_terminal = monthly_dca(proxy_common, monthly_amount=1000)
    dca_df = dca_terminal.rename("terminal_value_from_$1000_monthly").to_frame()
    dca_df["rank"] = dca_df["terminal_value_from_$1000_monthly"].rank(ascending=False, method="min")
    dca_df = dca_df.sort_values("terminal_value_from_$1000_monthly", ascending=False)
    dca_df.to_csv(OUTDIR / "monthly_dca_proxy_extended.csv")

    # Plots
    plot_wealth(actual_common, "Growth of $10,000 — actual ETF history common window", OUTDIR / "wealth_actual.png")
    plot_wealth(proxy_common, "Growth of $10,000 — proxy-extended common window", OUTDIR / "wealth_proxy.png")
    plot_drawdown(proxy_common, "Drawdowns — proxy-extended common window", OUTDIR / "drawdown_proxy.png")

    print("\n=== Actual ETF history (common overlap) ===")
    print(actual_summary.to_string())
    print("\n=== Proxy-extended (QQQM extended with QQQ prior to 2020-10-13) ===")
    print(proxy_summary.to_string())
    print("\n=== Monthly DCA ($1,000/month) terminal values on proxy-extended window ===")
    print(dca_df.to_string())
    print(f"\nSaved outputs to: {OUTDIR.resolve()}")


if __name__ == "__main__":
    main()
