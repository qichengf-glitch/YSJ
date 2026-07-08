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
};

const $ = (id) => document.getElementById(id);
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

async function api(path, options = {}) {
  const res = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options });
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
  if (v === '盘前') return `<span class="time-pill pre">盘前</span>`;
  if (v === '盘后') return `<span class="time-pill post">盘后</span>`;
  return `<span class="chip">${escapeHtml(fmt(v))}</span>`;
}
function statusPill(s) {
  const map = { upcoming: '待公布', partially_released: '部分公布', released: '已公布', stale_pending_release: '待补查' };
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
    toast('加载失败：' + err.message.slice(0, 160));
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
  $('briefHeadline').textContent = d.brief.headline;
  $('briefParagraph').textContent = d.brief.paragraph;
  $('briefBullets').innerHTML = (d.brief.bullets || []).map(x => `<li>${escapeHtml(x)}</li>`).join('');
  $('briefChips').innerHTML = (d.brief.chips || []).map(x => chip(x)).join('');

  const metrics = [
    ['覆盖公司', d.metrics.active_companies ?? d.metrics.earnings_events, '未来7天有财报/指标的公司数', 'earnings'],
    ['重点公司', d.metrics.high_star_companies ?? d.metrics.high_star_events, 'Star 4/5 的公司级财报事件', 'earnings'],
    ['近48h窗口', d.metrics.next_48h_events, '今天到明天的财报时间窗口', 'earnings'],
    ['可比较结果', d.metrics.comparable_results, 'Actual 与 Consensus 均存在', 'earnings'],
    ['超/低预期', `${fmt(d.metrics.positive_surprises || 0)} / ${fmt(d.metrics.negative_surprises || 0)}`, '超预期 / 低于预期指标数', 'earnings'],
    ['实质更新', d.metrics.material_updates ?? d.metrics.updates_last_loaded, '去重后的有效数据/事件变化', 'updates'],
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
    return `<div class="update-region-grid"><section class="glass update-region"><h3>重要更新</h3>${renderUpdateCards(fallback, 6, true)}</section></div>`;
  }
  return `<div class="update-region-grid">${regions.map(region => `
    <section class="glass update-region">
      <div class="region-head"><h3>${region}</h3><span>${(byRegion[region] || []).length} 条</span></div>
      ${renderUpdateCards(byRegion[region] || [], 4, true)}
    </section>
  `).join('')}</div>`;
}

function renderCompactEvents(items) {
  if (!items.length) return `<div class="empty">暂无事件</div>`;
  return items.slice(0, 6).map(e => `
    <div class="compact-item" onclick='openEarningsDrawer(${JSON.stringify(e.event_key)})'>
      <div class="compact-title">${escapeHtml(e.company_name || e.ticker || 'Unknown')} <span class="ticker">${escapeHtml(e.ticker || '')}</span></div>
      <div class="compact-sub">${shortTime(e.pub_time)} · Star ${e.star} · ${escapeHtml((e.measures||[]).join(' / '))}</div>
    </div>
  `).join('');
}

function renderCompactSurprises(items) {
  if (!items.length) return `<div class="empty">暂无可比较 surprise</div>`;
  return items.slice(0, 6).map(m => `
    <div class="compact-item">
      <div class="compact-title">${escapeHtml(m.ticker || '')} · ${escapeHtml(m.measure || '')} <span class="${clsSurprise(m.surprise_pct)}">${escapeHtml(m.surprise_pct_display)}</span></div>
      <div class="compact-sub">Actual ${fmt(m.actual)} vs Consensus ${fmt(m.consensus)}</div>
    </div>
  `).join('');
}

function renderBars(target, pairs) {
  if (!$(target)) return;
  const max = Math.max(1, ...pairs.map(p => p[1] || 0));
  $(target).innerHTML = pairs.length ? pairs.map(([name, count]) => `
    <div class="bar-row">
      <div>${escapeHtml(name)}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${Math.max(8, count / max * 100)}%"></div></div>
      <div>${count}</div>
    </div>
  `).join('') : `<div class="empty">暂无统计</div>`;
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
  $('earningsList').innerHTML = items.length ? items.map(renderEarnCard).join('') : `<div class="empty">暂无财报数据。请点击“同步数据”拉取真实金十数据。</div>`;
}

function renderEarnCard(e) {
  const topMetrics = (e.metrics || []).slice(0, 3);
  const groups = (e.groups || []).slice(0, 2).map(g => chip(g, 'group-chip')).join('');
  return `
    <article class="earn-card" onclick='openEarningsDrawer(${JSON.stringify(e.event_key)})'>
      <div class="earn-top">
        <div>
          <div class="company">${escapeHtml(e.company_name || 'Unknown')}</div>
          <div class="ticker">${escapeHtml(e.ticker || '')} · ${escapeHtml(e.exchange_name || '')}</div>
        </div>
        ${star(e.star)}
      </div>
      <div class="earn-meta">
        ${timePill(e.time_status)}${statusPill(e.status)}${chip(e.time_period || '周期未知')}${chip(`${e.released_count}/${e.metrics_count} 已公布`)}${groups}
      </div>
      <div class="metric-summary">
        ${topMetrics.map(m => `
          <div class="metric-line">
            <span class="metric-name">${escapeHtml(m.measure || '')}</span>
            <span class="metric-value-small">Actual ${fmt(m.actual)} · Surprise <span class="${clsSurprise(m.surprise_pct)}">${escapeHtml(m.surprise_pct_display || '—')}</span></span>
          </div>`).join('')}
      </div>
    </article>`;
}

function updateKindLabel(u) { return u.display_kind || (u.source_type === 'data' ? '数据更新' : '重要事件'); }
function updateKindClass(u) {
  const k = updateKindLabel(u);
  if (k.includes('公布')) return 'kind-release';
  if (k.includes('修正') || k.includes('预测') || k.includes('前值')) return 'kind-forecast';
  if (k.includes('事件')) return 'kind-event';
  return '';
}
function renderUpdateCards(items, limit=80, compact=false) {
  const arr = items.slice(0, limit);
  if (!arr.length) return `<div class="empty">暂无有效更新</div>`;
  return arr.map(u => `
    <article class="update-card ${compact ? 'compact-update' : ''}">
      <div class="update-type ${updateKindClass(u)}">${escapeHtml(u.region || '其他')} · ${escapeHtml(updateKindLabel(u))}</div>
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
      <div class="update-type ${updateKindClass(u)}">${escapeHtml(u.region || '其他')} · ${escapeHtml(updateKindLabel(u))}</div>
      <div class="simple-title">${escapeHtml(u.title)}</div>
      <p>${escapeHtml(u.change)}</p>
      <div class="simple-meta">${star(u.star || 0)}${u.time_status ? timePill(u.time_status) : ''}${chip(shortTime(u.modify_time))}</div>
    </article>`).join('') : `<div class="empty">暂无有效更新</div>`;
}
function renderHolidays() {
  const items = filterByQuery(state.holidays, ['name', 'event_content', 'country', 'exchange_name', 'rest_note']);
  $('holidaysList').innerHTML = items.length ? items.map(h => `
    <article class="holiday-card">
      <div class="date">${escapeHtml(h.date || (h.event_time || '').slice(0,10) || '—')}</div>
      <div class="name">${escapeHtml(h.name || h.event_content || 'Holiday')}</div>
      <div class="note">${escapeHtml(h.country || '')}${h.exchange_name ? ' · ' + escapeHtml(h.exchange_name) : ''}</div>
      <div class="note">${escapeHtml(h.rest_note || h.note || '')}</div>
    </article>`).join('') : `<div class="empty">暂无假期信息</div>`;
}

function bucketToneClass(bucket) {
  if (bucket === 'rates_usd') return 'rates';
  if (bucket === 'geo_commodities') return 'geo';
  if (bucket === 'growth_risk') return 'growth';
  return '';
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
  if (mode === 'volume') return `${escapeHtml(m.bucket_label)} · 7D <span class="${moveCls}">${fmtPP(m.change_7d_pp)}</span> · Prob ${fmtNum(m.prob_pct,1)}%`;
  return `${escapeHtml(m.bucket_label)} · <span class="${moveCls}">${fmtPP(m.change_7d_pp)}</span> · Vol ${fmtMoney(m.volume_7d)}`;
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
  $('pmFetchedAt').textContent = ov.fetched_at ? `Last sync: ${shortTime(ov.fetched_at)} · ${filteredPredictionMarkets().length}/${ov.market_count || 0} markets` : '尚未同步 Polymarket';
  const buckets = ov.bucket_summary || [];
  $('pmBucketBoard').innerHTML = buckets.length ? buckets.map(b => {
    const move = b.weighted_change_pp ?? b.avg_change_pp ?? 0;
    return `
    <article class="glass pm-bucket ${bucketToneClass(b.bucket)} ${state.pmBucket === b.bucket ? 'active' : ''}" data-pm-jump="${escapeHtml(b.bucket)}">
      <div class="pm-bucket-main">
        <div>
          <div class="section-kicker">${escapeHtml(b.label)}</div>
          <h3>${fmtMoney(b.volume_sum)}</h3>
          <p>${escapeHtml(b.subtitle || '')}</p>
        </div>
        <div class="pm-bucket-move ${(move || 0) >= 0 ? 'pos' : 'neg'}">
          <span>7日观察</span>
          <b>${fmtPP(move)}</b>
        </div>
      </div>
      <div class="pm-mini-row"><span>${b.market_count} markets</span><span>按成交额加权</span></div>
    </article>`;
  }).join('') : `<div class="empty glass">暂无 Polymarket 数据。点击“同步 Polymarket”后生成宏观事件赔率雷达。</div>`;

  const scoped = filteredPredictionMarkets();
  const tops = pmTopLists(scoped);
  $('pmTopUp').innerHTML = renderPmCompact(tops.up, 'up');
  $('pmTopDown').innerHTML = renderPmCompact(tops.down, 'down');
  $('pmVolumeLeaders').innerHTML = renderPmCompact(tops.volume, 'volume');
  renderPmTable();
}
function renderPmCompact(items, mode='up') {
  if (!items.length) return `<div class="empty">暂无数据</div>`;
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
    $('pmMarketsTable').innerHTML = `<div class="empty">暂无匹配的宏观市场。请先同步 Polymarket，或切换到“全部”。</div>`;
    return;
  }
  $('pmMarketsTable').innerHTML = `
    <table class="pm-table">
      <thead><tr><th>主线</th><th>事件 / Option</th><th>Prob</th><th>7D</th><th>1D</th><th>Volume</th><th>Spread</th><th>影响资产</th></tr></thead>
      <tbody>${items.map(m => {
        const impact = m.asset_impact || {};
        const assets = impact.assets || [];
        return `<tr onclick='openPmDrawer(${JSON.stringify(m.condition_id)})'>
          <td><span class="bucket-pill ${bucketToneClass(m.bucket)}">${escapeHtml(m.bucket_label)}</span></td>
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
      <p>发布时间：${escapeHtml(shortTime(e.pub_time))}。当前共有 ${e.metrics_count} 个指标，${e.released_count} 个已公布。</p>
    </div>
    <div class="drawer-section price-panel">
      <div class="price-head"><div><h3>价格反应</h3><p class="microcopy">近一交易日走势；数据来自 yfinance，仅用于内部参考。</p></div>
      <div class="price-controls"><button class="seg active" data-price-range="1d" data-price-interval="5m">1D</button><button class="seg" data-price-range="5d" data-price-interval="15m">5D</button><button class="seg" data-price-range="1mo" data-price-interval="60m">1M</button></div></div>
      <div id="priceSummary" class="price-summary"><div class="empty">正在加载 ${escapeHtml(e.ticker || '')} 价格数据...</div></div><div id="priceChart" class="price-chart"></div>
    </div>
    <div class="drawer-section"><h3>指标明细</h3>${e.metrics.map(m => `<div class="metric-line"><span class="metric-name">${escapeHtml(m.measure || '')}</span><span class="metric-value-small">Actual ${fmt(m.actual)} · Consensus ${fmt(m.consensus)} · Previous ${fmt(m.previous)} · Surprise <span class="${clsSurprise(m.surprise_pct)}">${escapeHtml(m.surprise_pct_display || '—')}</span> · Change <span class="${clsSurprise(m.change_pct)}">${escapeHtml(m.change_pct_display || '—')}</span></span></div>`).join('')}</div>
    <div class="drawer-section"><h3>公司组别</h3><div class="chip-row">${(e.groups || []).map(g => chip(g)).join('')}</div></div>
    <div class="drawer-section"><h3>Raw Metrics</h3><pre class="raw-json">${escapeHtml(JSON.stringify(e.metrics, null, 2))}</pre></div>`;
  $('drawer').classList.add('show');
  $('drawerMask').classList.add('show');
  bindPriceControls(e);
  loadPrice(e.ticker, '1d', '5m', e.pub_time);
}

async function openPmDrawer(conditionId) {
  $('drawerTitle').textContent = 'Prediction Market';
  $('drawerBody').innerHTML = `<div class="empty">正在加载 Polymarket 详情...</div>`;
  $('drawer').classList.add('show');
  $('drawerMask').classList.add('show');
  try {
    const m = await api(`/api/prediction-markets/market/${encodeURIComponent(conditionId)}`);
    const impact = m.asset_impact || {};
    const bias = impact.bias || {};
    $('drawerTitle').textContent = m.bucket_label || 'Prediction Market';
    $('drawerBody').innerHTML = `
      <div class="drawer-section pm-detail-head">
        <div class="earn-meta"><span class="bucket-pill ${bucketToneClass(m.bucket)}">${escapeHtml(m.bucket_label)}</span>${chip('Polymarket')}</div>
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
      <div class="drawer-section"><h3>7日概率走势</h3><div id="pmProbChart" class="price-chart"></div></div>
      <div class="drawer-section"><h3>资产影响</h3><div class="pm-impact-grid">${Object.entries(bias).map(([asset, val]) => `<div><span>${escapeHtml(asset)}</span><b>${escapeHtml(val)}</b></div>`).join('')}</div><p>${escapeHtml(impact.reason || '')}</p></div>
      <div class="drawer-section"><h3>Raw</h3><pre class="raw-json">${escapeHtml(JSON.stringify(m.raw_json || {}, null, 2))}</pre></div>`;
    renderProbabilityChart(m.history || []);
  } catch (err) {
    $('drawerBody').innerHTML = `<div class="empty">加载失败：${escapeHtml(err.message)}</div>`;
  }
}

function renderProbabilityChart(history) {
  const el = $('pmProbChart');
  if (!el) return;
  const rows = (history || []).filter(x => x.prob_pct !== null && x.prob_pct !== undefined);
  if (rows.length < 2) { el.innerHTML = `<div class="empty">暂无足够历史价格点。同步时可打开 fetch_history。</div>`; return; }
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
  if (!ticker) { $('priceSummary').innerHTML = `<div class="empty">该事件缺少 ticker，无法加载价格走势。</div>`; $('priceChart').innerHTML = ''; return; }
  $('priceSummary').innerHTML = `<div class="empty">正在加载 ${escapeHtml(ticker)} ${rangeKey} 价格数据...</div>`;
  $('priceChart').innerHTML = '';
  try { const data = await api(`/api/price/intraday?ticker=${encodeURIComponent(ticker)}&range_key=${encodeURIComponent(rangeKey)}&interval=${encodeURIComponent(interval)}&force=false`); renderPriceSummary(data); renderPriceChart(data, eventTime); }
  catch (err) { $('priceSummary').innerHTML = `<div class="empty">价格数据加载失败：${escapeHtml(err.message.slice(0, 180))}<br/>可先安装 yfinance，或正式版改接 Polygon/Finnhub/内部行情源。</div>`; }
}
function renderPriceSummary(data) {
  const s = data.summary || {}; const pct = s.change_pct; const cls = (pct || 0) >= 0 ? 'pos' : 'neg';
  $('priceSummary').innerHTML = `<div class="price-stat-row"><div><span class="price-label">Last</span><strong>${fmtNum(s.last)}</strong></div><div><span class="price-label">Change</span><strong class="${cls}">${fmtNum(s.change)} / ${fmtSignedPct(s.change_pct)}</strong></div><div><span class="price-label">High</span><strong>${fmtNum(s.high)}</strong></div><div><span class="price-label">Low</span><strong>${fmtNum(s.low)}</strong></div><div><span class="price-label">Volume</span><strong>${fmtNum(s.volume, 0)}</strong></div></div><div class="microcopy">${escapeHtml(data.provider)} · ${escapeHtml(data.interval)} · ${data.cached ? 'cache' : 'fresh'} · ${escapeHtml(data.note || '')}</div>`;
}
function renderPriceChart(data, eventTime=null) {
  const bars = (data.bars || []).filter(x => x.close !== null && x.close !== undefined);
  if (bars.length < 2) {
    const d = data.diagnostics || {}; const symbol = data.normalized_ticker || data.ticker || ''; const attempts = (d.attempts || []).map(a => `${a.period}/${a.interval}`).join(' → ');
    $('priceChart').innerHTML = `<div class="empty">暂无足够价格点。<br/><span class="microcopy">yfinance symbol: ${escapeHtml(symbol)} · points: ${bars.length}${attempts ? ` · tried: ${escapeHtml(attempts)}` : ''}</span><br/><span class="microcopy">常见原因：Yahoo 当日分钟线为空、市场休市/节假日、网络访问 Yahoo 受限、或 ticker 无法映射。</span></div>`; return;
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
  $('btnSync').addEventListener('click', async () => { try { toast('开始同步默认窗口...'); await api('/api/sync/default', { method: 'POST' }); await api('/api/sync/logs', { method: 'POST' }).catch(() => null); toast('同步完成'); await loadAll(); } catch (err) { toast('同步失败：' + err.message.slice(0, 160)); } });
  const btnSyncPM = $('btnSyncPM'); if (btnSyncPM) btnSyncPM.addEventListener('click', async () => { try { toast('开始同步 Polymarket，可能需要几十秒...'); await api('/api/prediction-markets/sync?min_prob=0.10&min_volume=10000&max_pages=15&fetch_history=true', { method: 'POST' }); toast('Polymarket 同步完成'); await loadAll(); switchView('prediction'); } catch (err) { toast('Polymarket 同步失败：' + err.message.slice(0, 180)); } });
  document.querySelectorAll('[data-filter]').forEach(btn => btn.addEventListener('click', () => { document.querySelectorAll('[data-filter]').forEach(b => b.classList.remove('active')); document.querySelectorAll('[data-range]').forEach(b => b.classList.remove('active')); btn.classList.add('active'); state.earningsFilter = btn.dataset.filter; renderEarnings(); }));
  document.querySelectorAll('[data-range]').forEach(btn => btn.addEventListener('click', () => { document.querySelectorAll('[data-filter]').forEach(b => b.classList.remove('active')); document.querySelectorAll('[data-range]').forEach(b => b.classList.remove('active')); btn.classList.add('active'); state.earningsFilter = null; renderEarnings(); }));
  document.querySelectorAll('[data-update-filter]').forEach(btn => btn.addEventListener('click', () => { document.querySelectorAll('[data-update-filter]').forEach(b => b.classList.remove('active')); btn.classList.add('active'); state.updateFilter = btn.dataset.updateFilter || 'all'; renderUpdates(); }));
  document.querySelectorAll('[data-pm-bucket]').forEach(btn => btn.addEventListener('click', () => setPmBucket(btn.dataset.pmBucket || 'all')));
}

bindEvents();
loadAll();
setInterval(loadAll, 60_000);
