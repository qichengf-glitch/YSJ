import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter

ROOT = "/Users/wonderfulren/Desktop/coding/quant/cn_option_vix"
CSV_PATH = os.path.join(ROOT, "outputs", "vix_30m_2y.csv")
OUT_DIR = os.path.join(ROOT, "outputs", "roadshow_custom")
os.makedirs(OUT_DIR, exist_ok=True)

START = "2024-09-15"
END   = "2024-11-15"

# -----------------------------
# 1) 读数据
# -----------------------------
df = pd.read_csv(CSV_PATH)

time_col = None
for c in ["timestamp", "datetime", "dt", "time"]:
    if c in df.columns:
        time_col = c
        break
if time_col is None:
    raise ValueError(f"没找到时间列，现有列: {list(df.columns)}")

df[time_col] = pd.to_datetime(df[time_col])
df = df.sort_values(time_col).reset_index(drop=True)

need_cols = ["overall", "hard_tech"]
for c in need_cols:
    if c not in df.columns:
        raise ValueError(f"缺少列: {c}")

# 过滤时间区间
start_ts = pd.Timestamp(START)
end_ts = pd.Timestamp(END) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
df = df[(df[time_col] >= start_ts) & (df[time_col] <= end_ts)].copy()

if df.empty:
    raise ValueError("筛选后没有数据，请检查日期范围和 CSV 文件内容。")

df["spread"] = df["hard_tech"] - df["overall"]

# -----------------------------
# 2) 做图风格
# -----------------------------
plt.rcParams["figure.dpi"] = 160
plt.rcParams["savefig.dpi"] = 320
plt.rcParams["font.size"] = 11
plt.rcParams["axes.titlesize"] = 16
plt.rcParams["axes.labelsize"] = 12
plt.rcParams["legend.fontsize"] = 11

# 更接近路演风格的画布比例
fig = plt.figure(figsize=(16, 9))
gs = fig.add_gridspec(nrows=2, ncols=1, height_ratios=[3.2, 1.5], hspace=0.10)
ax1 = fig.add_subplot(gs[0, 0])
ax2 = fig.add_subplot(gs[1, 0], sharex=ax1)

x = df[time_col]
overall = df["overall"]
hard = df["hard_tech"]
spread = df["spread"]

# 颜色：克制专业
c_overall = "#2F3B52"   # 深灰蓝
c_hard    = "#1F77B4"   # 专业蓝
c_pos     = "#4C9F70"   # 正值填充：绿色
c_neg     = "#D96C6C"   # 负值填充：红色
c_fill    = "#AFC7E8"   # 两线之间的淡蓝填充

# -----------------------------
# 3) 上图：overall vs hard_tech
# -----------------------------
ax1.plot(x, overall, linewidth=2.2, label="Overall VIX", color=c_overall)
ax1.plot(x, hard, linewidth=2.4, label="Hard Tech VIX", color=c_hard)

# 线间填充
ax1.fill_between(x, overall, hard, color=c_fill, alpha=0.25)

# 最新点标注
last_idx = df.index[-1]
ax1.scatter(df.loc[last_idx, time_col], df.loc[last_idx, "overall"], s=25, color=c_overall, zorder=5)
ax1.scatter(df.loc[last_idx, time_col], df.loc[last_idx, "hard_tech"], s=25, color=c_hard, zorder=5)

ax1.annotate(
    f"{df.loc[last_idx, 'overall']:.2f}",
    (df.loc[last_idx, time_col], df.loc[last_idx, "overall"]),
    xytext=(8, -5),
    textcoords="offset points",
    color=c_overall,
    fontsize=10,
    weight="bold"
)
ax1.annotate(
    f"{df.loc[last_idx, 'hard_tech']:.2f}",
    (df.loc[last_idx, time_col], df.loc[last_idx, "hard_tech"]),
    xytext=(8, 8),
    textcoords="offset points",
    color=c_hard,
    fontsize=10,
    weight="bold"
)

ax1.set_title("Hard Tech vs Overall VIX (30-Min Frequency)", pad=16, weight="bold")
ax1.set_ylabel("VIX")
ax1.grid(True, which="major", axis="both", alpha=0.22)
ax1.legend(loc="upper left", frameon=False)

# 统计信息写在右上角
spread_mean = spread.mean()
spread_max = spread.max()
spread_min = spread.min()

text_box = (
    f"Period: {START} to {END}\n"
    f"Avg Spread: {spread_mean:.2f}\n"
    f"Max Spread: {spread_max:.2f}\n"
    f"Min Spread: {spread_min:.2f}"
)
ax1.text(
    0.995, 0.98, text_box,
    transform=ax1.transAxes,
    ha="right", va="top",
    fontsize=10,
    bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="#DDDDDD", alpha=0.95)
)

# -----------------------------
# 4) 下图：spread = hard_tech - overall
# -----------------------------
ax2.axhline(0, color="#666666", linewidth=1.1)

# 正负分色 area
ax2.fill_between(x, 0, spread, where=(spread >= 0), interpolate=True, alpha=0.75, color=c_pos, label="Spread > 0")
ax2.fill_between(x, 0, spread, where=(spread < 0), interpolate=True, alpha=0.75, color=c_neg, label="Spread < 0")

ax2.plot(x, spread, color="#333333", linewidth=1.5, alpha=0.9)

ax2.set_ylabel("Hard Tech - Overall")
ax2.set_xlabel("Time")
ax2.grid(True, which="major", axis="both", alpha=0.20)
ax2.legend(loc="upper left", frameon=False)

# -----------------------------
# 5) 横轴：按“半天粒度”展示
# -----------------------------
# major tick：每个工作日
ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))

# minor tick：每12小时，用于增强“半天精度”感
ax2.xaxis.set_minor_locator(mdates.HourLocator(byhour=[12]))

# 主次网格
ax2.grid(True, which="minor", axis="x", alpha=0.08)
ax1.grid(True, which="minor", axis="x", alpha=0.08)

plt.setp(ax1.get_xticklabels(), visible=False)

# -----------------------------
# 6) 边框和留白优化
# -----------------------------
for ax in [ax1, ax2]:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

fig.suptitle(
    "Market Volatility Monitor: Hard Tech vs Overall",
    fontsize=20,
    weight="bold",
    y=0.98
)

fig.text(
    0.01, 0.01,
    "Source: RQData | Frequency: 30min | Spread = Hard Tech VIX - Overall VIX",
    fontsize=10,
    color="#555555"
)

plt.tight_layout(rect=[0, 0.02, 1, 0.96])

# -----------------------------
# 7) 保存
# -----------------------------
png_path = os.path.join(OUT_DIR, "roadshow_hardtech_overall_20240915_20241115.png")
svg_path = os.path.join(OUT_DIR, "roadshow_hardtech_overall_20240915_20241115.svg")
pdf_path = os.path.join(OUT_DIR, "roadshow_hardtech_overall_20240915_20241115.pdf")

plt.savefig(png_path, bbox_inches="tight")
plt.savefig(svg_path, bbox_inches="tight")
plt.savefig(pdf_path, bbox_inches="tight")
plt.close()

print("Saved:")
print(png_path)
print(svg_path)
print(pdf_path)