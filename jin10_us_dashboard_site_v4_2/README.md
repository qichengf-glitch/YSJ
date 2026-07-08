# US Event Intelligence v4 — Prediction Markets

美股事件驱动 Dashboard v4。

本版在 v3.2 的金十美股日历基础上，新增 `Prediction Markets` 页面：

- 直接从 Polymarket Gamma API 拉取 active/open events
- 直接从 Polymarket CLOB API 拉取 7 日 probability history
- 不再生成 Excel
- 后端内部完成分类、过滤、信号打分、资产影响映射
- 前端展示宏观事件赔率、7 日变化、成交量、流动性、交易观察信号

顶部导航：

```text
Dashboard | Earnings | Updates | Holidays | Prediction Markets
```

## 交易主线分类

前台只保留三条交易员更容易使用的主线：

```text
全部
利率美元
地缘商品
增长风险
```

后台仍读取 Polymarket tags，但不会把 Fed / Inflation / Recession / War / Peace / IPO 等小标签全部暴露到前台。

## Prediction Markets 页面包含

```text
Macro Signal Board      — 三条主线的市场数量、成交额、平均 7日波动
概率上升 / 概率下降       — 过去 7 日概率变化最大
成交额最高                — 市场关注度最高
大成交重定价与观察信号     — 大成交、反转、拥挤共识
宏观相关市场表             — 主线、事件、概率、7D变化、成交量、影响资产
详情抽屉                  — 7日概率走势图、Bid/Ask、资产影响解释、Raw JSON
```

## 运行

```bash
cd jin10_us_dashboard_site_v4
python -m pip install -r requirements.txt
cp .env.example .env
```

填入金十 key：

```bash
JIN10_SECRET_KEY=你的金十secret-key
```

启动：

```bash
bash run.sh
```

浏览器打开：

```text
http://127.0.0.1:8000
```

## 同步数据

金十美股日历：

```bash
curl -X POST http://127.0.0.1:8000/api/sync/default
curl -X POST http://127.0.0.1:8000/api/sync/logs
```

Polymarket：

```bash
curl -X POST 'http://127.0.0.1:8000/api/prediction-markets/sync?min_prob=0.10&min_volume=10000&max_pages=15&fetch_history=true'
```

网页里也可以直接点 `同步 Polymarket`。

## 新增 API

```text
POST /api/prediction-markets/sync
GET  /api/prediction-markets/overview
GET  /api/prediction-markets/markets?bucket=all|rates_usd|geo_commodities|growth_risk
GET  /api/prediction-markets/market/{condition_id}
GET  /api/prediction-markets/history/{condition_id}
```

## 数据库新增表

```text
pm_events
pm_markets
pm_price_history
```

## 注意

- Prediction Markets 的信号不是直接买卖建议，只用于识别宏观事件预期是否发生大成交重定价。
- Polymarket 价格是事件 probability，不是黄金、原油、美债收益率或股指价格。
- IPO / 个股类低宏观相关市场默认过滤，不进入老板主视图。
- 7 日历史曲线在后端按小时 bucket 重新采样，避免 Excel 中同一分钟多行的问题。


## v4.2
- Prediction Markets 卡片不再重复显示 question/event_title。
- event_title 仅在与 question 明显不同、能提供额外上下文时显示。
- Top Movers、Volume Leaders、表格和详情抽屉均应用该去重规则。
