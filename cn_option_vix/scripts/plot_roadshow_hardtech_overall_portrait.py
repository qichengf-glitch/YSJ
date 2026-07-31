import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = "/Users/wonderfulren/Desktop/coding/quant/cn_option_vix"
CSV_PATH = os.path.join(ROOT, "outputs", "vix_30m_2y.csv")
OUT_DIR = os.path.join(ROOT, "outputs", "roadshow_custom")
os.makedirs(OUT_DIR, exist_ok=True)

START = "2026-02-14"
END   = "2026-07-13"

# 这个参数控制日期标签密度
# 如果你想每一天都显示，改成 1
# 如果觉得太密，可以改成 2 或 3
TICK_EVERY_N_DAYS = 3

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
df["date_str"] = df[time_col].dt.strftime("%Y-%m-%d")
df["time_only"] = df[time_col].dt.strftime("%H:%M")

# -----------------------------
# 2) 用等间距交易时点作横轴
# -----------------------------
df = df.reset_index(drop=True)
df["x"] = np.arange(len(df))

day_first_rows = df.groupby("date_only").head(1).copy()
day_starts = day_first_rows["x"].tolist()
day_labels_all = day_first_rows["date_str"].tolist()

# 稀疏显示日期标签
tick_positions = day_starts[::TICK_EVERY_N_DAYS]
tick_labels = day_labels_all[::TICK_EVERY_N_DAYS]

# 每天分隔线
all_day_starts = day_starts

# 午间分隔线（如果一天8个点，大致在第4个点后）
lunch_break_positions = []
for d, sub in df.groupby("date_only"):
    sub = sub.reset_index()
    if len(sub) >= 5:
        lunch_break_positions.append(sub.loc[3, "index"] + 0.5)

# -----------------------------
# 3) 样式
# -----------------------------
plt.rcParams["figure.dpi"] = 160
plt.rcParams["savefig.dpi"] = 320
plt.rcParams["font.size"] = 11
plt.rcParams["axes.titlesize"] = 15
plt.rcParams["axes.labelsize"] = 12
plt.rcParams["legend.fontsize"] = 11

# 竖版比例
fig = plt.figure(figsize=(10, 13))
gs = fig.add_gridspec(
    nrows=2,
    ncols=1,
    height_ratios=[3.0, 1.8],
    hspace=0.10
)

ax1 = fig.add_subplot(gs[0, 0])
ax2 = fig.add_subplot(gs[1, 0], sharex=ax1)

x = df["x"].values
overall = df["overall"].values
hard = df["hard_tech"].values
spread = df["spread"].values

# 配色
c_overall = "#2F3B52"   # 深灰蓝
c_hard    = "#1F77B4"   # 专业蓝
c_fill    = "#AFC7E8"   # 两线之间填充
c_pos     = "#5E9C76"   # spread > 0
c_neg     = "#D97A7A"   # spread < 0

# -----------------------------
# 4) 上图：主VIX
# -----------------------------
ax1.plot(x, overall, linewidth=2.2, color=c_overall, label="Overall VIX")
ax1.plot(x, hard, linewidth=2.4, color=c_hard, label="Hard Tech VIX")
ax1.fill_between(x, overall, hard, color=c_fill, alpha=0.24)

# 最新值标注
ax1.scatter(x[-1], overall[-1], s=28, color=c_overall, zorder=5)
ax1.scatter(x[-1], hard[-1], s=28, color=c_hard, zorder=5)

ax1.annotate(
    f"{overall[-1]:.2f}",
    (x[-1], overall[-1]),
    xytext=(8, -4),
    textcoords="offset points",
    color=c_overall,
    fontsize=10,
    weight="bold"
)
ax1.annotate(
    f"{hard[-1]:.2f}",
    (x[-1], hard[-1]),
    xytext=(8, 8),
    textcoords="offset points",
    color=c_hard,
    fontsize=10,
    weight="bold"
)

ax1.set_title("Hard Tech vs Overall VIX", pad=12, weight="bold")
ax1.set_ylabel("VIX")
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
    0.995, 0.985, text_box,
    transform=ax1.transAxes,
    ha="right", va="top",
    fontsize=10,
    bbox=dict(
        boxstyle="round,pad=0.35",
        facecolor="white",
        edgecolor="#DDDDDD",
        alpha=0.95
    )
)

# -----------------------------
# 5) 下图：spread
# -----------------------------
ax2.axhline(0, color="#666666", linewidth=1.0)
ax2.fill_between(
    x, 0, spread,
    where=(spread >= 0),
    color=c_pos,
    alpha=0.78,
    interpolate=True,
    label="Spread > 0"
)
ax2.fill_between(
    x, 0, spread,
    where=(spread < 0),
    color=c_neg,
    alpha=0.78,
    interpolate=True,
    label="Spread < 0"
)
ax2.plot(x, spread, color="#3A3A3A", linewidth=1.4)

ax2.set_title("Hard Tech Premium over Overall", pad=10, weight="bold")
ax2.set_ylabel("Hard Tech - Overall")
ax2.set_xlabel("Date")
ax2.legend(loc="upper left", frameon=False)
ax2.grid(True, axis="y", alpha=0.18)
ax2.grid(False, axis="x")

# -----------------------------
# 6) 每天分隔线 + 午间分隔线
# -----------------------------
for pos in all_day_starts:
    ax1.axvline(pos - 0.5, color="#E8E8E8", linewidth=0.9, zorder=0)
    ax2.axvline(pos - 0.5, color="#E8E8E8", linewidth=0.9, zorder=0)

for pos in lunch_break_positions:
    ax1.axvline(pos, color="#F2F2F2", linewidth=0.8, linestyle="--", zorder=0)
    ax2.axvline(pos, color="#F2F2F2", linewidth=0.8, linestyle="--", zorder=0)

# -----------------------------
# 7) x轴日期标签
# -----------------------------
ax2.set_xticks(tick_positions)
ax2.set_xticklabels(tick_labels, rotation=90, ha="center")

# 上图不显示x轴标签
plt.setp(ax1.get_xticklabels(), visible=False)

# -----------------------------
# 8) 美化边框
# -----------------------------
for ax in [ax1, ax2]:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

fig.suptitle(
    "Market Volatility Monitor",
    fontsize=20,
    weight="bold",
    y=0.985
)

fig.text(
    0.01, 0.012,
    "Source: RQData | 30-min bars (equally spaced by trading interval) | Spread = Hard Tech VIX - Overall VIX",
    fontsize=10,
    color="#555555"
)

plt.tight_layout(rect=[0, 0.03, 1, 0.97])

png_path = os.path.join(OUT_DIR, "roadshow_hardtech_overall_portrait_20260214_20260713.png")
svg_path = os.path.join(OUT_DIR, "roadshow_hardtech_overall_portrait_20260214_20260713.svg")
pdf_path = os.path.join(OUT_DIR, "roadshow_hardtech_overall_portrait_20260214_20260713.pdf")

plt.savefig(png_path, bbox_inches="tight")
plt.savefig(svg_path, bbox_inches="tight")
plt.savefig(pdf_path, bbox_inches="tight")
plt.close()

print("Saved:")
print(png_path)
print(svg_path)
print(pdf_path)