import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

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

for c in ["overall", "hard_tech"]:
    if c not in df.columns:
        raise ValueError(f"缺少列: {c}")

start_ts = pd.Timestamp(START)
end_ts = pd.Timestamp(END) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
df = df[(df[time_col] >= start_ts) & (df[time_col] <= end_ts)].copy()

if df.empty:
    raise ValueError("筛选后没有数据，请检查日期范围和 CSV 文件内容。")

df["spread"] = df["hard_tech"] - df["overall"]
df["date_only"] = df[time_col].dt.date
df["time_only"] = df[time_col].dt.strftime("%H:%M")

# -----------------------------
# 2) 用“交易时点索引”替代真实 datetime 作为横轴
# -----------------------------
df = df.reset_index(drop=True)
df["x"] = np.arange(len(df))

# 每天开始位置，用于放主刻度和画分隔线
day_starts = df.groupby("date_only").head(1).index.tolist()
day_labels = [pd.Timestamp(str(d)).strftime("%m-%d") for d in df.groupby("date_only").head(1)["date_only"]]

# 每天中间位置用于标记（可选）
day_mid = df.groupby("date_only")["x"].mean().tolist()

# 如果一天有 8 个30min点，午间大致分界在第4个点后
lunch_break_positions = []
for d, sub in df.groupby("date_only"):
    sub = sub.reset_index()
    if len(sub) >= 5:
        # 第4个点和第5个点之间的位置附近
        lunch_break_positions.append(sub.loc[3, "index"] + 0.5)

# -----------------------------
# 3) 样式
# -----------------------------
plt.rcParams["figure.dpi"] = 160
plt.rcParams["savefig.dpi"] = 320
plt.rcParams["font.size"] = 11
plt.rcParams["axes.titlesize"] = 16
plt.rcParams["axes.labelsize"] = 12
plt.rcParams["legend.fontsize"] = 11

fig = plt.figure(figsize=(16, 9))
gs = fig.add_gridspec(nrows=2, ncols=1, height_ratios=[3.2, 1.5], hspace=0.08)
ax1 = fig.add_subplot(gs[0, 0])
ax2 = fig.add_subplot(gs[1, 0], sharex=ax1)

x = df["x"].values
overall = df["overall"].values
hard = df["hard_tech"].values
spread = df["spread"].values

# 配色
c_overall = "#2F3B52"
c_hard    = "#1F77B4"
c_fill    = "#AFC7E8"
c_pos     = "#5E9C76"
c_neg     = "#D97A7A"

# -----------------------------
# 4) 上图：主线
# -----------------------------
ax1.plot(x, overall, linewidth=2.2, color=c_overall, label="Overall VIX")
ax1.plot(x, hard, linewidth=2.4, color=c_hard, label="Hard Tech VIX")
ax1.fill_between(x, overall, hard, color=c_fill, alpha=0.22)

# 最后值标注
ax1.scatter(x[-1], overall[-1], s=24, color=c_overall, zorder=5)
ax1.scatter(x[-1], hard[-1], s=24, color=c_hard, zorder=5)

ax1.annotate(f"{overall[-1]:.2f}", (x[-1], overall[-1]), xytext=(8, -4),
             textcoords="offset points", color=c_overall, fontsize=10, weight="bold")
ax1.annotate(f"{hard[-1]:.2f}", (x[-1], hard[-1]), xytext=(8, 8),
             textcoords="offset points", color=c_hard, fontsize=10, weight="bold")

ax1.set_ylabel("VIX")
ax1.set_title("Hard Tech vs Overall VIX (30-Min Bars)", pad=14, weight="bold")
ax1.legend(loc="upper left", frameon=False)
ax1.grid(True, axis="y", alpha=0.20)
ax1.grid(False, axis="x")

# 统计框
text_box = (
    f"Period: {START} to {END}\n"
    f"Avg Spread: {df['spread'].mean():.2f}\n"
    f"Max Spread: {df['spread'].max():.2f}\n"
    f"Min Spread: {df['spread'].min():.2f}"
)
ax1.text(
    0.995, 0.98, text_box,
    transform=ax1.transAxes,
    ha="right", va="top",
    fontsize=10,
    bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="#DDDDDD", alpha=0.95)
)

# -----------------------------
# 5) 下图：spread
# -----------------------------
ax2.axhline(0, color="#666666", linewidth=1.0)
ax2.fill_between(x, 0, spread, where=(spread >= 0), color=c_pos, alpha=0.75, interpolate=True, label="Spread > 0")
ax2.fill_between(x, 0, spread, where=(spread < 0), color=c_neg, alpha=0.75, interpolate=True, label="Spread < 0")
ax2.plot(x, spread, color="#3A3A3A", linewidth=1.4)

ax2.set_ylabel("Hard Tech - Overall")
ax2.set_xlabel("Trading Time")
ax2.legend(loc="upper left", frameon=False)
ax2.grid(True, axis="y", alpha=0.18)
ax2.grid(False, axis="x")

# -----------------------------
# 6) 每日分隔线 + 午间分隔线
# -----------------------------
for pos in day_starts:
    ax1.axvline(pos - 0.5, color="#E6E6E6", linewidth=1.0, zorder=0)
    ax2.axvline(pos - 0.5, color="#E6E6E6", linewidth=1.0, zorder=0)

for pos in lunch_break_positions:
    ax1.axvline(pos, color="#F0F0F0", linewidth=0.8, linestyle="--", zorder=0)
    ax2.axvline(pos, color="#F0F0F0", linewidth=0.8, linestyle="--", zorder=0)

# x轴只显示日期（每天一个标签）
ax2.set_xticks(day_starts)
ax2.set_xticklabels(day_labels, rotation=0)

# 不显示上图x轴标签
plt.setp(ax1.get_xticklabels(), visible=False)

# 美化边框
for ax in [ax1, ax2]:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

fig.suptitle(
    "Market Volatility Monitor: Hard Tech vs Overall",
    fontsize=20,
    weight="bold",
    y=0.97
)

fig.text(
    0.01, 0.01,
    "Source: RQData | 30-min bars (equally spaced by trading interval) | Spread = Hard Tech VIX - Overall VIX",
    fontsize=10,
    color="#555555"
)

plt.tight_layout(rect=[0, 0.02, 1, 0.95])

png_path = os.path.join(OUT_DIR, "roadshow_hardtech_overall_20240915_20241115_v2.png")
svg_path = os.path.join(OUT_DIR, "roadshow_hardtech_overall_20240915_20241115_v2.svg")
pdf_path = os.path.join(OUT_DIR, "roadshow_hardtech_overall_20240915_20241115_v2.pdf")

plt.savefig(png_path, bbox_inches="tight")
plt.savefig(svg_path, bbox_inches="tight")
plt.savefig(pdf_path, bbox_inches="tight")
plt.close()

print("Saved:")
print(png_path)
print(svg_path)
print(pdf_path)