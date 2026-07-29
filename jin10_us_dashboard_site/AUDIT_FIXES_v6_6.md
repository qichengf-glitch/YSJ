# Market Radar + Prediction Market 数据链路审计与修复

版本：v6.6  
审计日期：2026-07-17

## 1. 结论

老板看到的不是普通的几分钟延迟，而是数据同步在 2026-07-09 后停止或未成功落库。

压缩包内数据库审计结果：

| 数据集 | 最新时间 | 审计时状态 |
|---|---|---|
| Prediction Market 当前市场 | 2026-07-09T08:23:34Z | 约 8 天滞后 |
| Prediction Market 价格历史 | 2026-07-09T08:00:00Z | 约 8 天滞后 |
| Prediction Market 成交量历史 | 2026-07-09 | 只有单日快照 |
| Whale positions | 2026-07-09T13:07:43Z | 约 8 天滞后 |
| Whale trades | 2026-07-09T12:53:16Z | 约 8 天滞后 |
| 金十 current 数据 | 2026-07-09T13:07:29Z | 约 8 天滞后 |
| 金十日志 poll state | 2026-07-09T13:07:40Z | 约 8 天滞后 |

因此，仅刷新网页或提高前端刷新频率无法解决；旧版前端只是不断读取已停止更新的 SQLite。

## 2. 已确认的严重数据错误

### P0：普通 `/events` 使用了错误分页方式

旧代码调用 Gamma 普通 `/events`，却把事件 ID 当作 `next_cursor` 继续请求。普通 endpoint 使用 `limit` + `offset`；keyset endpoint 才使用 `next_cursor` / `after_cursor`。旧逻辑可能重复第一页、漏掉大量活跃事件，同时没有报错。

修复：

- `/events` 改为 `offset = page_no * limit`。
- 按 `volume_24hr` 降序拉取，使雷达优先覆盖当前活跃市场，而不是历史累计大市场。
- 检测重复/无新增 ID 页面，发生时直接失败并保留旧快照，而不是静默写入部分数据。
- 达到配置页数上限时标记 `snapshot_complete=false`；仍更新已看到的高活跃市场，但不会错误停用页数上限之外的有效市场。

官方参考：

- https://docs.polymarket.com/developers/gamma-markets-api/fetch-markets-guide
- https://docs.polymarket.com/api-reference/events/list-events-keyset-pagination

### P0：把累计总成交量当成 7 日成交量

旧代码将 `volume` / `volumeNum`（累计成交量）写成 `volume_7d`，并在缺少日历史时用累计成交量除以 7 作为日均基线。这会导致：

- 成交异动比率系统性失真；
- 老市场天然看起来比新市场活跃；
- “7D volume” 标签与实际口径不一致；
- 雷达排序不能反映当天资金活动。

修复：

- 优先使用官方 `volume1wk`；若拆分字段存在则使用 `volume1wkClob + volume1wkAmm`。
- `volume24hr` 单独保存。
- 累计 `volume` 仅保存为 `volume_total`，不再参与 7 日口径。
- 有本地日快照时，基线按窗口内真实日值并包含安静日 0；无足够历史时，用 `volume1wk / 7` 明确作为 fallback。
- 页面明确显示成交量来源。

官方 market schema：

- https://docs.polymarket.com/api-reference/markets/list-markets

### P0：假定 outcome/token 数组第 0 项永远是 YES

旧代码直接读取 index 0。若市场返回 `['No', 'Yes']`，会把 NO 概率、NO token 的历史价格错误显示为 YES。

修复：解析 `outcomes`，定位字符串 `Yes` 的真实索引，再使用同一索引读取 `outcomePrices` 与 `clobTokenIds`。

### P0：行情、历史和 Whale 在一条长链中串行执行

旧版一次 Prediction 同步同时完成事件、市场、每个 token 的价格历史和 Whale；历史接口慢或某个钱包失败时：

- 当前行情迟迟不能 commit；
- 数据库读端持续看到旧快照；
- Whale 可能完全跳过；
- 前端无从判断是正在运行、失败还是 scheduler 根本未启动。

修复：拆分成独立任务：

1. 当前行情：2 分钟，短事务，先提交。
2. 价格历史：30 分钟，独立任务。
3. Whale：10 分钟，独立任务。
4. 金十日志：1 分钟，独立任务。
5. 金十完整窗口：180 分钟，独立纠偏。

### P0：同步失败不可见

旧版没有统一的 job health 表，也没有在页面暴露最近成功、最近失败和错误信息。即使 scheduler 停止，页面仍可正常打开并继续显示旧数据。

修复：

- 新增 `sync_job_status`。
- 新增 `/api/health` 和 `/api/data-status`。
- Prediction 与 Whale API 返回 `age_seconds` / `is_stale`。
- 页面显示明确的 stale/error 状态，而不是将旧时间戳当作正常数据。

## 3. 其他已修复的数据与实时性问题

### 3.1 数据库长事务与锁

旧版在 SQLite transaction 内执行大量 HTTP 请求，48 个钱包与历史接口完成前不提交。

修复：

- HTTP 请求移出长事务。
- 每个钱包 current positions 获取后使用短事务保存。
- SQLite 启用 WAL、`busy_timeout=30000`、显式 rollback。
- 网络/解析异常不会留下半提交状态。

### 3.2 空响应会清空有效快照

旧版先将所有记录标记 inactive；上游异常返回空列表或字段变化时，可能把页面清空。

修复：

- 上游 0 events 直接报错。
- 原来存在 live market，但本次解析后 0 eligible markets 时，事务整体 rollback。
- 保留最后一次有效快照并把任务标为 failed。

### 3.3 已关闭或消失市场长期保留

旧版只 upsert 新数据，没有可靠 active/closed 生命周期处理，旧市场会长期出现在雷达中。

修复：仅在一次完整成功快照事务中先降级旧记录，再激活本次实际看到的 active/open 市场。

### 3.4 bid/ask 缺失被伪装成 0

旧版缺失 bid/ask 时写 0，使未知价差看起来极小，影响流动性与信号判断。

修复：缺失保存为 `NULL`；只有 bid 和 ask 都存在时才计算 spread。

### 3.5 事件级 liquidity 覆盖市场级 liquidity

修复：优先使用 market `liquidityNum` / `liquidity`，仅在缺失时回退 event liquidity。

### 3.6 历史数据无限增长

修复：

- 价格历史保留 8 天。
- volume daily snapshots 保留 35 天。
- Whale positions/runs/trades 保留 35 天。

### 3.7 Whale 全量重复下载

旧版每次为每个钱包、每个市场重复下载完整 10 天交易。

修复：

- 新 wallet-market pair 拉 10 天。
- 已有 pair 仅拉 2 天重叠窗口去重补录。
- 请求使用服务端 `start` / `end` 限制，降低数据量与超时概率。

### 3.8 Whale 当前快照被历史补拉或单钱包失败阻断

旧版中，一个钱包 positions 请求失败就可能让整批新快照不可用；如果直接保存部分结果，又会把失败钱包误显示为清仓。

修复：

- positions 先形成可用快照，trades 回补随后执行。
- 某个钱包失败时，若上一份有效快照的钱包集合哈希与当前完全一致，则仅把该钱包上一份 positions 安全 carry-forward；其他成功钱包继续使用最新数据。
- carry-forward 行写入来源时间，run 标记为 `partial_carried`，不会伪装成全部成功。
- 钱包集合变化时禁止沿用旧数据，避免把已替换的钱包错误继承为新钱包。
- positions 全部成功但部分 trades 失败时，当前持仓仍可用，并显示 partial 状态。

### 3.9 Whale trade 写入错误被静默吞掉

旧版逐条保存交易时捕获所有异常后直接忽略，数据库字段变化、序列化错误或写锁问题可能造成缺失，但同步仍显示成功。

修复：无效时间/condition 仍安全跳过；真正的持久化异常会向上抛出，使该钱包交易回补标记为 partial/failed 并出现在 job error 中。

### 3.10 “24h top traders” 使用伪指标

旧版使用相邻 position snapshot 的价值差近似 24h 活跃度，价格波动会被误判成交易。

修复：榜单改用近 24h 实际 trades 的 turnover、net flow 与 trade count。

### 3.11 伪 win rate 误删钱包

旧版用当前未平仓头寸的 PnL 正负作为“胜率”，可能把人工精选钱包错误剔除。

修复：不再使用未实现 PnL 伪胜率淘汰 `Wallets.json` 中的 curated wallets；该指标仅作为显示信息。

### 3.12 金十日志 `data_id` 兼容与删除记录

部分日志可能只在嵌套 `data.id` 中提供记录 ID。旧版 `record_log()` 强制读取顶层 `data_id`，会在合法日志上抛错并中断后续增量同步；delete payload 缺少嵌套 id 时也可能无法留存。

修复：raw log 使用 `data_id`，缺失时回退 `data.id`；delete fallback 自动补入已解析的 ID。数据库 migration 只忽略“重复列”错误，不再吞掉其他真实 schema/disk 异常。

### 3.13 金十停机后只拉一页日志

旧版一次 poll 只处理一个 response，停机数日后若 API 分页/限量，会长期追不上。

修复：每轮最多连续追赶 20 页；每页成功后推进 cursor。下轮从断点继续。

### 3.14 Prediction 成交量快照按 UTC 错位切日

旧版将滚动 24h 成交量快照按 UTC 日期写入日表；在亚洲时区，早晨/夜间会落入错误日期，影响 10 日基线。

修复：Prediction volume snapshot 与清理窗口统一使用 `DASHBOARD_TIMEZONE` 的本地日期。

### 3.15 金十异常日志可卡住 cursor

上游若出现缺失或非法 `data_id` 的日志，旧逻辑会跳过该记录但不推进 cursor，导致每分钟重复遇到同一条异常日志。

修复：raw log 使用 `data_id=0` 留档，并推进到该 `log_id`；异常记录计入 `skipped_missing_data_id`，后续正常日志不会被阻断。

### 3.16 前端缓存与刷新误导

旧版每 60 秒调用本地 API，但：

- 不触发上游同步；
- 浏览器可能复用缓存；
- 多 endpoint 使用 `Promise.all`，任何一个失败会阻止整页更新；
- 重叠请求可能堆积。

修复：

- API 与静态入口添加 `no-store`。
- GET 增加 cache-busting query。
- 每 30 秒读取，页面恢复可见时立即读取。
- 使用 `Promise.allSettled`，单一模块失败不阻断其他模块。
- 增加 loading guard，避免重叠刷新。

### 3.17 UTC 时间被当成本地时间

旧版前端删除时间字符串的 `Z` 后再构造 Date，导致 UTC 被错误解释为本地时间，显示可额外偏差 8/9 小时。

修复：保留时区，使用浏览器标准 Date 转换；后端统一使用 dashboard timezone 处理本地日期边界。

### 3.18 前端运行时错误

`renderCompactSurprises()` 使用未定义变量 `mode`，可能中断后续渲染。

修复：使用固定安全上限 6。

### 3.19 production 使用 `--reload`

旧版启动脚本默认 `--reload`，文件变化会重启进程，scheduler 和运行中的同步任务也会被中断。

修复：生产默认关闭 reload；只有显式 `DEV_RELOAD=true` 才启用。

## 4. 验证结果

已完成：

- Python 全量 compile：通过。
- JavaScript `node --check`：通过。
- FastAPI `/`, `/api/health`, `/api/data-status` 冒烟测试：通过。
- 旧数据库 schema migration：通过。
- 14 项自动化测试：全部通过。

自动化测试覆盖：

1. 普通 events endpoint 使用 offset 分页，且不会发送 cursor 参数。
2. Gamma events 同时兼容数组响应和带 `events` / `has_more` 的 envelope 响应，并正确解析字符串布尔值。
3. 达到 events page cap 时标记不完整快照，且不批量停用未拉到的市场。
4. `['No','Yes']` 时正确选取 YES price/token。
5. 缺少明确 YES outcome 的记录拒绝落库，避免将 NO/其他 outcome 错标成 YES。
6. 使用真实 `volume1wk`，累计 volume 单独保存。
7. Prediction volume snapshot 按 dashboard 本地日期切日。
8. 空上游响应或解析后 0 个有效市场时保留最后有效快照。
9. Whale trades 使用服务端 start/end。
10. 不完整的 partial Whale run 不会覆盖旧版有效快照。
11. 单钱包失败时安全 carry-forward，其他钱包仍更新；钱包集合哈希落库。
12. Whale 日线按 dashboard 本地时区切日，不再按服务器/UTC 日期误分组。
13. 金十日志顶层缺少 `data_id` 时正确回退嵌套 `data.id`。
14. 金十日志完全缺少/非法 `data_id` 时仍留档并推进 cursor。

## 5. 部署后必须观察

当前交付环境不能代替你的正式网络、JIN10 key 和长期运行进程，因此部署后应立即检查：

1. `./run.sh` 启动后，`/api/health` 的 `scheduler_running` 为 true。
2. 2–3 分钟内 `/api/data-status` 的 Prediction `fetched_at` 更新到当前时间。
3. 10–12 分钟内 Whale `fetched_at` 更新。
4. 金十 `jin10_logs` 状态成功且 cursor 继续递增。
5. 任何 job failed 时查看 `last_error`，不要仅刷新页面。

## 6. 后续建议

若老板要求秒级而不是 2 分钟级行情，应将当前 Gamma polling 升级为 Polymarket WebSocket market channel。当前 v6.6 仍采用 HTTP polling，但已消除本地代码造成的多日停更、错误口径与长事务延迟。
