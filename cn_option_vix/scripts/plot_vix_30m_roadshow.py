"""Create slide-ready 16:9 charts from the full 30-minute VIX history."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parent.parent

PALETTE = {
    "navy": "#102A43",
    "blue": "#2F6BFF",
    "light_blue": "#DCE8FF",
    "gold": "#C98A16",
    "grid": "#D9E2EC",
    "text": "#243B53",
    "muted": "#6B7C93",
    "index_vix": "#526D82",
    "blue_chip": "#2F6BFF",
    "sz_growth": "#8A5CF6",
    "mid_small": "#D97706",
    "hard_tech": "#0F9D8A",
}


def _select_font(language: str) -> str:
    candidates = (
        ["PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "SimHei"]
        if language == "zh"
        else ["Avenir Next", "Helvetica Neue", "Arial", "DejaVu Sans"]
    )
    available = {f.name for f in font_manager.fontManager.ttflist}
    return next((name for name in candidates if name in available), "DejaVu Sans")


def _read(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    time_col = next(
        (c for c in ("timestamp", "datetime", "date") if c in df.columns), None
    )
    if time_col is None:
        raise ValueError(f"No timestamp column found. Columns: {list(df.columns)}")
    df["timestamp"] = pd.to_datetime(df[time_col], errors="raise")
    df = df.sort_values("timestamp").drop_duplicates("timestamp", keep="last")
    if "overall" not in df.columns:
        raise ValueError("Input has no 'overall' column")
    df["overall"] = pd.to_numeric(df["overall"], errors="coerce")
    return df


def _daily(df: pd.DataFrame) -> pd.DataFrame:
    x = df.set_index("timestamp").copy()
    numeric_cols = [
        c
        for c in [
            "overall",
            "index_vix",
            "blue_chip",
            "sz_growth",
            "mid_small",
            "hard_tech",
        ]
        if c in x.columns
    ]
    for col in numeric_cols:
        x[col] = pd.to_numeric(x[col], errors="coerce")

    grouped = x.groupby(x.index.normalize())
    out = pd.DataFrame(index=sorted(x.index.normalize().unique()))
    out.index.name = "date"
    out["overall_close"] = grouped["overall"].last()
    out["overall_low"] = grouped["overall"].min()
    out["overall_high"] = grouped["overall"].max()
    out["overall_median"] = grouped["overall"].median()
    for col in numeric_cols:
        out[col] = grouped[col].last()
    out["trend_20d"] = out["overall_close"].rolling(20, min_periods=5).median()
    return out


def _base_style(language: str) -> None:
    plt.rcParams.update(
        {
            "font.family": _select_font(language),
            "axes.unicode_minus": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "font.size": 10,
        }
    )


def _format_axis(ax, daily: pd.DataFrame) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(PALETTE["grid"])
    ax.spines["bottom"].set_color(PALETTE["grid"])
    ax.grid(axis="y", color=PALETTE["grid"], linewidth=0.8, alpha=0.65)
    ax.grid(axis="x", visible=False)
    ax.tick_params(colors=PALETTE["muted"], labelsize=9)
    span_days = max(1, (daily.index.max() - daily.index.min()).days)
    interval = 2 if span_days > 450 else 1
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=interval))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    ax.set_xlim(daily.index.min(), daily.index.max() + pd.Timedelta(days=18))


def plot_overall(daily: pd.DataFrame, out_dir: Path, language: str) -> None:
    zh = language == "zh"
    title = "中国金融期权综合 VIX｜两年趋势" if zh else "China Financial Options VIX | Two-Year Trend"
    subtitle = (
        "30分钟观测 · 30天恒定期限 · 持仓量加权"
        if zh
        else "30-minute observations · 30-day constant maturity · Open-interest weighted"
    )
    source = (
        "数据：RQData；阴影为每日30分钟高低区间；粗线为每日收盘值。"
        if zh
        else "Source: RQData. Shading shows each day's 30-minute range; bold line is the daily close."
    )

    d = daily.dropna(subset=["overall_close"]).copy()
    if d.empty:
        raise RuntimeError("No valid overall VIX observations")

    fig, ax = plt.subplots(figsize=(13.333, 7.5))
    fig.subplots_adjust(left=0.075, right=0.94, top=0.82, bottom=0.16)

    ax.fill_between(
        d.index,
        d["overall_low"].to_numpy(),
        d["overall_high"].to_numpy(),
        color=PALETTE["light_blue"],
        alpha=0.78,
        linewidth=0,
        label="Intraday range",
    )
    ax.plot(
        d.index,
        d["overall_close"],
        color=PALETTE["navy"],
        linewidth=2.0,
        solid_capstyle="round",
        label="Daily close",
        zorder=3,
    )
    ax.plot(
        d.index,
        d["trend_20d"],
        color=PALETTE["gold"],
        linewidth=1.4,
        linestyle=(0, (4, 3)),
        label="20-day trend",
        zorder=4,
    )

    _format_axis(ax, d)
    ax.set_ylabel("VIX", color=PALETTE["text"], fontsize=10, labelpad=10)

    fig.text(0.075, 0.925, title, fontsize=23, fontweight="bold", color=PALETTE["navy"])
    fig.text(0.075, 0.875, subtitle, fontsize=11.5, color=PALETTE["muted"])
    fig.text(0.075, 0.055, source, fontsize=8.5, color=PALETTE["muted"])

    last_date = d.index[-1]
    last_val = float(d["overall_close"].iloc[-1])
    high_date = d["overall_high"].idxmax()
    high_val = float(d.loc[high_date, "overall_high"])
    low_date = d["overall_low"].idxmin()
    low_val = float(d.loc[low_date, "overall_low"])

    ax.scatter([last_date], [last_val], s=32, color=PALETTE["blue"], zorder=6)
    ax.annotate(
        f"{last_val:.1f}",
        xy=(last_date, last_val),
        xytext=(10, 0),
        textcoords="offset points",
        va="center",
        fontsize=10.5,
        fontweight="bold",
        color="white",
        bbox=dict(boxstyle="round,pad=0.32", fc=PALETTE["blue"], ec="none"),
    )

    stats_title = "最新 / 高点 / 低点" if zh else "LAST / HIGH / LOW"
    stats_value = f"{last_val:.1f}   {high_val:.1f}   {low_val:.1f}"
    fig.text(0.925, 0.925, stats_title, ha="right", fontsize=8.5, color=PALETTE["muted"])
    fig.text(0.925, 0.885, stats_value, ha="right", fontsize=14, fontweight="bold", color=PALETTE["navy"])

    # Only mark the global extremes; avoid event clutter.
    ax.annotate(
        f"{high_val:.1f}",
        xy=(high_date, high_val),
        xytext=(0, 13),
        textcoords="offset points",
        ha="center",
        fontsize=8.5,
        color=PALETTE["muted"],
    )
    ax.annotate(
        f"{low_val:.1f}",
        xy=(low_date, low_val),
        xytext=(0, -17),
        textcoords="offset points",
        ha="center",
        fontsize=8.5,
        color=PALETTE["muted"],
    )

    ax.legend(
        loc="upper left",
        bbox_to_anchor=(0.0, 1.01),
        ncol=3,
        frameon=False,
        fontsize=9,
        labelcolor=PALETTE["muted"],
        handlelength=2.4,
    )

    png = out_dir / "roadshow_vix_overall_2y.png"
    svg = out_dir / "roadshow_vix_overall_2y.svg"
    fig.savefig(png, dpi=320, bbox_inches="tight")
    fig.savefig(svg, bbox_inches="tight")
    plt.close(fig)
    print("saved:", png)
    print("saved:", svg)


def plot_segments(daily: pd.DataFrame, out_dir: Path, language: str) -> None:
    zh = language == "zh"
    labels = {
        "overall": "综合" if zh else "Overall",
        "index_vix": "股指期权" if zh else "Index options",
        "blue_chip": "大盘蓝筹" if zh else "Blue chip",
        "sz_growth": "深市成长" if zh else "SZ growth",
        "mid_small": "中小盘" if zh else "Mid-small cap",
        "hard_tech": "硬科技" if zh else "Hard tech",
    }
    cols = [c for c in labels if c in daily.columns]
    d = daily.dropna(how="all", subset=cols).copy()
    if not cols or d.empty:
        return

    fig, ax = plt.subplots(figsize=(13.333, 7.5))
    fig.subplots_adjust(left=0.075, right=0.94, top=0.82, bottom=0.16)

    for col in cols:
        if col == "overall":
            color, width, alpha, z = PALETTE["navy"], 2.4, 1.0, 5
        else:
            color, width, alpha, z = PALETTE.get(col, PALETTE["muted"]), 1.25, 0.82, 3
        ax.plot(d.index, d[col], label=labels[col], color=color, linewidth=width, alpha=alpha, zorder=z)

    _format_axis(ax, d)
    ax.set_ylabel("VIX", color=PALETTE["text"], fontsize=10, labelpad=10)
    title = "中国金融期权 VIX｜市场板块对比" if zh else "China Financial Options VIX | Market Segment Comparison"
    subtitle = "每日最后一个30分钟观测值" if zh else "Daily final 30-minute observation"
    source = "数据：RQData" if zh else "Source: RQData"
    fig.text(0.075, 0.925, title, fontsize=23, fontweight="bold", color=PALETTE["navy"])
    fig.text(0.075, 0.875, subtitle, fontsize=11.5, color=PALETTE["muted"])
    fig.text(0.075, 0.055, source, fontsize=8.5, color=PALETTE["muted"])
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(0.0, 1.01),
        ncol=3,
        frameon=False,
        fontsize=9,
        labelcolor=PALETTE["muted"],
        handlelength=2.4,
    )

    png = out_dir / "roadshow_vix_segments_2y.png"
    svg = out_dir / "roadshow_vix_segments_2y.svg"
    fig.savefig(png, dpi=320, bbox_inches="tight")
    fig.savefig(svg, bbox_inches="tight")
    plt.close(fig)
    print("saved:", png)
    print("saved:", svg)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(ROOT / "outputs" / "vix_30m_2y.csv"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "outputs" / "roadshow_2y"),
    )
    parser.add_argument("--language", choices=["en", "zh"], default="en")
    args = parser.parse_args()

    _base_style(args.language)
    input_path = Path(args.input).expanduser().resolve()
    out_dir = Path(args.output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    df = _read(input_path)
    daily = _daily(df)
    plot_overall(daily, out_dir, args.language)
    plot_segments(daily, out_dir, args.language)


if __name__ == "__main__":
    main()
