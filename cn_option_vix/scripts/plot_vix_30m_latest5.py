import os
import pandas as pd
import matplotlib.pyplot as plt

ROOT = "/Users/wonderfulren/Desktop/coding/quant/cn_option_vix"
CSV_PATH = os.path.join(ROOT, "outputs", "vix_30m_latest5.csv")
OUT_DIR = os.path.join(ROOT, "outputs", "plots_30m_latest5")
os.makedirs(OUT_DIR, exist_ok=True)

df = pd.read_csv(CSV_PATH)

# -------- 自动识别时间列 --------
time_col = None
for c in ["timestamp", "datetime", "dt", "time"]:
    if c in df.columns:
        time_col = c
        break

if time_col is None:
    raise ValueError(f"没找到时间列，现有列为: {list(df.columns)}")

df[time_col] = pd.to_datetime(df[time_col])
df = df.sort_values(time_col).reset_index(drop=True)
df["date_only"] = df[time_col].dt.date
df["time_only"] = df[time_col].dt.strftime("%H:%M")

print("columns:", list(df.columns))
print("rows:", len(df))
print(df.head())

# -------- 主要列 --------
main_cols = [
    "overall",
    "index_vix",
    "blue_chip",
    "sz_growth",
    "mid_small",
    "hard_tech",
]
main_cols = [c for c in main_cols if c in df.columns]

spread_cols = []
for c in [
    "spread_index_bluechip",
    "spread_bluechip_szgrowth",
    "index_vix_minus_blue_chip",
    "blue_chip_minus_sz_growth",
]:
    if c in df.columns:
        spread_cols.append(c)

# 如果没有现成 spread 列，就现场计算
if "spread_index_bluechip" not in df.columns and {"index_vix", "blue_chip"}.issubset(df.columns):
    df["spread_index_bluechip"] = df["index_vix"] - df["blue_chip"]
    spread_cols.append("spread_index_bluechip")

if "spread_bluechip_szgrowth" not in df.columns and {"blue_chip", "sz_growth"}.issubset(df.columns):
    df["spread_bluechip_szgrowth"] = df["blue_chip"] - df["sz_growth"]
    spread_cols.append("spread_bluechip_szgrowth")

# 去重
spread_cols = list(dict.fromkeys(spread_cols))

# -------- 图1：全部主 VIX 序列 --------
if main_cols:
    plt.figure(figsize=(16, 7))
    for c in main_cols:
        plt.plot(df[time_col], df[c], marker="o", label=c)
    plt.title("30min VIX Series (Latest 5 Trading Days)")
    plt.xlabel("Time")
    plt.ylabel("VIX")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    out1 = os.path.join(OUT_DIR, "01_main_vix_series.png")
    plt.savefig(out1, dpi=180)
    plt.close()
    print("saved:", out1)

# -------- 图2：spread 序列 --------
if spread_cols:
    plt.figure(figsize=(16, 6))
    for c in spread_cols:
        plt.plot(df[time_col], df[c], marker="o", label=c)
    plt.axhline(0.0, linewidth=1)
    plt.title("30min VIX Spreads (Latest 5 Trading Days)")
    plt.xlabel("Time")
    plt.ylabel("Spread")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    out2 = os.path.join(OUT_DIR, "02_spread_series.png")
    plt.savefig(out2, dpi=180)
    plt.close()
    print("saved:", out2)

# -------- 图3：每天单独画主 VIX --------
if main_cols:
    unique_dates = list(df["date_only"].unique())
    for d in unique_dates:
        sub = df[df["date_only"] == d].copy()
        plt.figure(figsize=(12, 6))
        for c in main_cols:
            plt.plot(sub["time_only"], sub[c], marker="o", label=c)
        plt.title(f"30min VIX Intraday - {d}")
        plt.xlabel("Time")
        plt.ylabel("VIX")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        outp = os.path.join(OUT_DIR, f"day_main_vix_{d}.png")
        plt.savefig(outp, dpi=180)
        plt.close()
        print("saved:", outp)

# -------- 图4：每天单独画 spread --------
if spread_cols:
    unique_dates = list(df["date_only"].unique())
    for d in unique_dates:
        sub = df[df["date_only"] == d].copy()
        plt.figure(figsize=(12, 5))
        for c in spread_cols:
            plt.plot(sub["time_only"], sub[c], marker="o", label=c)
        plt.axhline(0.0, linewidth=1)
        plt.title(f"30min Spread Intraday - {d}")
        plt.xlabel("Time")
        plt.ylabel("Spread")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        outp = os.path.join(OUT_DIR, f"day_spread_{d}.png")
        plt.savefig(outp, dpi=180)
        plt.close()
        print("saved:", outp)

# -------- 图5：如果有单品种 iv_ 列，也一起画 --------
iv_cols = [c for c in df.columns if c.startswith("iv_")]
if iv_cols:
    plt.figure(figsize=(16, 8))
    for c in iv_cols:
        plt.plot(df[time_col], df[c], marker="o", label=c)
    plt.title("30min Instrument-level IV / VIX Series")
    plt.xlabel("Time")
    plt.ylabel("Value")
    plt.legend(ncol=3, fontsize=8)
    plt.grid(True)
    plt.tight_layout()
    out5 = os.path.join(OUT_DIR, "03_instrument_iv_series.png")
    plt.savefig(out5, dpi=180)
    plt.close()
    print("saved:", out5)

print("\n全部完成，输出目录：", OUT_DIR)