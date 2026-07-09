# Jin10 US Dashboard v6.5

核心修复：手动/自动多次同步 whales 后，事件详情里的 10 日 YES/NO 小图不会退化成 `1d` 或坏图。

## 本版修复的问题

v6.4 第一次同步时会用 `/trades` 回补 10 日曲线；但第二次点击“同步 Whales”后，系统检测到已有两次本地 `/positions` snapshot，就错误切换到“本地快照模式”。因为这两次快照都发生在同一天，前 9 天没有本地日期点，所以曲线退化成只有当天一格。

v6.5 改为：

- 10 日曲线始终先用近 10 日 `/trades` 建底图。
- 每天的本地 `/positions` snapshot 只作为覆盖点。
- 同一天多次同步只保留当天最新一次 snapshot，不会累加、不再覆盖掉前 9 天 trade-backfill 曲线。
- 今天最后一个点仍然强制等于 `/positions.currentValue`。
- 持仓为 0 的日期显示 0，不计入持有天数。

## 数据原则

- 当前持仓金额、方向、size、PnL：只以 `data-api.polymarket.com/positions` 的当前 snapshot 为准。
- 10 日小图：用 `/trades` 回补历史形状，然后用本地 `/positions` 按日期覆盖真实观测点。
- 后续网站每运行一天，都会多一个本地真实 snapshot 日期；多日后曲线会越来越接近完全由本地 `/positions` 组成。
- 如果近 10 日没有交易但当前仍有仓位，显示为 `≥10d`，表示窗口开始前已经持有。

## 自动同步

启动后自动每 10 分钟执行：

1. Polymarket markets/events/price history sync
2. tracked wallets positions snapshot sync
3. tracked wallets 10D trades backfill

`.env` 配置：

```bash
PREDICTION_SYNC_INTERVAL_MINUTES=10
PREDICTION_SYNC_MAX_PAGES=15
PREDICTION_SYNC_MIN_PROB=0.10
PREDICTION_SYNC_MIN_VOLUME=10000
```

## 运行

```bash
python -m pip install -r requirements.txt
cp .env.example .env
bash run.sh
```

手动强刷：

```bash
curl -X POST 'http://127.0.0.1:8000/api/prediction-markets/sync?min_prob=0.10&min_volume=10000&max_pages=15&fetch_history=true'
curl -X POST 'http://127.0.0.1:8000/api/prediction-markets/sync-whales'
```

## 不建议删库

不要因为这次修复删 `data/us_dashboard.db`。已有的 `pm_whale_trades` 和 `pm_whale_positions` 会被新逻辑重新读取并正确组合。
