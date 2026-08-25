"""
每日四板块HTML汇总

读取当天四个数据源，各调一次Claude生成结构化小结，输出HTML。

定时跑：22:10（在A股日报15:10和商品日报22:00之后）
  10 22 * * 1-5 cd /你的项目路径 && /你的venv/bin/python generate_daily_summary.py

数据来源：
  A股   → jin10_gate_a_digest.jsonl      关卡A行情复盘新闻
  美股   → jin10_us_analyst_digest.jsonl  关卡F分析师评级变动
  外汇   → forex_digest.jsonl             全部外汇新闻（重点政策类）
  商品   → jin10_commodity_scored.jsonl   有方向性新闻（0-3/7-10分）
"""

import json, re, os
from datetime import date, datetime
from pathlib import Path
from anthropic import Anthropic

TODAY      = date.today().strftime("%Y-%m-%d")
PACKAGE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("DAILY_SUMMARY_DATA_DIR", PACKAGE_DIR / "data"))
OUTPUT_DIR = DATA_DIR / "summaries"
MODEL      = os.getenv("DAILY_SUMMARY_CLAUDE_MODEL", "claude-sonnet-4-6")

client = Anthropic() if os.getenv("ANTHROPIC_API_KEY") else None

# ============================================================
# 读取今日数据
# ============================================================

def load_today(filepath, filter_fn=None, target_date=None):
    target_date = target_date or date.today().strftime("%Y-%m-%d")
    path = DATA_DIR / filepath
    records = []
    if not path.exists():
        return records
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
                if str(r.get("time", "")).startswith(target_date):
                    if filter_fn is None or filter_fn(r):
                        records.append(r)
            except Exception:
                pass
    # 去重
    seen, out = set(), []
    for r in records:
        k = str(r.get("id", r.get("content", "")))
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def is_directional(r):
    s = r.get("claude_score")
    return s is not None and (s <= 3 or s >= 7)


# ============================================================
# 各板块 Claude prompt
# ============================================================

PROMPTS = {

"a_share": """你是A股市场分析师。以下是今天的A股行情复盘新闻（关卡A类，描述已发生的价格/指数走势）。
整理成结构化JSON（不要其他文字）：
{
  "overall": "bullish|bearish|neutral",
  "summary": "一句话总结今日A股基调（15字内）",
  "indices": [{"name":"上证指数","change":"-1.00%","emoji":"▼"}],
  "sectors": {"strong":["煤炭","通信"],"weak":["电新","医药"]},
  "key_events": ["重点事件1，含潜在影响","事件2","事件3"],
  "strategy": ["大盘判断","看好板块","风险提示"]
}
emoji：涨▲，跌▼。找不到数字不要捏造。strategy写2-3条专业展望。""",

"us": """你是美股分析师。以下是今天的美股分析师评级变动记录。
整理成结构化JSON（不要其他文字）：
{
  "summary": "一句话总结今日评级动向（15字内）",
  "upgrades": [{"ticker":"NVDA","firm":"高盛","from":"240","to":"300","change":"+25%","note":"AI需求"}],
  "downgrades": [{"ticker":"AAPL","firm":"美银","from":"220","to":"195","change":"-11%","note":"需求放缓"}],
  "key_points": ["评级动向要点"]
}
upgrades=上调，downgrades=下调。找不到数据留空数组。""",

"forex": """你是外汇市场分析师。以下是今天的外汇新闻，重点关注政策类。
整理成结构化JSON（不要其他文字）：
{
  "overall": "dollar_strong|dollar_weak|mixed",
  "summary": "一句话总结今日外汇基调（15字内）",
  "policy_news": [
    {"institution":"美联储","speaker":"鲍威尔","signal":"hawkish|dovish|neutral","content":"关键表态"}
  ],
  "fx_moves": [{"name":"美元指数","change":"+0.35%","emoji":"▲"}],
  "key_points": ["其他重要事件"]
}
policy_news是重点（央行/利率决议/官员表态）。signal：鹰派hawkish，鸽派dovish，中性neutral。
emoji：美元走强▲，美元走弱/其他货币走强▼。找不到数字不要捏造。""",

"commodity": """你是大宗商品分析师。以下是今天有方向性的商品新闻（分数≤3或≥7），重点关注两个维度。
整理成结构化JSON（不要其他文字）：
{
  "overall": "bullish|bearish|mixed",
  "summary": "一句话总结今日商品市场基调（15字内）",
  "sentiment_signals": [
    {"commodity":"黄金","score":8,"direction":"up","event":"高盛上调目标价，地缘风险溢价升温"}
  ],
  "supply_demand_signals": [
    {"commodity":"WTI原油","score":3,"direction":"down","event":"EIA库存超预期增加420万桶"}
  ],
  "key_points": ["综合要点"]
}
sentiment_signals：地缘/机构预测/制裁/持仓变化类（舆情情绪）。
supply_demand_signals：库存/产量/进出口数据类（存量变化）。
各最多4条，按分数离5越远越优先。""",
}


def get_summary(channel, records):
    if not records:
        return None
    if client is None:
        print("  [Claude跳过] 缺少 ANTHROPIC_API_KEY")
        return None
    lines = []
    for r in records[:50]:
        t = str(r.get("time", ""))[:16]
        content = str(r.get("content", ""))[:200]
        score = r.get("claude_score")
        comm_type = r.get("cat5_commodity_type", "")
        extra = f" [分数:{score}]" if score is not None else ""
        if comm_type: extra += f" [{comm_type}]"
        lines.append(f"[{t}]{extra} {content}")

    try:
        msg = client.messages.create(
            model=MODEL, max_tokens=900,
            system=PROMPTS[channel],
            messages=[{"role": "user", "content":
                f"今日新闻（共{len(records)}条）：\n\n" + "\n".join(lines)}],
        )
        raw = re.sub(r'^```json\s*|\s*```$', '', msg.content[0].text.strip())
        return json.loads(raw)
    except Exception as e:
        print(f"  [Claude失败-{channel}] {e}")
        return None


# ============================================================
# HTML 渲染
# ============================================================

CHANNEL_META = {
    "a_share":   {"title": "A股",  "icon": "🇨🇳", "color": "#e74c3c", "sub": "关卡A行情复盘"},
    "us":        {"title": "美股",  "icon": "🇺🇸", "color": "#27ae60", "sub": "分析师评级变动"},
    "forex":     {"title": "外汇",  "icon": "💱",  "color": "#2980b9", "sub": "政策类新闻"},
    "commodity": {"title": "商品",  "icon": "🛢️",  "color": "#d35400", "sub": "舆情+供需信号"},
}

OVERALL_MAP = {
    "bullish":       ("▲ 偏多",  "#e74c3c"),
    "bearish":       ("▼ 偏空",  "#27ae60"),
    "neutral":       ("- 中性",  "#888"),
    "mixed":         ("~ 分化",  "#f39c12"),
    "dollar_strong": ("▲ 美元强", "#e74c3c"),
    "dollar_weak":   ("▼ 美元弱", "#27ae60"),
}

SIGNAL_ICON = {"hawkish": "[鹰]", "dovish": "[鸽]", "neutral": "[中]"}


def render_panel(channel, digest, count):
    m = CHANNEL_META[channel]
    color, title, icon, sub = m["color"], m["title"], m["icon"], m["sub"]

    if digest is None:
        return f'''<div class="panel" style="border-top:3px solid {color}">
          <div class="ph"><span class="pi">{icon}</span><span class="pt">{title}</span>
          <span class="ps">{sub}</span><span class="pc">今日{count}条</span></div>
          <div class="nodata">今日暂无数据或整理失败</div></div>'''

    ol, oc = OVERALL_MAP.get(digest.get("overall",""), ("⚪","#888"))
    summary = digest.get("summary", "")
    rows = ""

    # 指数/汇率行情
    for key in ["indices", "fx_moves"]:
        moves = digest.get(key, [])
        if moves:
            bits = " &nbsp; ".join(
                f'{x.get("emoji","")} {x.get("name","")} <b>{x.get("change","")}</b>'
                for x in moves)
            rows += f'<div class="row"><span class="rl">行情</span><span>{bits}</span></div>'

    # 板块强弱（A股）
    sectors = digest.get("sectors", {})
    if sectors.get("strong") or sectors.get("weak"):
        s = ""
        if sectors.get("strong"):
            s += f'<span style="color:#e74c3c">▲ {"，".join(sectors["strong"])}</span>'
        if sectors.get("weak"):
            s += f' &nbsp; <span style="color:#27ae60">▼ {"，".join(sectors["weak"])}</span>'
        rows += f'<div class="row"><span class="rl">板块</span><span>{s}</span></div>'

    # 外汇政策类新闻（重点）
    policy = digest.get("policy_news", [])
    if policy:
        bits = "<br>".join(
            f'{SIGNAL_ICON.get(p.get("signal",""),"·")} <b>{p.get("institution","")}</b>'
            f'{"·"+p.get("speaker","") if p.get("speaker") else ""}: {p.get("content","")}'
            for p in policy[:4])
        rows += f'<div class="row"><span class="rl" style="background:#2980b9">政策</span><span>{bits}</span></div>'

    # 商品舆情信号
    for sig in digest.get("sentiment_signals", []):
        arrow = "▲" if sig.get("direction") == "up" else "▼"
        rows += (f'<div class="row"><span class="rl" style="background:#e67e22">舆情</span>'
                 f'<span>{arrow} <b>{sig.get("commodity","")}</b>'
                 f' [{sig.get("score","")}分] {sig.get("event","")}</span></div>')

    # 商品供需信号
    for sig in digest.get("supply_demand_signals", []):
        arrow = "▲" if sig.get("direction") == "up" else "▼"
        rows += (f'<div class="row"><span class="rl" style="background:{color}">供需</span>'
                 f'<span>{arrow} <b>{sig.get("commodity","")}</b>'
                 f' [{sig.get("score","")}分] {sig.get("event","")}</span></div>')

    # 美股评级
    for label, field, lcolor in [("上调","upgrades","#e74c3c"),("下调","downgrades","#27ae60")]:
        items = digest.get(field, [])
        if items:
            bits = " &nbsp; ".join(
                f'<b>{x.get("ticker","")}</b> {x.get("firm","")} '
                f'{x.get("from","")}→{x.get("to","")} '
                f'<span style="color:{lcolor}">({x.get("change","")})</span>'
                for x in items)
            rows += f'<div class="row"><span class="rl" style="background:{lcolor}">{label}</span><span>{bits}</span></div>'

    # 重点事件/要点
    pts = digest.get("key_events", []) or digest.get("key_points", [])
    if pts:
        rows += (f'<div class="row"><span class="rl">事件</span>'
                 f'<span>{"<br>".join(f"{i+1}. {p}" for i,p in enumerate(pts[:4]))}</span></div>')

    # A股策略
    strategy = digest.get("strategy", [])
    if strategy:
        rows += (f'<div class="row"><span class="rl" style="background:#8e44ad">策略</span>'
                 f'<span>{"<br>".join(f"{i+1}. {s}" for i,s in enumerate(strategy[:3]))}</span></div>')

    return f'''<div class="panel" style="border-top:3px solid {color}">
      <div class="ph">
        <span class="pi">{icon}</span>
        <span class="pt">{title}</span>
        <span class="ps">{sub}</span>
        <span class="ob" style="background:{oc}20;color:{oc}">{ol}</span>
        <span class="pc">今日{count}条</span>
      </div>
      <div class="sm">{summary}</div>
      <div class="rows">{rows}</div>
    </div>'''


def generate_html(summaries, counts, date_str):
    panels = "".join(
        render_panel(ch, summaries.get(ch), counts.get(ch, 0))
        for ch in ["a_share", "us", "forex", "commodity"]
    )
    gen_time = datetime.now().strftime("%H:%M")
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>每日市场日报 {date_str}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{height:100%}}
body{{font-family:-apple-system,"Microsoft YaHei",sans-serif;background:#f0f2f5;
     color:#222;font-size:14px;display:flex;flex-direction:column;
     padding:12px;gap:10px;min-height:100vh}}
.header{{flex-shrink:0}}
h1{{font-size:17px;font-weight:700;margin-bottom:2px}}
.sub{{font-size:11px;color:#aaa}}
.grid{{flex:1;display:grid;
      grid-template-columns:1fr 1fr;
      grid-template-rows:1fr 1fr;
      gap:10px;min-height:0}}
.panel{{background:#fff;border-radius:12px;padding:14px 16px;
       box-shadow:0 1px 6px rgba(0,0,0,.08);
       display:flex;flex-direction:column;overflow:hidden;min-height:0}}
.ph{{display:flex;align-items:center;gap:7px;margin-bottom:8px;flex-wrap:wrap;flex-shrink:0}}
.pi{{font-size:17px}}
.pt{{font-size:15px;font-weight:700}}
.ps{{font-size:10px;color:#aaa;border:1px solid #eee;padding:1px 5px;border-radius:4px}}
.ob{{padding:2px 9px;border-radius:20px;font-size:11px;font-weight:600}}
.pc{{margin-left:auto;font-size:10px;color:#ccc;background:#f5f5f5;
    padding:2px 6px;border-radius:10px}}
.sm{{font-size:12px;color:#555;background:#f9f9f9;padding:6px 10px;
    border-radius:6px;margin-bottom:7px;line-height:1.55;flex-shrink:0}}
.rows{{flex:1;display:flex;flex-direction:column;overflow-y:auto;min-height:0}}
.row{{display:flex;gap:8px;font-size:12px;line-height:1.6;
     padding:5px 0;border-bottom:1px solid #f5f5f5;flex-shrink:0}}
.row:last-child{{border-bottom:none}}
.rl{{flex-shrink:0;font-size:9px;font-weight:700;color:#fff;background:#bbb;
    border-radius:3px;padding:1px 5px;height:17px;margin-top:2px;
    align-self:flex-start;white-space:nowrap;display:flex;align-items:center}}
.nodata{{color:#bbb;text-align:center;padding:20px;font-size:13px}}
.footer{{flex-shrink:0;text-align:center;color:#ccc;font-size:10px;padding-top:4px}}
</style>
</head>
<body>
<div class="header">
  <h1>每日市场日报 &nbsp;<span style="font-size:13px;font-weight:400;color:#aaa">{date_str} &nbsp;·&nbsp; 生成于 {gen_time}</span></h1>
</div>
<div class="grid">{panels}</div>
<div class="footer">A股：关卡A行情复盘 &nbsp;|&nbsp; 美股：分析师评级 &nbsp;|&nbsp; 外汇：政策类新闻 &nbsp;|&nbsp; 商品：舆情+供需</div>
</body>
</html>'''


# ============================================================
# 主流程
# ============================================================

def build_summary_payload(target_date=None):
    target_date = target_date or date.today().strftime("%Y-%m-%d")

    sources = {
        "a_share":   ("jin10_gate_a_digest.jsonl",     None),
        "us":        ("jin10_us_analyst_digest.jsonl",  None),
        "forex":     ("forex_digest.jsonl",             None),
        "commodity": ("jin10_commodity_scored.jsonl",   is_directional),
    }

    summaries, counts = {}, {}
    for ch, (filepath, fn) in sources.items():
        records = load_today(filepath, fn, target_date=target_date)
        counts[ch] = len(records)
        meta = CHANNEL_META[ch]
        print(f"  {meta['title']}: {len(records)} 条", end="")
        if records:
            print(" → Claude...", end="", flush=True)
            summaries[ch] = get_summary(ch, records)
            print(" ✓" if summaries[ch] else " ✗")
        else:
            print(" (无数据)")
            summaries[ch] = None

    return {
        "status": "ok",
        "date": target_date,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summaries": summaries,
        "counts": counts,
        "source_files": {
            "a_share": str(DATA_DIR / "jin10_gate_a_digest.jsonl"),
            "us": str(DATA_DIR / "jin10_us_analyst_digest.jsonl"),
            "forex": str(DATA_DIR / "forex_digest.jsonl"),
            "commodity": str(DATA_DIR / "jin10_commodity_scored.jsonl"),
        },
    }


def generate(target_date=None):
    target_date = target_date or date.today().strftime("%Y-%m-%d")
    print(f"生成 {target_date} 日报...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = build_summary_payload(target_date)
    html = generate_html(payload["summaries"], payload["counts"], target_date)

    # 固定文件名（每天覆盖）+ 按日期归档
    latest  = OUTPUT_DIR / "daily_summary_latest.html"
    archive = OUTPUT_DIR / f"daily_summary_{target_date}.html"
    for path in [latest, archive]:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

    latest_json = OUTPUT_DIR / "daily_summary_latest.json"
    archive_json = OUTPUT_DIR / f"daily_summary_{target_date}.json"
    for path in [latest_json, archive_json]:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 输出：{latest}")
    print(f"   归档：{archive}")
    return payload


def main():
    generate()


if __name__ == "__main__":
    main()
