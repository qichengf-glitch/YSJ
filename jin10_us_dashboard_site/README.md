> **YSJ integration note:** this release intentionally includes the uploaded `data/us_dashboard.db` snapshot, while `.env` and the non-portable macOS `.venv` are excluded. For the integrated server, configure the root `.env` and use `../scripts/start_all.sh`.

# US Event Intelligence v6.6

金十美国市场事件 + Polymarket Prediction Market / Whale Radar 仪表盘。

本版本重点修复了 v6.5 的数据滞后、错误分页、成交量口径错误、长事务阻塞、旧快照无提示、浏览器缓存与前端时间显示问题。

## 更新节奏

| 数据 | 默认频率 | 说明 |
|---|---:|---|
| 金十增量日志 | 1 分钟 | 启动后约 2 秒首次执行，并循环追赶遗漏日志 |
| 金十完整窗口 | 180 分钟 | 启动后约 8 秒首次执行；用于纠偏和补全 |
| Polymarket 当前行情 | 2 分钟 | 启动立即执行；只拉当前价格、24h/7d 成交量和市场状态，快速提交 |
| Polymarket 7 日价格历史 | 30 分钟 | 与当前行情分开，避免历史接口拖慢实时行情 |
| Whale 当前持仓与成交回补 | 10 分钟 | 当前持仓先独立提交；单钱包失败时安全沿用该钱包上一快照，其他钱包照常更新 |
| 浏览器读取本地 API | 30 秒 | 禁用缓存；页面重新可见时立即刷新 |

## 启动

干净交付包不包含 `.env` 或旧的 SQLite 数据库，避免泄露密钥和把 2026-07-09 的陈旧快照误当成当前数据。

全新启动：

```bash
cd jin10_us_dashboard_site
cp .env.example .env
# 编辑 .env，填入 JIN10_SECRET_KEY
python -m pip install -r requirements.txt
./run.sh
```

从 v6.5 升级并保留历史：先把旧版 `.env` 和 `data/us_dashboard.db` 复制进新目录，再运行 `./run.sh`。启动时会自动完成 schema migration；不要复制旧代码文件。

默认地址：`http://127.0.0.1:8000`

生产运行默认不启用 `--reload`。开发时才使用：

```bash
DEV_RELOAD=true ./run.sh
```

## 首次检查

启动后查看：

- `/api/health`：服务版本、scheduler 状态和各任务最近状态
- `/api/data-status`：Prediction Market / Whale 最新数据时间、延迟秒数和 stale 状态

页面显示“数据滞后”时，不要只刷新浏览器。优先查看 `/api/data-status` 中任务的 `status`、`last_error` 和时间戳。

## 手动同步

快速刷新当前 Prediction Market 行情，不拉历史：

```bash
curl -X POST 'http://127.0.0.1:8000/api/prediction-markets/sync?fetch_history=false'
```

单独补拉价格历史：

```bash
curl -X POST 'http://127.0.0.1:8000/api/prediction-markets/sync-history'
```

同步 Whale：

```bash
curl -X POST 'http://127.0.0.1:8000/api/prediction-markets/sync-whales'
```

同步金十默认窗口与增量日志：

```bash
curl -X POST 'http://127.0.0.1:8000/api/sync/default'
curl -X POST 'http://127.0.0.1:8000/api/sync/logs'
```

## 关键环境变量

参考 `.env.example`：

- `PREDICTION_QUOTE_INTERVAL_MINUTES=2`
- `PREDICTION_HISTORY_INTERVAL_MINUTES=30`
- `PREDICTION_WHALE_INTERVAL_MINUTES=10`
- `PREDICTION_STALE_AFTER_MINUTES=6`
- `WHALE_STALE_AFTER_MINUTES=20`
- `LOG_POLL_INTERVAL_MINUTES=1`
- `FULL_SYNC_INTERVAL_MINUTES=180`
- `DASHBOARD_TIMEZONE=Asia/Shanghai`

## 数据安全与容错

- SQLite 使用 WAL、30 秒 busy timeout 和显式 rollback。
- 上游返回空事件或解析后意外得到 0 个有效市场时，本次事务回滚，保留上一份成功快照。
- 当前行情、历史价格和 Whale 同步互相独立；一个任务失败不会阻断其他任务。
- Whale 使用钱包集合哈希校验安全 carry-forward，避免单个钱包 API 失败被误判为清仓，也避免冻结所有其他钱包。
- API 和前端静态入口返回 `no-store`，避免浏览器继续展示缓存响应。
- `.env` 包含密钥，不应提交或发送；本交付压缩包不包含 `.env`。

## 测试

```bash
PYTHONPATH=. python -m unittest discover -s tests -v
node --check app/static/app.js
python -m compileall -q app
```

详细问题、修复和验证见 `AUDIT_FIXES_v6_6.md`。
