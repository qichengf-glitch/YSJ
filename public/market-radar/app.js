const state = {
  view: 'dashboard',
  dashboard: null,
  earnings: [],
  updates: [],
  holidays: [],
  predictionOverview: null,
  predictionMarkets: [],
  query: '',
  earningsFilter: null,
  updateFilter: 'all',
  pmBucket: 'all',
  activeEventKey: null,
  language: 'en',
};

const $ = (id) => document.getElementById(id);
const API_PROXY_PREFIX = '/api/market-radar';
const I18N = {
  en: {
    brandTitle: 'Market Calendar Intelligence',
    brandSubtitle: 'US Event-Driven Dashboard',
    tabDashboard: 'Dashboard',
    tabEarnings: 'Earnings',
    tabUpdates: 'Updates',
    tabHolidays: 'Holidays',
    tabPrediction: 'Prediction Markets',
    searchPlaceholder: 'Search TSM / NVDA / revenue / after hours',
    syncData: 'Sync Data',
    thisWeek: 'This Week',
    waitingHeadline: 'Waiting for data sync',
    waitingParagraph: 'After syncing the US market calendar, this area will show event themes, earnings concentration, and pre-market/after-hours risk windows.',
    monitorMetrics: 'Market Monitor',
    liveIntelligence: 'Live Intelligence',
    latestUpdates: 'Latest Updates',
    viewAll: 'View All',
    today: 'Today',
    todayPreMarket: 'Today Pre-Market',
    tonight: 'Tonight',
    todayAfterHours: 'Today After-Hours',
    released: 'Released',
    concentration: 'Concentration',
    companyGroupsTitle: 'Company Groups & Event Concentration',
    themeGroups: 'Theme Groups',
    frequentCompanies: 'Frequent Companies',
    earnings: 'Earnings',
    earningsCalendar: 'Earnings Calendar',
    releasedFilter: 'Released',
    upcomingFilter: 'Upcoming',
    range7: '7D',
    range30: '30D',
    star4Plus: 'Star 4+',
    materialChanges: 'Material Changes',
    importantChanges: 'Important Changes',
    updatesNote: 'Includes valid events across all Star levels; delete records, empty entries, ordinary pending rows, and items older than 7 days are hidden.',
    all: 'All',
    dataRelease: 'Data Release',
    forecastRevision: 'Forecast / Revision',
    marketEvent: 'Market Event',
    regionUS: 'US',
    regionEurope: 'Europe',
    regionAsia: 'Asia',
    marketSchedule: 'Market Schedule',
    holidaysSchedule: 'Holidays & Trading Schedule',
    predictionMarkets: 'Prediction Markets',
    macroOddsRadar: 'Macro Event Odds Radar',
    predictionNote: 'Pulls event odds and 7-day probability changes directly from Polymarket Gamma/CLOB APIs. The main view keeps three trading themes: rates/USD, geopolitics/commodities, and growth risk.',
    ratesUsd: 'Rates / USD',
    geoCommodities: 'Geo / Commodities',
    growthRisk: 'Growth Risk',
    syncPolymarket: 'Sync Polymarket',
    watch7d: '7D Watch',
    themeMonitor: 'Theme Monitor',
    notSynced: 'Not synced yet',
    up7d: '7D Up',
    probUp: 'Probability Up',
    down7d: '7D Down',
    probDown: 'Probability Down',
    volume: 'Volume',
    volumeLeaders: 'Volume Leaders',
    allMarkets: 'All Markets',
    macroMarkets: 'Macro-Relevant Markets',
    details: 'Details',
    company: 'Company',
    noEvents: 'No events',
    noComparableSurprise: 'No comparable surprise',
    noStats: 'No statistics',
    noEarnings: 'No earnings data. Click “Sync Data” to pull real Jin10 data.',
    noUpdates: 'No valid updates',
    noHolidays: 'No holiday information',
    noPredictionData: 'No Polymarket data yet. Click “Sync Polymarket” to generate the macro event odds radar.',
    noData: 'No data',
    noMatchingMacro: 'No matching macro markets. Sync Polymarket first, or switch to “All”.',
    syncStarted: 'Starting default-window sync...',
    syncDone: 'Sync complete',
    syncFailed: 'Sync failed: ',
    loadFailed: 'Load failed: ',
    pmSyncStarted: 'Starting Polymarket sync. This may take a few dozen seconds...',
    pmSyncDone: 'Polymarket sync complete',
    pmSyncFailed: 'Polymarket sync failed: ',
    releasedStatus: 'Released',
    partialStatus: 'Partially released',
    upcomingStatus: 'Upcoming',
    staleStatus: 'Needs follow-up',
    preMarket: 'Pre-market',
    afterHours: 'After-hours',
    unknown: 'Unknown',
    importantUpdate: 'Important Updates',
    countSuffix: 'items',
    metricActiveCompanies: 'Covered Companies',
    metricActiveCompaniesSub: 'Companies with earnings/indicators in the next 7 days',
    metricHighStarCompanies: 'Focus Companies',
    metricHighStarCompaniesSub: 'Company-level earnings events with Star 4/5',
    metricNext48h: 'Next 48h Window',
    metricNext48hSub: 'Earnings windows from today through tomorrow',
    metricComparable: 'Comparable Results',
    metricComparableSub: 'Both Actual and Consensus are present',
    metricSurprise: 'Beat / Miss',
    metricSurpriseSub: 'Beat vs miss indicator count',
    metricMaterial: 'Material Updates',
    metricMaterialSub: 'Deduplicated effective data/event changes',
    englishBriefHeadline: '{group} enters the event watch window',
    englishBriefParagraph: 'There are {events} aggregated earnings events in the next {days} days, including {highStar} Star 4/5 events. The window is more concentrated in {window}, which helps prioritize opening and after-hours risk.',
    englishBriefGroup: 'Most concentrated group: {group}, with {count} events.',
    englishBriefWindow: 'Pre-market {pre}, after-hours {post}; after-hours events are more likely to affect next-session pre-market pricing.',
    englishBriefSurprise: 'Released indicators: {released}; comparable indicators show {positive} beats and {negative} misses.',
    fallbackGroup: 'Other',
    todayTonight: 'today/tomorrow',
    preMarketWindow: 'pre-market',
    afterHoursWindow: 'after-hours',
    currentCycle: 'period unknown',
    publishedCount: '{released}/{total} released',
    updateKindData: 'Data Update',
    updateKindImportant: 'Important Event',
    updateKindRelease: 'Release',
    updateKindForecast: 'Forecast / Revision',
    updateKindEvent: 'Market Event',
    regionOther: 'Other',
    holiday: 'Holiday',
    lastSync: 'Last sync',
    markets: 'markets',
    notSyncedPolymarket: 'Polymarket not synced yet',
    weightedByVolume: 'volume-weighted',
    watch7dLabel: '7D watch',
    pmTableTheme: 'Theme',
    pmTableEvent: 'Event / Option',
    pmTableProb: 'Prob',
    pmTable7d: '7D',
    pmTable1d: '1D',
    pmTableVolume: 'Volume',
    pmTableSpread: 'Spread',
    pmTableImpact: 'Impact Assets',
    starLabel: 'Star',
    actualLabel: 'Actual',
    consensusLabel: 'Consensus',
    previousLabel: 'Previous',
    surpriseLabel: 'Surprise',
    changeLabel: 'Change',
    lastLabel: 'Last',
    highLabel: 'High',
    lowLabel: 'Low',
    releaseTime: 'Release time',
    metricsCountSentence: 'There are {total} indicators, {released} released.',
    priceReaction: 'Price Reaction',
    priceNote: 'Near-session movement; data from yfinance for internal reference only.',
    loadingPrice: 'Loading {ticker} price data...',
    metricDetails: 'Metric Details',
    companyGroups: 'Company Groups',
    loadingPmDetail: 'Loading Polymarket details...',
    probabilityTrend: '7-day Probability Trend',
    assetImpact: 'Asset Impact',
    detailLoadFailed: 'Load failed: ',
    noHistory: 'Not enough historical price points. Enable fetch_history during sync.',
    noTicker: 'This event has no ticker, so price movement cannot be loaded.',
    priceLoadFailed: 'Price data failed to load: ',
    priceFallbackHint: 'Install yfinance first, or connect Polygon/Finnhub/internal market data in production.',
    insufficientPrice: 'Not enough price points.',
    priceCommonReasons: 'Common reasons: Yahoo intraday data is empty, the market is closed/holiday, Yahoo network access is blocked, or the ticker cannot be mapped.',
  },
  zh: {
    brandTitle: '市场日历情报',
    brandSubtitle: '美股事件驱动仪表盘',
    tabDashboard: '仪表盘',
    tabEarnings: '财报',
    tabUpdates: '更新',
    tabHolidays: '假期',
    tabPrediction: '预测市场',
    searchPlaceholder: '搜索 TSM / NVDA / 营收 / 盘后',
    syncData: '同步数据',
    thisWeek: '本周',
    waitingHeadline: '等待数据同步',
    waitingParagraph: '同步美股日历后，这里会展示事件主线、财报集中度和盘前/盘后风险窗口。',
    monitorMetrics: '市场监控指标',
    liveIntelligence: '实时情报',
    latestUpdates: '最新更新',
    viewAll: '查看全部',
    today: '今日',
    todayPreMarket: '今日盘前',
    tonight: '今晚',
    todayAfterHours: '今日盘后',
    released: '已公布',
    concentration: '集中度',
    companyGroupsTitle: '公司组别与事件集中度',
    themeGroups: '主线组别',
    frequentCompanies: '高频公司',
    earnings: '财报',
    earningsCalendar: '财报日历',
    releasedFilter: '已公布',
    upcomingFilter: '待公布',
    range7: '7天',
    range30: '30天',
    star4Plus: '4星以上',
    materialChanges: '实质变化',
    importantChanges: '重要变化',
    updatesNote: '全部包含所有 Star 等级的有效事件；前台自动隐藏 delete、无内容记录、普通待公布流水，以及已过去满 7 天的项目。',
    all: '全部',
    dataRelease: '数据公布',
    forecastRevision: '预测/修正',
    marketEvent: '市场事件',
    regionUS: '美国',
    regionEurope: '欧洲',
    regionAsia: '亚洲',
    marketSchedule: '交易日程',
    holidaysSchedule: '假期与交易安排',
    predictionMarkets: '预测市场',
    macroOddsRadar: '宏观事件赔率雷达',
    predictionNote: '直接从 Polymarket Gamma/CLOB API 拉取事件赔率和 7 日概率变化；不再生成 Excel。主视图只保留利率美元、地缘商品、增长风险三条交易主线。',
    ratesUsd: '利率美元',
    geoCommodities: '地缘商品',
    growthRisk: '增长风险',
    syncPolymarket: '同步 Polymarket',
    watch7d: '7日观察',
    themeMonitor: '交易主线监控',
    notSynced: '尚未同步',
    up7d: '7日上升',
    probUp: '概率上升',
    down7d: '7日下降',
    probDown: '概率下降',
    volume: '成交额',
    volumeLeaders: '成交额最高',
    allMarkets: '全部市场',
    macroMarkets: '宏观相关市场',
    details: '详情',
    company: '公司',
    noEvents: '暂无事件',
    noComparableSurprise: '暂无可比较 surprise',
    noStats: '暂无统计',
    noEarnings: '暂无财报数据。请点击“同步数据”拉取真实金十数据。',
    noUpdates: '暂无有效更新',
    noHolidays: '暂无假期信息',
    noPredictionData: '暂无 Polymarket 数据。点击“同步 Polymarket”后生成宏观事件赔率雷达。',
    noData: '暂无数据',
    noMatchingMacro: '暂无匹配的宏观市场。请先同步 Polymarket，或切换到“全部”。',
    syncStarted: '开始同步默认窗口...',
    syncDone: '同步完成',
    syncFailed: '同步失败：',
    loadFailed: '加载失败：',
    pmSyncStarted: '开始同步 Polymarket，可能需要几十秒...',
    pmSyncDone: 'Polymarket 同步完成',
    pmSyncFailed: 'Polymarket 同步失败：',
    releasedStatus: '已公布',
    partialStatus: '部分公布',
    upcomingStatus: '待公布',
    staleStatus: '待补查',
    preMarket: '盘前',
    afterHours: '盘后',
    unknown: '未知',
    importantUpdate: '重要更新',
    countSuffix: '条',
    metricActiveCompanies: '覆盖公司',
    metricActiveCompaniesSub: '未来7天有财报/指标的公司数',
    metricHighStarCompanies: '重点公司',
    metricHighStarCompaniesSub: '4星/5星公司级财报事件',
    metricNext48h: '近48h窗口',
    metricNext48hSub: '今天到明天的财报时间窗口',
    metricComparable: '可比较结果',
    metricComparableSub: '实际值与一致预期均存在',
    metricSurprise: '超/低预期',
    metricSurpriseSub: '超预期 / 低于预期指标数',
    metricMaterial: '实质更新',
    metricMaterialSub: '去重后的有效数据/事件变化',
    fallbackGroup: '其他',
    currentCycle: '周期未知',
    publishedCount: '{released}/{total} 已公布',
    updateKindData: '数据更新',
    updateKindImportant: '重要事件',
    updateKindRelease: '数据公布',
    updateKindForecast: '预测/修正',
    updateKindEvent: '市场事件',
    regionOther: '其他',
    holiday: '假期',
    lastSync: '上次同步',
    markets: '个市场',
    notSyncedPolymarket: '尚未同步 Polymarket',
    weightedByVolume: '按成交额加权',
    watch7dLabel: '7日观察',
    pmTableTheme: '主线',
    pmTableEvent: '事件 / 选项',
    pmTableProb: '概率',
    pmTable7d: '7日',
    pmTable1d: '1日',
    pmTableVolume: '成交额',
    pmTableSpread: '价差',
    pmTableImpact: '影响资产',
    starLabel: '星级',
    actualLabel: '实际值',
    consensusLabel: '一致预期',
    previousLabel: '前值',
    surpriseLabel: '超预期',
    changeLabel: '变化',
    lastLabel: '最新',
    highLabel: '最高',
    lowLabel: '最低',
    releaseTime: '发布时间',
    metricsCountSentence: '当前共有 {total} 个指标，{released} 个已公布。',
    priceReaction: '价格反应',
    priceNote: '近一交易日走势；数据来自 yfinance，仅用于内部参考。',
    loadingPrice: '正在加载 {ticker} 价格数据...',
    metricDetails: '指标明细',
    companyGroups: '公司组别',
    loadingPmDetail: '正在加载 Polymarket 详情...',
    probabilityTrend: '7日概率走势',
    assetImpact: '资产影响',
    detailLoadFailed: '加载失败：',
    noHistory: '暂无足够历史价格点。同步时可打开 fetch_history。',
    noTicker: '该事件缺少 ticker，无法加载价格走势。',
    priceLoadFailed: '价格数据加载失败：',
    priceFallbackHint: '可先安装 yfinance，或正式版改接 Polygon/Finnhub/内部行情源。',
    insufficientPrice: '暂无足够价格点。',
    priceCommonReasons: '常见原因：Yahoo 当日分钟线为空、市场休市/节假日、网络访问 Yahoo 受限、或 ticker 无法映射。',
  },
};
const REGION_LABELS = {
  en: { '美国': 'US', '欧洲': 'Europe', '亚洲': 'Asia', '其他': 'Other' },
  zh: { '美国': '美国', '欧洲': '欧洲', '亚洲': '亚洲', '其他': '其他' },
};
const GROUP_LABELS = {
  en: { '消费': 'Consumer', '其他': 'Other' },
  zh: { '消费': '消费', '其他': '其他' },
};
const fmt = (v) => (v === null || v === undefined || v === '' ? '—' : v);
const shortTime = (v) => v ? String(v).replace('T',' ').replace('.000Z','').replace('Z','').slice(0,16) : '—';
const clsSurprise = (v) => (v || 0) >= 0 ? 'pos' : 'neg';
const fmtNum = (v, digits=2) => (v === null || v === undefined || Number.isNaN(Number(v))) ? '—' : Number(v).toFixed(digits);
const fmtMoney = (v) => {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return '—';
  const n = Number(v);
  if (n >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  if (n >= 1e3) return `$${(n / 1e3).toFixed(1)}K`;
  return `$${n.toFixed(0)}`;
};
const fmtPP = (v, digits=1) => {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return '—';
  const n = Number(v);
  return `${n > 0 ? '+' : ''}${n.toFixed(digits)} pp`;
};
const fmtSignedPct = (v) => {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return '—';
  const n = Number(v);
  return `${n > 0 ? '+' : ''}${n.toFixed(2)}%`;
};
function template(text, vars = {}) {
  return String(text || '').replace(/\{(\w+)\}/g, (_, key) => vars[key] ?? '');
}
function tr(key, vars = {}) {
  return template((I18N[state.language] || I18N.en)[key] ?? I18N.en[key] ?? key, vars);
}
function currentLanguage() {
  return localStorage.getItem('language') === 'zh' ? 'zh' : 'en';
}
function localizeRegion(region) {
  return (REGION_LABELS[state.language] || REGION_LABELS.en)[region] || region || tr('regionOther');
}
function localizeGroup(group) {
  return (GROUP_LABELS[state.language] || GROUP_LABELS.en)[group] || group || tr('fallbackGroup');
}
function applyStaticTranslations() {
  document.documentElement.lang = state.language === 'zh' ? 'zh-CN' : 'en';
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    el.textContent = tr(el.dataset.i18n);
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
    el.setAttribute('placeholder', tr(el.dataset.i18nPlaceholder));
  });
}
function setLanguage(language, options = {}) {
  const next = language === 'zh' ? 'zh' : 'en';
  const changed = state.language !== next;
  state.language = next;
  applyStaticTranslations();
  if ((changed || options.forceRender) && options.render !== false) {
    renderAll();
  }
}
function watchLanguage() {
  window.addEventListener('storage', (event) => {
    if (event.key === 'language') setLanguage(currentLanguage());
  });
  setInterval(() => {
    const next = currentLanguage();
    if (next !== state.language) setLanguage(next);
  }, 500);
}
function dashboardBrief(d) {
  if (state.language === 'zh') return d.brief;
  const groupPair = (d.group_distribution || [])[0] || [tr('fallbackGroup'), 0];
  const group = localizeGroup(groupPair[0]);
  const pre = d.today_focus?.pre_market?.length ?? 0;
  const post = d.today_focus?.after_hours?.length ?? 0;
  const dominantWindow = pre >= post ? tr('preMarketWindow') : tr('afterHoursWindow');
  const events = d.metrics.active_companies ?? d.metrics.earnings_events ?? 0;
  const highStar = d.metrics.high_star_companies ?? d.metrics.high_star_events ?? 0;
  return {
    headline: tr('englishBriefHeadline', { group }),
    paragraph: tr('englishBriefParagraph', {
      events,
      days: d.window?.days ?? 7,
      highStar,
      window: dominantWindow,
    }),
    bullets: [
      tr('englishBriefGroup', { group, count: groupPair[1] || 0 }),
      tr('englishBriefWindow', { pre, post }),
      tr('englishBriefSurprise', {
        released: d.metrics.released_metrics ?? 0,
        positive: d.metrics.positive_surprises || 0,
        negative: d.metrics.negative_surprises || 0,
      }),
    ],
    chips: (d.brief?.chips || []).map((chipText) => localizeGroup(String(chipText).replace(/\s+\d+$/, '')) + (String(chipText).match(/\s+\d+$/)?.[0] || '')),
  };
}

async function api(path, options = {}) {
  const proxiedPath = path.startsWith('/api/')
    ? `${API_PROXY_PREFIX}${path.slice('/api'.length)}`
    : path;
  const res = await fetch(proxiedPath, { headers: { 'Content-Type': 'application/json' }, ...options });
  if (!res.ok) {
    let text = await res.text();
    try { text = JSON.parse(text).detail || text; } catch (_) {}
    throw new Error(text || `HTTP ${res.status}`);
  }
  return await res.json();
}

function toast(msg) {
  const el = $('toast');
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 2800);
}

function chip(text, extra='') { return `<span class="chip ${extra}">${escapeHtml(text)}</span>`; }
function star(star) { return `<span class="star-pill">★ ${fmt(star)}</span>`; }
function timePill(v) {
  if (v === '盘前') return `<span class="time-pill pre">${tr('preMarket')}</span>`;
  if (v === '盘后') return `<span class="time-pill post">${tr('afterHours')}</span>`;
  return `<span class="chip">${escapeHtml(fmt(v))}</span>`;
}
function statusPill(s) {
  const map = {
    upcoming: tr('upcomingStatus'),
    partially_released: tr('partialStatus'),
    released: tr('releasedStatus'),
    stale_pending_release: tr('staleStatus'),
  };
  const cls = s === 'released' ? 'released' : s === 'partially_released' ? 'partial' : 'upcoming';
  return `<span class="status-pill ${cls}">${map[s] || s || '—'}</span>`;
}
function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch]));
}

async function loadAll() {
  try {
    const [dashboard, earnings, updates, holidays, pmOverview, pmMarkets] = await Promise.all([
      api('/api/dashboard?days=7'),
      api('/api/earnings'),
      api('/api/updates?limit=120'),
      api('/api/holidays?limit=200'),
      api('/api/prediction-markets/overview').catch(() => null),
      api('/api/prediction-markets/markets?limit=1000').catch(() => ({data: []})),
    ]);
    state.dashboard = dashboard;
    state.earnings = earnings.data || [];
    state.updates = updates.data || [];
    state.holidays = holidays.data || [];
    state.predictionOverview = pmOverview;
    state.predictionMarkets = pmMarkets.data || [];
    renderAll();
  } catch (err) {
    console.error(err);
    toast(tr('loadFailed') + err.message.slice(0, 160));
  }
}

function renderAll() {
  renderDashboard();
  renderEarnings();
  renderUpdates();
  renderHolidays();
  renderPrediction();
}

function renderDashboard() {
  const d = state.dashboard;
  if (!d) return;
  const brief = dashboardBrief(d);
  $('briefHeadline').textContent = brief.headline;
  $('briefParagraph').textContent = brief.paragraph;
  $('briefBullets').innerHTML = (brief.bullets || []).map(x => `<li>${escapeHtml(x)}</li>`).join('');
  $('briefChips').innerHTML = (brief.chips || []).map(x => chip(x)).join('');

  const metrics = [
    [tr('metricActiveCompanies'), d.metrics.active_companies ?? d.metrics.earnings_events, tr('metricActiveCompaniesSub'), 'earnings'],
    [tr('metricHighStarCompanies'), d.metrics.high_star_companies ?? d.metrics.high_star_events, tr('metricHighStarCompaniesSub'), 'earnings'],
    [tr('metricNext48h'), d.metrics.next_48h_events, tr('metricNext48hSub'), 'earnings'],
    [tr('metricComparable'), d.metrics.comparable_results, tr('metricComparableSub'), 'earnings'],
    [tr('metricSurprise'), `${fmt(d.metrics.positive_surprises || 0)} / ${fmt(d.metrics.negative_surprises || 0)}`, tr('metricSurpriseSub'), 'earnings'],
    [tr('metricMaterial'), d.metrics.material_updates ?? d.metrics.updates_last_loaded, tr('metricMaterialSub'), 'updates'],
  ];
  $('metricGrid').innerHTML = metrics.map(([label, val, sub, jump]) => `
    <button class="metric-tile" type="button" data-view-jump="${jump}">
      <div class="metric-value">${fmt(val)}</div>
      <div class="metric-label">${label}</div>
      <div class="metric-subtitle">${escapeHtml(sub)}</div>
    </button>
  `).join('');

  $('latestUpdates').innerHTML = renderRegionalUpdates(d.latest_updates_by_region || null, d.latest_updates || []);
  $('todayPre').innerHTML = renderCompactEvents(d.today_focus.pre_market || []);
  $('todayPost').innerHTML = renderCompactEvents(d.today_focus.after_hours || []);
  $('topSurprises').innerHTML = renderCompactSurprises(d.top_surprises || []);
  renderBars('groupBars', d.group_distribution || []);
  renderBars('tickerBars', d.ticker_focus || []);
}

function renderRegionalUpdates(byRegion, fallback) {
  const regions = ['美国', '欧洲', '亚洲'];
  if (!byRegion) {
    return `<div class="update-region-grid"><section class="glass update-region"><h3>${tr('importantUpdate')}</h3>${renderUpdateCards(fallback, 6, true)}</section></div>`;
  }
  return `<div class="update-region-grid">${regions.map(region => `
    <section class="glass update-region">
      <div class="region-head"><h3>${localizeRegion(region)}</h3><span>${(byRegion[region] || []).length} ${tr('countSuffix')}</span></div>
      ${renderUpdateCards(byRegion[region] || [], 4, true)}
    </section>
  `).join('')}</div>`;
}

function renderCompactEvents(items) {
  if (!items.length) return `<div class="empty">${tr('noEvents')}</div>`;
  return items.slice(0, 6).map(e => `
    <div class="compact-item" onclick='openEarningsDrawer(${JSON.stringify(e.event_key)})'>
      <div class="compact-title">${escapeHtml(e.company_name || e.ticker || tr('unknown'))} <span class="ticker">${escapeHtml(e.ticker || '')}</span></div>
      <div class="compact-sub">${shortTime(e.pub_time)} · ${tr('starLabel')} ${e.star} · ${escapeHtml((e.measures||[]).join(' / '))}</div>
    </div>
  `).join('');
}

function renderCompactSurprises(items) {
  if (!items.length) return `<div class="empty">${tr('noComparableSurprise')}</div>`;
  return items.slice(0, 6).map(m => `
    <div class="compact-item">
      <div class="compact-title">${escapeHtml(m.ticker || '')} · ${escapeHtml(m.measure || '')} <span class="${clsSurprise(m.surprise_pct)}">${escapeHtml(m.surprise_pct_display)}</span></div>
      <div class="compact-sub">${tr('actualLabel')} ${fmt(m.actual)} vs ${tr('consensusLabel')} ${fmt(m.consensus)}</div>
    </div>
  `).join('');
}

function renderBars(target, pairs) {
  if (!$(target)) return;
  const max = Math.max(1, ...pairs.map(p => p[1] || 0));
  $(target).innerHTML = pairs.length ? pairs.map(([name, count]) => `
    <div class="bar-row">
      <div>${escapeHtml(target === 'groupBars' ? localizeGroup(name) : name)}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${Math.max(8, count / max * 100)}%"></div></div>
      <div>${count}</div>
    </div>
  `).join('') : `<div class="empty">${tr('noStats')}</div>`;
}

function filterByQuery(items, fields) {
  const q = state.query.trim().toLowerCase();
  if (!q) return items;
  return items.filter(item => fields.some(f => String(item[f] || '').toLowerCase().includes(q)) || JSON.stringify(item).toLowerCase().includes(q));
}

function filteredEarnings() {
  let items = filterByQuery(state.earnings, ['company_name', 'ticker', 'time_period', 'time_status']);
  if (state.earningsFilter === 'released') items = items.filter(e => ['released', 'partially_released'].includes(e.status));
  if (state.earningsFilter === 'upcoming') items = items.filter(e => ['upcoming', 'stale_pending_release'].includes(e.status));
  if (state.earningsFilter === 'star4') items = items.filter(e => (e.star || 0) >= 4);
  return items;
}

function renderEarnings() {
  const items = filteredEarnings();
  $('earningsList').innerHTML = items.length ? items.map(renderEarnCard).join('') : `<div class="empty">${tr('noEarnings')}</div>`;
}

function renderEarnCard(e) {
  const topMetrics = (e.metrics || []).slice(0, 3);
  const groups = (e.groups || []).slice(0, 2).map(g => chip(localizeGroup(g), 'group-chip')).join('');
  return `
    <article class="earn-card" onclick='openEarningsDrawer(${JSON.stringify(e.event_key)})'>
      <div class="earn-top">
        <div>
          <div class="company">${escapeHtml(e.company_name || tr('unknown'))}</div>
          <div class="ticker">${escapeHtml(e.ticker || '')} · ${escapeHtml(e.exchange_name || '')}</div>
        </div>
        ${star(e.star)}
      </div>
      <div class="earn-meta">
        ${timePill(e.time_status)}${statusPill(e.status)}${chip(e.time_period || tr('currentCycle'))}${chip(tr('publishedCount', { released: e.released_count, total: e.metrics_count }))}${groups}
      </div>
      <div class="metric-summary">
        ${topMetrics.map(m => `
          <div class="metric-line">
            <span class="metric-name">${escapeHtml(m.measure || '')}</span>
            <span class="metric-value-small">${tr('actualLabel')} ${fmt(m.actual)} · ${tr('surpriseLabel')} <span class="${clsSurprise(m.surprise_pct)}">${escapeHtml(m.surprise_pct_display || '—')}</span></span>
          </div>`).join('')}
      </div>
    </article>`;
}

function updateKindLabel(u) {
  const label = u.display_kind || (u.source_type === 'data' ? '数据更新' : '重要事件');
  if (state.language === 'zh') return label;
  if (label.includes('公布')) return tr('updateKindRelease');
  if (label.includes('修正') || label.includes('预测') || label.includes('前值')) return tr('updateKindForecast');
  if (label.includes('事件')) return tr('updateKindEvent');
  if (u.source_type === 'data') return tr('updateKindData');
  return tr('updateKindImportant');
}
function updateKindClass(u) {
  const k = u.display_kind || updateKindLabel(u);
  if (k.includes('公布')) return 'kind-release';
  if (k.includes('修正') || k.includes('预测') || k.includes('前值')) return 'kind-forecast';
  if (k.includes('事件')) return 'kind-event';
  return '';
}
function renderUpdateCards(items, limit=80, compact=false) {
  const arr = items.slice(0, limit);
  if (!arr.length) return `<div class="empty">${tr('noUpdates')}</div>`;
  return arr.map(u => `
    <article class="update-card ${compact ? 'compact-update' : ''}">
      <div class="update-type ${updateKindClass(u)}">${escapeHtml(localizeRegion(u.region || '其他'))} · ${escapeHtml(updateKindLabel(u))}</div>
      <div class="update-title">${escapeHtml(u.title)}</div>
      <div class="update-change">${escapeHtml(u.change)}</div>
      <div class="update-meta">${star(u.star || 0)}${u.time_status ? timePill(u.time_status) : ''}${chip(shortTime(u.modify_time))}</div>
    </article>`).join('');
}
function filteredUpdates() {
  let items = filterByQuery(state.updates, ['title', 'change', 'ticker', 'company_name', 'source_type', 'action', 'region', 'display_kind']);
  const f = state.updateFilter;
  if (f === 'release') items = items.filter(u => (u.display_kind || '').includes('公布'));
  if (f === 'forecast') items = items.filter(u => ['预测更新', '前值更新', '数据修正'].includes(u.display_kind));
  if (f === 'event') items = items.filter(u => u.source_type === 'event');
  if (f === 'star4') items = items.filter(u => (u.star || 0) >= 4);
  if (['美国', '欧洲', '亚洲'].includes(f)) items = items.filter(u => u.region === f);
  return items;
}
function renderUpdates() {
  const items = filteredUpdates();
  $('updatesList').innerHTML = items.length ? items.map(u => `
    <article class="simple-card material-update ${updateKindClass(u)}">
      <div class="update-type ${updateKindClass(u)}">${escapeHtml(localizeRegion(u.region || '其他'))} · ${escapeHtml(updateKindLabel(u))}</div>
      <div class="simple-title">${escapeHtml(u.title)}</div>
      <p>${escapeHtml(u.change)}</p>
      <div class="simple-meta">${star(u.star || 0)}${u.time_status ? timePill(u.time_status) : ''}${chip(shortTime(u.modify_time))}</div>
    </article>`).join('') : `<div class="empty">${tr('noUpdates')}</div>`;
}
function renderHolidays() {
  const items = filterByQuery(state.holidays, ['name', 'event_content', 'country', 'exchange_name', 'rest_note']);
  $('holidaysList').innerHTML = items.length ? items.map(h => `
    <article class="holiday-card">
      <div class="date">${escapeHtml(h.date || (h.event_time || '').slice(0,10) || '—')}</div>
      <div class="name">${escapeHtml(h.name || h.event_content || tr('holiday'))}</div>
      <div class="note">${escapeHtml(h.country || '')}${h.exchange_name ? ' · ' + escapeHtml(h.exchange_name) : ''}</div>
      <div class="note">${escapeHtml(h.rest_note || h.note || '')}</div>
    </article>`).join('') : `<div class="empty">${tr('noHolidays')}</div>`;
}

function bucketToneClass(bucket) {
  if (bucket === 'rates_usd') return 'rates';
  if (bucket === 'geo_commodities') return 'geo';
  if (bucket === 'growth_risk') return 'growth';
  return '';
}
function bucketLabel(mOrBucket) {
  const bucket = typeof mOrBucket === 'string' ? mOrBucket : mOrBucket?.bucket;
  const fallback = typeof mOrBucket === 'string' ? mOrBucket : mOrBucket?.bucket_label;
  if (bucket === 'rates_usd') return tr('ratesUsd');
  if (bucket === 'geo_commodities') return tr('geoCommodities');
  if (bucket === 'growth_risk') return tr('growthRisk');
  return fallback || tr('all');
}
function filteredPredictionMarkets() {
  let items = filterByQuery(state.predictionMarkets, ['event_title', 'question', 'bucket_label']);
  if (state.pmBucket !== 'all') items = items.filter(m => m.bucket === state.pmBucket);
  return items;
}
function normalizeTextForCompare(s) {
  return String(s || '')
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fff]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}
function shouldShowEventTitle(question, eventTitle) {
  const q = normalizeTextForCompare(question);
  const e = normalizeTextForCompare(eventTitle);
  if (!e || !q) return false;
  if (e === q) return false;
  if (q.includes(e) || e.includes(q)) return false;
  return true;
}
function eventTitleLine(m, cls='compact-sub') {
  if (!shouldShowEventTitle(m.question, m.event_title)) return '';
  return `<div class="${cls}">${escapeHtml((m.event_title || '').slice(0, 96))}</div>`;
}
function pmQuestion(m, n=118) {
  return escapeHtml((m.question || m.event_title || 'Prediction market').slice(0, n));
}
function pmMeta(m, mode='up') {
  const moveCls = (m.change_7d_pp || 0) >= 0 ? 'pos' : 'neg';
  if (mode === 'volume') return `${escapeHtml(bucketLabel(m))} · 7D <span class="${moveCls}">${fmtPP(m.change_7d_pp)}</span> · Prob ${fmtNum(m.prob_pct,1)}%`;
  return `${escapeHtml(bucketLabel(m))} · <span class="${moveCls}">${fmtPP(m.change_7d_pp)}</span> · Vol ${fmtMoney(m.volume_7d)}`;
}
function pmTopLists(items) {
  const copy = [...items];
  return {
    up: copy.filter(m => (m.change_7d_pp || 0) > 0).sort((a,b) => (b.change_7d_pp || 0) - (a.change_7d_pp || 0) || (b.volume_7d || 0) - (a.volume_7d || 0)).slice(0, 6),
    down: copy.filter(m => (m.change_7d_pp || 0) < 0).sort((a,b) => (a.change_7d_pp || 0) - (b.change_7d_pp || 0) || (b.volume_7d || 0) - (a.volume_7d || 0)).slice(0, 6),
    volume: copy.filter(m => (m.volume_7d || 0) > 0).sort((a,b) => (b.volume_7d || 0) - (a.volume_7d || 0)).slice(0, 6),
  };
}
function setPmBucket(bucket) {
  state.pmBucket = bucket || 'all';
  document.querySelectorAll('[data-pm-bucket]').forEach(b => b.classList.toggle('active', b.dataset.pmBucket === state.pmBucket));
  document.querySelectorAll('[data-pm-jump]').forEach(b => b.classList.toggle('active', b.dataset.pmJump === state.pmBucket));
  renderPrediction();
}
function renderPrediction() {
  if (!$('pmBucketBoard')) return;
  const ov = state.predictionOverview || {bucket_summary: [], market_count: 0};
  $('pmFetchedAt').textContent = ov.fetched_at ? `${tr('lastSync')}: ${shortTime(ov.fetched_at)} · ${filteredPredictionMarkets().length}/${ov.market_count || 0} ${tr('markets')}` : tr('notSyncedPolymarket');
  const buckets = ov.bucket_summary || [];
  $('pmBucketBoard').innerHTML = buckets.length ? buckets.map(b => {
    const move = b.weighted_change_pp ?? b.avg_change_pp ?? 0;
    return `
    <article class="glass pm-bucket ${bucketToneClass(b.bucket)} ${state.pmBucket === b.bucket ? 'active' : ''}" data-pm-jump="${escapeHtml(b.bucket)}">
      <div class="pm-bucket-main">
        <div>
          <div class="section-kicker">${escapeHtml(bucketLabel(b.bucket))}</div>
          <h3>${fmtMoney(b.volume_sum)}</h3>
          <p>${escapeHtml(b.subtitle || '')}</p>
        </div>
        <div class="pm-bucket-move ${(move || 0) >= 0 ? 'pos' : 'neg'}">
          <span>${tr('watch7dLabel')}</span>
          <b>${fmtPP(move)}</b>
        </div>
      </div>
      <div class="pm-mini-row"><span>${b.market_count} ${tr('markets')}</span><span>${tr('weightedByVolume')}</span></div>
    </article>`;
  }).join('') : `<div class="empty glass">${tr('noPredictionData')}</div>`;

  const scoped = filteredPredictionMarkets();
  const tops = pmTopLists(scoped);
  $('pmTopUp').innerHTML = renderPmCompact(tops.up, 'up');
  $('pmTopDown').innerHTML = renderPmCompact(tops.down, 'down');
  $('pmVolumeLeaders').innerHTML = renderPmCompact(tops.volume, 'volume');
  renderPmTable();
}
function renderPmCompact(items, mode='up') {
  if (!items.length) return `<div class="empty">${tr('noData')}</div>`;
  return items.slice(0, 6).map(m => `
    <div class="compact-item" onclick='openPmDrawer(${JSON.stringify(m.condition_id)})'>
      <div class="compact-title">${pmQuestion(m, 128)}</div>
      <div class="compact-sub">${pmMeta(m, mode)}</div>
      ${eventTitleLine(m)}
    </div>`).join('');
}
function renderPmTable() {
  const items = filteredPredictionMarkets();
  if (!items.length) {
    $('pmMarketsTable').innerHTML = `<div class="empty">${tr('noMatchingMacro')}</div>`;
    return;
  }
  $('pmMarketsTable').innerHTML = `
    <table class="pm-table">
      <thead><tr><th>${tr('pmTableTheme')}</th><th>${tr('pmTableEvent')}</th><th>${tr('pmTableProb')}</th><th>${tr('pmTable7d')}</th><th>${tr('pmTable1d')}</th><th>${tr('pmTableVolume')}</th><th>${tr('pmTableSpread')}</th><th>${tr('pmTableImpact')}</th></tr></thead>
      <tbody>${items.map(m => {
        const impact = m.asset_impact || {};
        const assets = impact.assets || [];
        return `<tr onclick='openPmDrawer(${JSON.stringify(m.condition_id)})'>
          <td><span class="bucket-pill ${bucketToneClass(m.bucket)}">${escapeHtml(bucketLabel(m))}</span></td>
          <td><div class="pm-q">${escapeHtml(m.question || m.event_title || '')}</div>${shouldShowEventTitle(m.question, m.event_title) ? `<div class="pm-event">${escapeHtml(m.event_title || '')}</div>` : ''}</td>
          <td>${fmtNum(m.prob_pct,1)}%</td>
          <td class="${(m.change_7d_pp || 0) >= 0 ? 'pos' : 'neg'}">${fmtPP(m.change_7d_pp)}</td>
          <td class="${(m.change_1d_pp || 0) >= 0 ? 'pos' : 'neg'}">${fmtPP(m.change_1d_pp)}</td>
          <td>${fmtMoney(m.volume_7d)}</td>
          <td>${fmtPP(m.spread_pp)}</td>
          <td>${assets.map(a => chip(a)).join('')}</td>
        </tr>`;
      }).join('')}</tbody>
    </table>`;
}

function openEarningsDrawer(eventKey) {
  const e = state.earnings.find(x => x.event_key === eventKey);
  if (!e) return;
  state.activeEventKey = eventKey;
  $('drawerTitle').textContent = `${e.company_name || ''} ${e.ticker || ''}`;
  $('drawerBody').innerHTML = `
    <div class="drawer-section">
      <div class="earn-meta">${star(e.star)}${timePill(e.time_status)}${statusPill(e.status)}${chip(e.time_period || '—')}${chip(e.exchange_name || '—')}</div>
      <p>${tr('releaseTime')}: ${escapeHtml(shortTime(e.pub_time))}. ${tr('metricsCountSentence', { total: e.metrics_count, released: e.released_count })}</p>
    </div>
    <div class="drawer-section price-panel">
      <div class="price-head"><div><h3>${tr('priceReaction')}</h3><p class="microcopy">${tr('priceNote')}</p></div>
      <div class="price-controls"><button class="seg active" data-price-range="1d" data-price-interval="5m">1D</button><button class="seg" data-price-range="5d" data-price-interval="15m">5D</button><button class="seg" data-price-range="1mo" data-price-interval="60m">1M</button></div></div>
      <div id="priceSummary" class="price-summary"><div class="empty">${tr('loadingPrice', { ticker: escapeHtml(e.ticker || '') })}</div></div><div id="priceChart" class="price-chart"></div>
    </div>
    <div class="drawer-section"><h3>${tr('metricDetails')}</h3>${e.metrics.map(m => `<div class="metric-line"><span class="metric-name">${escapeHtml(m.measure || '')}</span><span class="metric-value-small">${tr('actualLabel')} ${fmt(m.actual)} · ${tr('consensusLabel')} ${fmt(m.consensus)} · ${tr('previousLabel')} ${fmt(m.previous)} · ${tr('surpriseLabel')} <span class="${clsSurprise(m.surprise_pct)}">${escapeHtml(m.surprise_pct_display || '—')}</span> · ${tr('changeLabel')} <span class="${clsSurprise(m.change_pct)}">${escapeHtml(m.change_pct_display || '—')}</span></span></div>`).join('')}</div>
    <div class="drawer-section"><h3>${tr('companyGroups')}</h3><div class="chip-row">${(e.groups || []).map(g => chip(localizeGroup(g))).join('')}</div></div>
    <div class="drawer-section"><h3>Raw Metrics</h3><pre class="raw-json">${escapeHtml(JSON.stringify(e.metrics, null, 2))}</pre></div>`;
  $('drawer').classList.add('show');
  $('drawerMask').classList.add('show');
  bindPriceControls(e);
  loadPrice(e.ticker, '1d', '5m', e.pub_time);
}

async function openPmDrawer(conditionId) {
  $('drawerTitle').textContent = 'Prediction Market';
  $('drawerBody').innerHTML = `<div class="empty">${tr('loadingPmDetail')}</div>`;
  $('drawer').classList.add('show');
  $('drawerMask').classList.add('show');
  try {
    const m = await api(`/api/prediction-markets/market/${encodeURIComponent(conditionId)}`);
    const impact = m.asset_impact || {};
    const bias = impact.bias || {};
    $('drawerTitle').textContent = bucketLabel(m) || 'Prediction Market';
    $('drawerBody').innerHTML = `
      <div class="drawer-section pm-detail-head">
        <div class="earn-meta"><span class="bucket-pill ${bucketToneClass(m.bucket)}">${escapeHtml(bucketLabel(m))}</span>${chip('Polymarket')}</div>
        <h3>${escapeHtml(m.question || m.event_title || '')}</h3>
        ${shouldShowEventTitle(m.question, m.event_title) ? `<p class="microcopy">${escapeHtml(m.event_title || '')}</p>` : ''}
      </div>
      <div class="drawer-section"><div class="pm-detail-stats">
        <div><span>Current Prob</span><b>${fmtNum(m.prob_pct,1)}%</b></div>
        <div><span>7D Change</span><b class="${(m.change_7d_pp || 0) >= 0 ? 'pos' : 'neg'}">${fmtPP(m.change_7d_pp)}</b></div>
        <div><span>1D Change</span><b class="${(m.change_1d_pp || 0) >= 0 ? 'pos' : 'neg'}">${fmtPP(m.change_1d_pp)}</b></div>
        <div><span>Volume</span><b>${fmtMoney(m.volume_7d)}</b></div>
        <div><span>Bid / Ask</span><b>${fmtNum(m.bid_pct,1)} / ${fmtNum(m.ask_pct,1)}</b></div>
        <div><span>Liquidity</span><b>${fmtMoney(m.liquidity)}</b></div>
      </div></div>
      <div class="drawer-section"><h3>${tr('probabilityTrend')}</h3><div id="pmProbChart" class="price-chart"></div></div>
      <div class="drawer-section"><h3>${tr('assetImpact')}</h3><div class="pm-impact-grid">${Object.entries(bias).map(([asset, val]) => `<div><span>${escapeHtml(asset)}</span><b>${escapeHtml(val)}</b></div>`).join('')}</div><p>${escapeHtml(impact.reason || '')}</p></div>
      <div class="drawer-section"><h3>Raw</h3><pre class="raw-json">${escapeHtml(JSON.stringify(m.raw_json || {}, null, 2))}</pre></div>`;
    renderProbabilityChart(m.history || []);
  } catch (err) {
    $('drawerBody').innerHTML = `<div class="empty">${tr('detailLoadFailed')}${escapeHtml(err.message)}</div>`;
  }
}

function renderProbabilityChart(history) {
  const el = $('pmProbChart');
  if (!el) return;
  const rows = (history || []).filter(x => x.prob_pct !== null && x.prob_pct !== undefined);
  if (rows.length < 2) { el.innerHTML = `<div class="empty">${tr('noHistory')}</div>`; return; }
  const width = 820, height = 260, pad = 28;
  const vals = rows.map(r => Number(r.prob_pct));
  const min = Math.max(0, Math.min(...vals) - 2);
  const max = Math.min(100, Math.max(...vals) + 2);
  const span = Math.max(1e-9, max - min);
  const x = (i) => pad + (i / (rows.length - 1)) * (width - pad * 2);
  const y = (v) => height - pad - ((v - min) / span) * (height - pad * 2);
  const points = rows.map((r, i) => `${x(i).toFixed(1)},${y(Number(r.prob_pct)).toFixed(1)}`).join(' ');
  const up = vals[vals.length - 1] >= vals[0];
  el.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="probability chart">
    <line x1="${pad}" x2="${width-pad}" y1="${y(max).toFixed(1)}" y2="${y(max).toFixed(1)}" class="grid-line" />
    <line x1="${pad}" x2="${width-pad}" y1="${y(min).toFixed(1)}" y2="${y(min).toFixed(1)}" class="grid-line" />
    <polyline points="${points}" class="price-line ${up ? 'up' : 'down'}" />
    <text x="${pad}" y="${pad-8}" class="axis-label">${max.toFixed(1)}%</text>
    <text x="${pad}" y="${height-8}" class="axis-label">${min.toFixed(1)}%</text>
  </svg>`;
}

function bindPriceControls(e) {
  document.querySelectorAll('[data-price-range]').forEach(btn => btn.addEventListener('click', () => {
    document.querySelectorAll('[data-price-range]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    loadPrice(e.ticker, btn.dataset.priceRange, btn.dataset.priceInterval, e.pub_time);
  }));
}
async function loadPrice(ticker, rangeKey='1d', interval='5m', eventTime=null) {
  if (!ticker) { $('priceSummary').innerHTML = `<div class="empty">${tr('noTicker')}</div>`; $('priceChart').innerHTML = ''; return; }
  $('priceSummary').innerHTML = `<div class="empty">${tr('loadingPrice', { ticker: `${escapeHtml(ticker)} ${rangeKey}` })}</div>`;
  $('priceChart').innerHTML = '';
  try { const data = await api(`/api/price/intraday?ticker=${encodeURIComponent(ticker)}&range_key=${encodeURIComponent(rangeKey)}&interval=${encodeURIComponent(interval)}&force=false`); renderPriceSummary(data); renderPriceChart(data, eventTime); }
  catch (err) { $('priceSummary').innerHTML = `<div class="empty">${tr('priceLoadFailed')}${escapeHtml(err.message.slice(0, 180))}<br/>${tr('priceFallbackHint')}</div>`; }
}
function renderPriceSummary(data) {
  const s = data.summary || {}; const pct = s.change_pct; const cls = (pct || 0) >= 0 ? 'pos' : 'neg';
  $('priceSummary').innerHTML = `<div class="price-stat-row"><div><span class="price-label">${tr('lastLabel')}</span><strong>${fmtNum(s.last)}</strong></div><div><span class="price-label">${tr('changeLabel')}</span><strong class="${cls}">${fmtNum(s.change)} / ${fmtSignedPct(s.change_pct)}</strong></div><div><span class="price-label">${tr('highLabel')}</span><strong>${fmtNum(s.high)}</strong></div><div><span class="price-label">${tr('lowLabel')}</span><strong>${fmtNum(s.low)}</strong></div><div><span class="price-label">${tr('volume')}</span><strong>${fmtNum(s.volume, 0)}</strong></div></div><div class="microcopy">${escapeHtml(data.provider)} · ${escapeHtml(data.interval)} · ${data.cached ? 'cache' : 'fresh'} · ${escapeHtml(data.note || '')}</div>`;
}
function renderPriceChart(data, eventTime=null) {
  const bars = (data.bars || []).filter(x => x.close !== null && x.close !== undefined);
  if (bars.length < 2) {
    const d = data.diagnostics || {}; const symbol = data.normalized_ticker || data.ticker || ''; const attempts = (d.attempts || []).map(a => `${a.period}/${a.interval}`).join(' → ');
    $('priceChart').innerHTML = `<div class="empty">${tr('insufficientPrice')}<br/><span class="microcopy">yfinance symbol: ${escapeHtml(symbol)} · points: ${bars.length}${attempts ? ` · tried: ${escapeHtml(attempts)}` : ''}</span><br/><span class="microcopy">${tr('priceCommonReasons')}</span></div>`; return;
  }
  const width = 820, height = 260, pad = 28; const closes = bars.map(b => Number(b.close)); const min = Math.min(...closes), max = Math.max(...closes); const span = Math.max(1e-9, max - min);
  const x = (i) => pad + (i / (bars.length - 1)) * (width - pad * 2); const y = (v) => height - pad - ((v - min) / span) * (height - pad * 2); const points = bars.map((b, i) => `${x(i).toFixed(1)},${y(Number(b.close)).toFixed(1)}`).join(' '); const up = closes[closes.length - 1] >= closes[0];
  $('priceChart').innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="price chart"><line x1="${pad}" x2="${width-pad}" y1="${y(max).toFixed(1)}" y2="${y(max).toFixed(1)}" class="grid-line" /><line x1="${pad}" x2="${width-pad}" y1="${y(min).toFixed(1)}" y2="${y(min).toFixed(1)}" class="grid-line" /><polyline points="${points}" class="price-line ${up ? 'up' : 'down'}" /><text x="${pad}" y="${pad-8}" class="axis-label">${max.toFixed(2)}</text><text x="${pad}" y="${height-8}" class="axis-label">${min.toFixed(2)}</text></svg>`;
}
function closeDrawer() { $('drawer').classList.remove('show'); $('drawerMask').classList.remove('show'); }
function switchView(view) { state.view = view; document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.view === view)); document.querySelectorAll('.view').forEach(v => v.classList.toggle('active-view', v.id === view)); window.scrollTo({ top: 0, behavior: 'smooth' }); }
function bindEvents() {
  document.querySelectorAll('.tab').forEach(btn => btn.addEventListener('click', () => switchView(btn.dataset.view)));
  document.addEventListener('click', (e) => {
    const jump = e.target.closest('[data-view-jump]'); if (jump) switchView(jump.dataset.viewJump);
    const pmJump = e.target.closest('[data-pm-jump]'); if (pmJump) { setPmBucket(pmJump.dataset.pmJump); switchView('prediction'); }
  });
  $('drawerClose').addEventListener('click', closeDrawer); $('drawerMask').addEventListener('click', closeDrawer);
  $('globalSearch').addEventListener('input', (e) => { state.query = e.target.value; renderEarnings(); renderUpdates(); renderHolidays(); renderPrediction(); });
  $('btnSync').addEventListener('click', async () => { try { toast(tr('syncStarted')); await api('/api/sync/default', { method: 'POST' }); await api('/api/sync/logs', { method: 'POST' }).catch(() => null); toast(tr('syncDone')); await loadAll(); } catch (err) { toast(tr('syncFailed') + err.message.slice(0, 160)); } });
  const btnSyncPM = $('btnSyncPM'); if (btnSyncPM) btnSyncPM.addEventListener('click', async () => { try { toast(tr('pmSyncStarted')); await api('/api/prediction-markets/sync?min_prob=0.10&min_volume=10000&max_pages=15&fetch_history=true', { method: 'POST' }); toast(tr('pmSyncDone')); await loadAll(); switchView('prediction'); } catch (err) { toast(tr('pmSyncFailed') + err.message.slice(0, 180)); } });
  document.querySelectorAll('[data-filter]').forEach(btn => btn.addEventListener('click', () => { document.querySelectorAll('[data-filter]').forEach(b => b.classList.remove('active')); document.querySelectorAll('[data-range]').forEach(b => b.classList.remove('active')); btn.classList.add('active'); state.earningsFilter = btn.dataset.filter; renderEarnings(); }));
  document.querySelectorAll('[data-range]').forEach(btn => btn.addEventListener('click', () => { document.querySelectorAll('[data-filter]').forEach(b => b.classList.remove('active')); document.querySelectorAll('[data-range]').forEach(b => b.classList.remove('active')); btn.classList.add('active'); state.earningsFilter = null; renderEarnings(); }));
  document.querySelectorAll('[data-update-filter]').forEach(btn => btn.addEventListener('click', () => { document.querySelectorAll('[data-update-filter]').forEach(b => b.classList.remove('active')); btn.classList.add('active'); state.updateFilter = btn.dataset.updateFilter || 'all'; renderUpdates(); }));
  document.querySelectorAll('[data-pm-bucket]').forEach(btn => btn.addEventListener('click', () => setPmBucket(btn.dataset.pmBucket || 'all')));
}

setLanguage(currentLanguage(), { render: false });
bindEvents();
watchLanguage();
loadAll();
setInterval(loadAll, 60_000);
