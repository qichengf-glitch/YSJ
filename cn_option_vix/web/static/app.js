(() => {
  'use strict';

  const state = {
    config: null,
    terminals: {},
    focus: null,
    latestStatus: null,
    pollTimer: null,
    countdownTimer: null,
    candle: null,
    latestCards: [],
    averageRows: [],
    averagePayload: null,
    contextKey: null,
  };

  const $ = (id) => document.getElementById(id);
  const finiteValue = (v) => {
    if (v == null || v === '') return null;
    const number = Number(v);
    return Number.isFinite(number) ? number : null;
  };
  const fmt = (v, digits = 2) => { const number = finiteValue(v); return number == null ? '—' : number.toFixed(digits); };
  const signed = (v) => { const number = finiteValue(v); return number == null ? '—' : `${number >= 0 ? '+' : ''}${number.toFixed(2)}`; };
  const signClass = (v) => { const number = finiteValue(v); return number == null ? '' : number >= 0 ? 'positive' : 'negative'; };
  const dailyMove = (v) => { const number = finiteValue(v); return number == null ? '—' : `${(number / 16).toFixed(2)}%`; };
  const parseLocal = (text) => text ? new Date(text.replace(' ', 'T') + '+08:00') : null;
  const dateLabel = (text) => {
    if (!text) return '—';
    const d = parseLocal(text);
    return new Intl.DateTimeFormat('en-GB', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Shanghai' }).format(d);
  };
  const compactDate = (text) => {
    const d = parseLocal(text);
    return d ? new Intl.DateTimeFormat('en-GB', { month: 'short', day: '2-digit', timeZone: 'Asia/Shanghai' }).format(d) : '';
  };
  const fullDateTime = (text) => {
    const d = parseLocal(text);
    return d ? new Intl.DateTimeFormat('en-GB', { year: 'numeric', month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Shanghai' }).format(d) : '—';
  };
  const CN_VIX_API_PROXY_PREFIX = window.location.pathname.startsWith('/api/cn-option-vix-dashboard')
    ? '/api/cn-option-vix-dashboard'
    : '';

  async function api(path) {
    const proxiedPath = path.startsWith('/api/')
      ? `${CN_VIX_API_PROXY_PREFIX}${path}`
      : path;
    const res = await fetch(proxiedPath, { cache: 'no-store' });
    if (!res.ok) throw new Error(`${path}: ${res.status}`);
    return res.json();
  }

  function renderCards(payload) {
    state.latestCards = payload.cards || [];
    const container = $('metricCards');
    container.innerHTML = '';
    state.latestCards.forEach(card => {
      const row = state.averageRows.find(item => item.key === card.key) || {};
      const relativeBlock = [20, 60].map(window => {
        const isBenchmark = card.key === 'overall';
        return `
          <div class="card-stat-window">
            <span>${window}D Rel</span>
            <div>
              <b class="${isBenchmark ? '' : signClass(row[`spread_mean_${window}`])}">${isBenchmark ? '—' : signed(row[`spread_mean_${window}`])}</b>
              <small>Mean</small>
            </div>
            <div>
              <b>${isBenchmark ? '—' : fmt(row[`spread_std_${window}`])}</b>
              <small>SD</small>
            </div>
            <div>
              <b>${isBenchmark ? '—' : fmt(row[`spread_variance_${window}`])}</b>
              <small>Var</small>
            </div>
          </div>`;
      }).join('');
      const el = document.createElement('button');
      el.type = 'button';
      el.className = 'metric-card';
      el.dataset.key = card.key;
      el.style.setProperty('--series-color', card.color);
      el.innerHTML = `
        <div class="metric-head">
          <span>${card.label}</span>
          <span class="metric-dot"></span>
        </div>
        <div class="metric-hero">
          <div>
            <span>VIX</span>
            <strong>${fmt(card.value)}</strong>
          </div>
          <div>
            <span>VIX / 16</span>
            <strong>${dailyMove(card.value)}</strong>
          </div>
        </div>
        <div class="metric-subrow">
          <span>5m Δ <strong class="metric-change ${signClass(card.change)}">${signed(card.change)}</strong></span>
          <span>${card.key === 'overall' ? 'Benchmark' : 'vs Overall'} <strong class="metric-spread ${signClass(card.spread)}">${card.key === 'overall' ? '' : signed(card.spread)}</strong></span>
        </div>
        <div class="card-stat-grid">${relativeBlock}</div>
        <span class="card-action">Details</span>`;
      el.addEventListener('click', () => {
        setFocus(card.key);
        openContextDrawer(card.key);
      });
      container.appendChild(el);
    });
    updateFocusClasses();
  }

  function renderAverages(payload) {
    state.averagePayload = payload;
    state.averageRows = payload.rows || [];
    $('averageAsOf').textContent = `As of ${fullDateTime(payload.asof)}`;
    $('averageCoverage').textContent = `${payload.available_trading_days ?? 0} trading days`;
    if (state.contextKey) renderContextDrawer(state.contextKey);
  }

  function regimeFor(row) {
    const avg20 = finiteValue(row?.avg_20);
    const avg60 = finiteValue(row?.avg_60);
    const delta = avg20 == null || avg60 == null ? null : avg20 - avg60;
    if (delta == null || Math.abs(delta) < 0.10) return { className: 'neutral', text: 'NEUTRAL' };
    return delta > 0
      ? { className: 'rising', text: 'RISING' }
      : { className: 'cooling', text: 'COOLING' };
  }

  function contextWindow(row, window, mode) {
    const relative = mode === 'relative';
    const isBenchmark = row?.key === 'overall' && relative;
    return `
      <div class="context-window">
        <div class="context-window-title">${window}D ${relative ? 'Relative Spread' : 'VIX Level'}</div>
        <div class="context-stat">
          <span>${relative ? 'Mean' : 'Average'}</span>
          <strong class="${relative ? signClass(row?.[`spread_mean_${window}`]) : ''}">${isBenchmark ? '—' : relative ? signed(row?.[`spread_mean_${window}`]) : fmt(row?.[`avg_${window}`])}</strong>
        </div>
        <div class="context-stat">
          <span>${relative ? 'SD' : 'Delta vs Avg'}</span>
          <strong class="${relative ? '' : signClass(row?.[`vs_avg_${window}`])}">${isBenchmark ? '—' : relative ? fmt(row?.[`spread_std_${window}`]) : signed(row?.[`vs_avg_${window}`])}</strong>
        </div>
        <div class="context-stat">
          <span>Variance</span>
          <strong>${isBenchmark ? '—' : fmt(row?.[`${relative ? 'spread_variance' : 'variance'}_${window}`])}</strong>
        </div>
      </div>`;
  }

  function renderContextDrawer(key) {
    const card = state.latestCards.find(item => item.key === key);
    const row = state.averageRows.find(item => item.key === key) || {};
    if (!card) return;
    const regime = regimeFor(row);
    $('contextTitle').textContent = card.label;
    $('contextDetails').innerHTML = `
      <section class="context-snapshot" style="--series-color:${card.color}">
        <div>
          <span>Current VIX</span>
          <strong>${fmt(card.value)}</strong>
        </div>
        <div>
          <span>VIX / 16</span>
          <strong>${dailyMove(card.value)}</strong>
        </div>
        <div>
          <span>5m Delta</span>
          <strong class="${signClass(card.change)}">${signed(card.change)}</strong>
        </div>
        <div>
          <span>${card.key === 'overall' ? 'Benchmark' : 'vs Overall'}</span>
          <strong class="${signClass(card.spread)}">${card.key === 'overall' ? '—' : signed(card.spread)}</strong>
        </div>
      </section>
      <section class="context-block">
        <div class="context-block-head">
          <span>Regime</span>
          <strong class="regime-chip ${regime.className}">${regime.text}</strong>
        </div>
        <div class="context-window-grid">
          ${contextWindow(row, 20, 'relative')}
          ${contextWindow(row, 60, 'relative')}
        </div>
      </section>
      <section class="context-block">
        <div class="context-block-head">
          <span>VIX Level Context</span>
          <strong>${state.averagePayload ? `${state.averagePayload.available_trading_days ?? 0} days` : '—'}</strong>
        </div>
        <div class="context-window-grid">
          ${contextWindow(row, 20, 'level')}
          ${contextWindow(row, 60, 'level')}
        </div>
      </section>
    `;
  }

  function openContextDrawer(key) {
    state.contextKey = key;
    renderContextDrawer(key);
    $('contextDrawer').classList.add('open');
    $('contextDrawer').setAttribute('aria-hidden', 'false');
  }

  function closeContextDrawer() {
    $('contextDrawer').classList.remove('open');
    $('contextDrawer').setAttribute('aria-hidden', 'true');
  }

  function createToolbar(element, terminal) {
    element.innerHTML = '';
    state.config.series.forEach(meta => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'series-pill';
      button.dataset.key = meta.key;
      button.style.setProperty('--pill-color', meta.color);
      button.innerHTML = `<span class="swatch"></span>${meta.label}`;
      button.addEventListener('click', () => setFocus(state.focus === meta.key ? null : meta.key));
      element.appendChild(button);
    });
    const all = document.createElement('button');
    all.type = 'button';
    all.className = 'series-pill show-all';
    all.textContent = 'Show all';
    all.addEventListener('click', () => setFocus(null));
    element.appendChild(all);
    terminal.toolbar = element;
  }

  function makeTerminal({ resolution, chartId, legendId, tooltipId, emptyId }) {
    const container = $(chartId);
    const actualByTime = new Map();
    const chart = LightweightCharts.createChart(container, {
      autoSize: true,
      layout: {
        background: { type: 'solid', color: '#ffffff' },
        textColor: '#7a8495',
        fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif',
        fontSize: 10,
      },
      grid: { vertLines: { visible: false }, horzLines: { color: '#edf0f4', style: 0 } },
      localization: {
        locale: 'en-GB',
        // The chart uses the real market timestamp as its data key. Override the
        // crosshair time label so it is always rendered in Asia/Shanghai and,
        // for half-day data, shows the AM/PM session instead of a clock time.
        timeFormatter: (time) => actualByTime.get(Number(time))?.crosshairLabel || '',
      },
      rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.055, bottom: 0.055 }, minimumWidth: 57, ensureEdgeTickMarksVisible: true },
      leftPriceScale: { visible: false },
      timeScale: {
        borderVisible: false,
        timeVisible: false,
        secondsVisible: false,
        rightOffset: 3,
        barSpacing: resolution === '5m' ? 4.0 : 7.5,
        minBarSpacing: 1.0,
        fixLeftEdge: false,
        fixRightEdge: false,
        tickMarkFormatter: (time) => actualByTime.get(Number(time))?.axisLabel || '',
      },
      crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
        vertLine: { color: '#8792a5', width: 1, style: 2, labelBackgroundColor: '#263248' },
        horzLine: { color: '#aeb6c3', width: 1, style: 2, labelVisible: false },
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true },
      handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
    });

    const terminal = {
      resolution, chart, container, lineSeries: {}, actualByTime,
      points: [], mapped: [], toolbar: null, tooltip: $(tooltipId), empty: $(emptyId),
      hasInitialFit: false,
    };

    state.config.series.forEach(meta => {
      const series = chart.addSeries(LightweightCharts.LineSeries, {
        color: meta.color,
        lineWidth: meta.key === 'overall' ? 3 : 2,
        lineStyle: 0,
        pointMarkersVisible: false,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 3,
        lastValueVisible: true,
        priceLineVisible: false,
        title: meta.label,
        priceFormat: { type: 'price', precision: 2, minMove: 0.01 },
      }, 0);
      terminal.lineSeries[meta.key] = series;
    });

    createToolbar($(legendId), terminal);

    chart.subscribeCrosshairMove(param => {
      if (param.time == null || !terminal.actualByTime.has(Number(param.time))) {
        renderTooltip(terminal, null);
        return;
      }
      renderTooltip(terminal, terminal.actualByTime.get(Number(param.time)).point);
    });
    return terminal;
  }

  function chartPoints(points, resolution) {
    return points.map((point, index) => {
      const date = parseLocal(point.timestamp);
      if (!date || Number.isNaN(date.getTime())) {
        throw new Error(`Invalid dashboard timestamp: ${point.timestamp}`);
      }
      const currentDate = point.timestamp.slice(0, 10);
      const previousDate = index ? points[index - 1].timestamp.slice(0, 10) : null;
      const session = point.session || (point.timestamp.slice(11, 16) === '11:30' ? 'AM' : 'PM');
      return {
        // Lightweight Charts spaces bars by logical index, so real timestamps
        // preserve equally-spaced trading observations without creating visual
        // gaps for nights, weekends, or the lunch break.
        chartTime: Math.floor(date.getTime() / 1000),
        point,
        // Five-minute chart: one date label at the start of each trading day.
        // Half-day chart: both observations carry the correct calendar date;
        // the library automatically suppresses overlapping labels.
        axisLabel: resolution === '5m'
          ? (currentDate !== previousDate ? compactDate(point.timestamp) : '')
          : compactDate(point.timestamp),
        crosshairLabel: resolution === '5m'
          ? fullDateTime(point.timestamp)
          : `${compactDate(point.timestamp)} · ${session}`,
      };
    });
  }

  function mainSeriesValue(terminal, meta, point) {
    const raw = Number(point[meta.key]);
    if (!Number.isFinite(raw)) return null;
    return raw;
  }

  function renderMainSeries(terminal) {
    state.config.series.forEach(meta => {
      const data = terminal.mapped.map(item => ({
        time: item.chartTime,
        value: mainSeriesValue(terminal, meta, item.point),
      })).filter(item => item.value != null && Number.isFinite(item.value));
      terminal.lineSeries[meta.key].setData(data);
      terminal.lineSeries[meta.key].applyOptions({
        priceFormat: { type: 'price', precision: 2, minMove: 0.01 },
      });
    });
    try {
      const mainScale = terminal.chart.priceScale('right', 0);
      mainScale.setAutoScale(true);
    } catch (err) {
      console.debug('main scale fallback', err);
    }
  }

  function setTerminalData(terminal, points) {
    terminal.points = points;
    terminal.actualByTime.clear();
    const mapped = chartPoints(points, terminal.resolution);
    terminal.mapped = mapped;
    mapped.forEach(item => terminal.actualByTime.set(item.chartTime, item));
    renderMainSeries(terminal);
    terminal.empty.classList.toggle('hidden', points.length > 0);

    if (points.length && !terminal.hasInitialFit) {
      terminal.chart.timeScale().fitContent();
      terminal.hasInitialFit = true;
    }
    renderTooltip(terminal, points.length ? points[points.length - 1] : null);
    applyTerminalFocus(terminal);
  }

  function renderTooltip(terminal, point) {
    if (!point) {
      terminal.tooltip.innerHTML = '<span>Move across the chart to inspect VIX levels.</span>';
      return;
    }
    const time = `<span class="tooltip-time">${fullDateTime(point.timestamp)}${point.session ? ` · ${point.session}` : ''}</span>`;
    const values = state.config.series.map(meta => {
      const spread = meta.key === 'overall' ? null : point[`spread_${meta.key}_overall`];
      return `<span class="tooltip-item"><span style="color:${meta.color}">${meta.label}</span><b>${fmt(point[meta.key])}</b>${spread == null ? '' : `<em class="${signClass(spread)}">${signed(spread)}</em>`}</span>`;
    }).join('');
    terminal.tooltip.innerHTML = time + values;
  }

  function setFocus(key) {
    state.focus = key;
    Object.values(state.terminals).forEach(applyTerminalFocus);
    renderCandleChart();
    updateFocusClasses();
    if (key && $('contextDrawer')?.classList.contains('open')) {
      state.contextKey = key;
      renderContextDrawer(key);
    }
  }

  function applyTerminalFocus(terminal) {
    state.config.series.forEach(meta => {
      const strong = state.focus == null || meta.key === 'overall' || meta.key === state.focus;
      terminal.lineSeries[meta.key].applyOptions({
        visible: strong,
        color: meta.color,
        lineWidth: meta.key === 'overall' || meta.key === state.focus ? 3 : 2,
        lastValueVisible: strong,
      });
    });
    try {
      terminal.chart.priceScale('right', 0).setAutoScale(true);
    } catch (err) {
      console.debug('focus autoscale fallback', err);
    }
    if (terminal.toolbar) {
      terminal.toolbar.querySelectorAll('[data-key]').forEach(el => {
        el.classList.toggle('active', state.focus == null || el.dataset.key === state.focus);
      });
    }
  }

  function updateFocusClasses() {
    document.querySelectorAll('.metric-card').forEach(card => {
      card.classList.toggle('active', state.focus === card.dataset.key);
      card.classList.toggle('dimmed', state.focus != null && state.focus !== card.dataset.key && card.dataset.key !== 'overall');
    });
  }

  function createCandleToolbar(element) {
    element.innerHTML = '';
    state.config.series.forEach(meta => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'series-pill';
      button.dataset.key = meta.key;
      button.style.setProperty('--pill-color', meta.color);
      button.innerHTML = `<span class="swatch"></span>${meta.label}`;
      button.addEventListener('click', () => setFocus(meta.key));
      element.appendChild(button);
    });
  }

  function candleTargetMeta() {
    const key = state.focus || 'overall';
    return state.config.series.find(meta => meta.key === key) || state.config.series[0];
  }

  function makeCandleTerminal({ chartId, legendId, tooltipId, emptyId }) {
    const container = $(chartId);
    const actualByTime = new Map();
    const chart = LightweightCharts.createChart(container, {
      autoSize: true,
      layout: {
        background: { type: 'solid', color: '#ffffff' },
        textColor: '#7a8495',
        fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif',
        fontSize: 10,
      },
      grid: { vertLines: { visible: false }, horzLines: { color: '#edf0f4', style: 0 } },
      localization: {
        locale: 'en-GB',
        timeFormatter: (time) => actualByTime.get(Number(time))?.crosshairLabel || '',
      },
      rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.08, bottom: 0.08 }, minimumWidth: 57 },
      timeScale: {
        borderVisible: false,
        timeVisible: false,
        secondsVisible: false,
        rightOffset: 3,
        barSpacing: 7.0,
        minBarSpacing: 2.0,
        tickMarkFormatter: (time) => actualByTime.get(Number(time))?.axisLabel || '',
      },
      crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
        vertLine: { color: '#8792a5', width: 1, style: 2, labelBackgroundColor: '#263248' },
        horzLine: { color: '#aeb6c3', width: 1, style: 2, labelVisible: false },
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true },
      handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
    });
    const series = chart.addSeries(LightweightCharts.CandlestickSeries, {
      upColor: '#c63f48',
      downColor: '#14805a',
      borderUpColor: '#c63f48',
      borderDownColor: '#14805a',
      wickUpColor: '#c63f48',
      wickDownColor: '#14805a',
      priceLineVisible: false,
      lastValueVisible: true,
      priceFormat: { type: 'price', precision: 2, minMove: 0.01 },
    });
    const terminal = {
      chart, series, actualByTime, points: [], mapped: [], tooltip: $(tooltipId), empty: $(emptyId), hasInitialFit: false,
    };
    createCandleToolbar($(legendId));
    chart.subscribeCrosshairMove(param => {
      if (param.time == null || !actualByTime.has(Number(param.time))) {
        renderCandleTooltip(null);
        return;
      }
      renderCandleTooltip(actualByTime.get(Number(param.time)));
    });
    return terminal;
  }

  function aggregate15m(points, key) {
    const groups = new Map();
    points.forEach(point => {
      const value = Number(point[key]);
      const date = parseLocal(point.timestamp);
      if (!Number.isFinite(value) || !date || Number.isNaN(date.getTime())) return;
      const day = point.timestamp.slice(0, 10);
      const totalMinutes = date.getHours() * 60 + date.getMinutes();
      const endMinutes = Math.ceil(totalMinutes / 15) * 15;
      const endHour = Math.floor(endMinutes / 60);
      const endMinute = endMinutes % 60;
      const bucket = `${day} ${String(endHour).padStart(2, '0')}:${String(endMinute).padStart(2, '0')}:00`;
      if (!groups.has(bucket)) groups.set(bucket, []);
      groups.get(bucket).push({ point, value });
    });
    return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([timestamp, rows]) => {
      const values = rows.map(row => row.value);
      const date = parseLocal(timestamp);
      return {
        time: Math.floor(date.getTime() / 1000),
        timestamp,
        open: values[0],
        high: Math.max(...values),
        low: Math.min(...values),
        close: values[values.length - 1],
        count: values.length,
      };
    });
  }

  function renderCandleTooltip(candle) {
    const terminal = state.candle;
    if (!terminal) return;
    const meta = candleTargetMeta();
    if (!candle) {
      terminal.tooltip.innerHTML = `<span>Select a chain to inspect 15-minute VIX candles.</span>`;
      return;
    }
    const directionClass = candle.close >= candle.open ? 'positive' : 'negative';
    terminal.tooltip.innerHTML = `
      <span class="tooltip-time">${fullDateTime(candle.timestamp)}</span>
      <span class="tooltip-item"><span style="color:${meta.color}">${meta.label}</span><b>${fmt(candle.close)}</b><em class="${directionClass}">${signed(candle.close - candle.open)}</em></span>
      <span class="tooltip-item">O <b>${fmt(candle.open)}</b></span>
      <span class="tooltip-item">H <b>${fmt(candle.high)}</b></span>
      <span class="tooltip-item">L <b>${fmt(candle.low)}</b></span>`;
  }

  function renderCandleChart() {
    const terminal = state.candle;
    if (!terminal) return;
    const meta = candleTargetMeta();
    const candles = aggregate15m(terminal.points, meta.key);
    terminal.actualByTime.clear();
    candles.forEach((candle, index) => {
      const previous = index ? candles[index - 1].timestamp.slice(0, 10) : null;
      terminal.actualByTime.set(candle.time, {
        ...candle,
        axisLabel: candle.timestamp.slice(0, 10) !== previous ? compactDate(candle.timestamp) : '',
        crosshairLabel: fullDateTime(candle.timestamp),
      });
    });
    terminal.series.setData(candles.map(candle => ({
      time: candle.time,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    })));
    terminal.empty.classList.toggle('hidden', candles.length > 0);
    $('candleTarget').textContent = meta.label;
    $('fifteenMinutePointCount').textContent = `${candles.length.toLocaleString()} candles`;
    document.querySelectorAll('#legend15m [data-key]').forEach(el => {
      el.classList.toggle('active', el.dataset.key === meta.key);
    });
    if (candles.length && !terminal.hasInitialFit) {
      terminal.chart.timeScale().fitContent();
      terminal.hasInitialFit = true;
    }
    renderCandleTooltip(candles.length ? candles[candles.length - 1] : null);
  }

  function renderStatus(status) {
    state.latestStatus = status;
    const badge = $('marketBadge');
    badge.className = `market-badge ${status.state.toLowerCase()}`;
    badge.innerHTML = `<span class="status-dot"></span><span>${status.state}</span>`;
    $('last5m').textContent = dateLabel(status.last_5m);
    $('lastHalfday').textContent = dateLabel(status.last_halfday);
    $('qualityText').textContent = status.valid_instruments == null ? '—' : `${status.valid_instruments}/${status.expected_instruments}`;
    $('qualityText').className = status.quality === 'OK' ? 'positive' : 'negative';
    updateCountdowns();
  }

  function countdown(targetText) {
    if (!targetText) return '—';
    const seconds = Math.max(0, Math.floor((new Date(targetText).getTime() - Date.now()) / 1000));
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return h ? `${h}h ${String(m).padStart(2, '0')}m` : `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }

  function updateCountdowns() {
    if (!state.latestStatus) return;
    $('next5m').textContent = `Next ${countdown(state.latestStatus.next_5m)}`;
    $('nextHalfday').textContent = `Next ${countdown(state.latestStatus.next_halfday)}`;
  }

  async function renderQuality() {
    try {
      const q = await api('/api/quality');
      const event = q.last_collector_event;
      const rows = [
        ['Latest point', fullDateTime(q.timestamp)],
        ['Quality', q.quality || '—'],
        ['Valid instruments', `${q.valid_instruments ?? '—'} / ${q.expected_instruments ?? '—'}`],
        ['Valid contracts', q.valid_contracts ?? '—'],
        ['Missing quotes', q.missing_quotes ?? '—'],
        ['Provider timestamp', fullDateTime(q.provider_timestamp)],
        ['Calculated at', fullDateTime(q.calculated_at)],
        ['Collector event', event ? `${event.level} · ${event.event}` : '—'],
        ['Collector event time', event ? fullDateTime(event.event_time) : '—'],
        ['Collector details', event?.details || '—'],
        ['5m database points', q.database?.counts?.['5m'] ?? 0],
        ['Half-day database points', q.database?.counts?.halfday ?? 0],
        ['Database', q.database?.path ?? '—'],
      ];
      $('qualityDetails').innerHTML = rows.map(([k,v]) => `<div class="quality-row"><span>${k}</span><strong>${v}</strong></div>`).join('');
    } catch (err) {
      $('qualityDetails').innerHTML = `<div class="quality-row"><span>Error</span><strong>${err.message}</strong></div>`;
    }
  }

  async function refresh() {
    try {
      const [latest, status, five, half, averages] = await Promise.all([
        api('/api/latest'), api('/api/status'), api('/api/series?resolution=5m'), api('/api/series?resolution=halfday'), api('/api/averages')
      ]);
      renderAverages(averages);
      renderCards(latest);
      renderStatus(status);
      setTerminalData(state.terminals.five, five.points);
      setTerminalData(state.terminals.half, half.points);
      state.candle.points = five.points;
      renderCandleChart();
      $('fiveMinutePointCount').textContent = `${five.count.toLocaleString()} points`;
      $('halfdayPointCount').textContent = `${half.count.toLocaleString()} points`;
      $('footerRefresh').textContent = `Browser refresh: ${new Date().toLocaleTimeString('en-GB', { hour12: false })}`;
    } catch (err) {
      const badge = $('marketBadge');
      badge.className = 'market-badge delayed';
      badge.innerHTML = `<span class="status-dot"></span><span>OFFLINE</span>`;
      console.error(err);
    }
  }

  async function init() {
    if (!window.LightweightCharts) throw new Error('Lightweight Charts failed to load');
    state.config = await api('/api/config');
    const build = $('buildId');
    if (build) build.textContent = `Build: ${state.config.build_id}`;
    state.terminals.five = makeTerminal({ resolution: '5m', chartId: 'chart5m', legendId: 'legend5m', tooltipId: 'tooltip5m', emptyId: 'empty5m' });
    state.candle = makeCandleTerminal({ chartId: 'chart15m', legendId: 'legend15m', tooltipId: 'tooltip15m', emptyId: 'empty15m' });
    state.terminals.half = makeTerminal({ resolution: 'halfday', chartId: 'chartHalfday', legendId: 'legendHalfday', tooltipId: 'tooltipHalfday', emptyId: 'emptyHalfday' });
    await refresh();
    state.pollTimer = setInterval(refresh, state.config.poll_seconds * 1000);
    state.countdownTimer = setInterval(updateCountdowns, 1000);
  }

  $('qualityButton').addEventListener('click', async () => {
    await renderQuality();
    $('qualityDrawer').classList.add('open');
    $('qualityDrawer').setAttribute('aria-hidden', 'false');
  });
  document.querySelectorAll('[data-close-drawer]').forEach(el => el.addEventListener('click', () => {
    $('qualityDrawer').classList.remove('open');
    $('qualityDrawer').setAttribute('aria-hidden', 'true');
  }));
  document.querySelectorAll('[data-close-context]').forEach(el => el.addEventListener('click', closeContextDrawer));

  init().catch(err => {
    console.error(err);
    $('marketBadge').className = 'market-badge delayed';
    $('marketBadge').innerHTML = `<span class="status-dot"></span><span>INIT ERROR</span>`;
  });
})();
