(() => {
  'use strict';

  const state = {
    config: null,
    terminals: {},
    focus: null,
    latestStatus: null,
    pollTimer: null,
    countdownTimer: null,
  };

  const $ = (id) => document.getElementById(id);
  const fmt = (v, digits = 2) => v == null || Number.isNaN(Number(v)) ? '—' : Number(v).toFixed(digits);
  const signed = (v) => v == null || Number.isNaN(Number(v)) ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(2)}`;
  const signClass = (v) => v == null ? '' : Number(v) >= 0 ? 'positive' : 'negative';
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
  const rgba = (hex, alpha) => {
    const h = hex.replace('#', '');
    const n = parseInt(h, 16);
    return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${alpha})`;
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
    const container = $('metricCards');
    container.innerHTML = '';
    payload.cards.forEach(card => {
      const el = document.createElement('button');
      el.type = 'button';
      el.className = 'metric-card';
      el.dataset.key = card.key;
      el.style.setProperty('--series-color', card.color);
      el.innerHTML = `
        <div class="metric-head"><span>${card.label}</span><span class="metric-dot"></span></div>
        <div class="metric-value">${fmt(card.value)}</div>
        <div class="metric-subrow">
          <span>5m Δ <strong class="metric-change ${signClass(card.change)}">${signed(card.change)}</strong></span>
          <span>${card.key === 'overall' ? 'Benchmark' : 'vs Overall'} <strong class="metric-spread ${signClass(card.spread)}">${card.key === 'overall' ? '' : signed(card.spread)}</strong></span>
        </div>`;
      el.addEventListener('click', () => setFocus(state.focus === card.key ? null : card.key));
      container.appendChild(el);
    });
    updateFocusClasses();
  }

  function renderAverages(payload) {
    $('averageAsOf').textContent = `As of ${fullDateTime(payload.asof)}`;
    $('averageCoverage').textContent = `${payload.available_trading_days ?? 0} trading days`;
    const body = $('averageRows');
    if (!payload.rows || !payload.rows.length) {
      body.innerHTML = '<tr><td colspan="7" class="table-loading">No half-day history available.</td></tr>';
      return;
    }
    body.innerHTML = payload.rows.map(row => {
      const regimeDelta = row.avg_30 == null || row.avg_60 == null ? null : Number(row.avg_30) - Number(row.avg_60);
      const regimeClass = regimeDelta == null || Math.abs(regimeDelta) < 0.10 ? 'neutral' : regimeDelta > 0 ? 'rising' : 'cooling';
      const regimeText = regimeClass === 'rising' ? 'RISING' : regimeClass === 'cooling' ? 'COOLING' : 'NEUTRAL';
      return `<tr>
        <td><span class="average-series" style="--series-color:${row.color}"><span class="average-series-dot"></span>${row.label}</span></td>
        <td><span class="average-number">${fmt(row.latest)}</span></td>
        <td>${fmt(row.avg_30)}</td>
        <td><span class="average-delta ${signClass(row.vs_avg_30)}">${signed(row.vs_avg_30)}</span></td>
        <td>${fmt(row.avg_60)}</td>
        <td><span class="average-delta ${signClass(row.vs_avg_60)}">${signed(row.vs_avg_60)}</span></td>
        <td><span class="regime-chip ${regimeClass}">${regimeText}</span></td>
      </tr>`;
    }).join('');
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

  function makeTerminal({ resolution, chartId, legendId, tooltipId, labelsId, emptyId, toggleId, noteId }) {
    const container = $(chartId);
    const actualByTime = new Map();
    const chart = LightweightCharts.createChart(container, {
      autoSize: true,
      layout: {
        background: { type: 'solid', color: '#ffffff' },
        textColor: '#7a8495',
        fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif',
        fontSize: 10,
        panes: { separatorColor: '#e9edf2', separatorHoverColor: '#dce2ea', enableResize: false },
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
      resolution, chart, lineSeries: {}, spreadSeries: {}, actualByTime,
      points: [], mapped: [], toolbar: null, tooltip: $(tooltipId), empty: $(emptyId), labelLayer: $(labelsId),
      viewToggle: $(toggleId), displayNote: $(noteId), viewMode: 'indexed', hasInitialFit: false,
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

    state.config.spreads.forEach((meta, i) => {
      const series = chart.addSeries(LightweightCharts.BaselineSeries, {
        baseValue: { type: 'price', price: 0 },
        topLineColor: meta.color,
        topFillColor1: rgba(meta.color, .38),
        topFillColor2: rgba(meta.color, .06),
        bottomLineColor: '#c7555d',
        bottomFillColor1: 'rgba(199,85,93,.08)',
        bottomFillColor2: 'rgba(199,85,93,.36)',
        lineWidth: 1,
        lastValueVisible: true,
        priceLineVisible: false,
        crosshairMarkerVisible: false,
        priceFormat: { type: 'price', precision: 1, minMove: 0.1 },
      }, i + 1);
      terminal.spreadSeries[meta.group] = series;
    });

    createToolbar($(legendId), terminal);
    requestAnimationFrame(() => sizePanes(terminal));
    new ResizeObserver(() => requestAnimationFrame(() => sizePanes(terminal))).observe(container);
    if (terminal.viewToggle) {
      terminal.viewToggle.querySelectorAll('[data-mode]').forEach(button => {
        button.addEventListener('click', () => setViewMode(terminal, button.dataset.mode));
      });
    }
    container.closest('.chart-card')?.setAttribute('data-view-mode', terminal.viewMode);

    chart.subscribeCrosshairMove(param => {
      if (param.time == null || !terminal.actualByTime.has(Number(param.time))) {
        renderTooltip(terminal, null);
        return;
      }
      renderTooltip(terminal, terminal.actualByTime.get(Number(param.time)).point);
    });
    return terminal;
  }

  function sizePanes(terminal) {
    const panes = terminal.chart.panes();
    if (panes.length < 6) return;
    panes[0].setHeight(335);
    for (let i = 1; i < 6; i++) panes[i].setHeight(55);
    renderPaneLabels(terminal);
  }

  function renderPaneLabels(terminal) {
    terminal.labelLayer.innerHTML = '';
    const panes = terminal.chart.panes();
    if (panes.length < 6) return;
    let top = panes[0].getHeight();
    state.config.spreads.forEach((meta, i) => {
      const el = document.createElement('div');
      el.className = 'pane-label';
      el.dataset.group = meta.group;
      el.style.setProperty('--pane-color', meta.color);
      el.style.top = `${top + 8}px`;
      el.textContent = meta.label;
      terminal.labelLayer.appendChild(el);
      top += panes[i + 1].getHeight();
    });
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

  function mainSeriesValue(terminal, meta, point, baseValue) {
    const raw = Number(point[meta.key]);
    if (!Number.isFinite(raw)) return null;
    if (terminal.viewMode === 'indexed') {
      return Number.isFinite(baseValue) && baseValue !== 0 ? 100 * raw / baseValue : null;
    }
    return raw;
  }

  function renderMainSeries(terminal) {
    state.config.series.forEach(meta => {
      const baseItem = terminal.mapped.find(item => Number.isFinite(Number(item.point[meta.key])));
      const baseValue = baseItem ? Number(baseItem.point[meta.key]) : null;
      const data = terminal.mapped.map(item => ({
        time: item.chartTime,
        value: mainSeriesValue(terminal, meta, item.point, baseValue),
      })).filter(item => item.value != null && Number.isFinite(item.value));
      terminal.lineSeries[meta.key].setData(data);
      terminal.lineSeries[meta.key].applyOptions({
        priceFormat: terminal.viewMode === 'indexed'
          ? { type: 'price', precision: 1, minMove: 0.1 }
          : { type: 'price', precision: 2, minMove: 0.01 },
      });
    });
    try {
      const mainScale = terminal.chart.priceScale('right', 0);
      mainScale.setAutoScale(true);
    } catch (err) {
      console.debug('main scale fallback', err);
    }
  }

  function setViewMode(terminal, mode) {
    if (!['level', 'indexed'].includes(mode) || terminal.viewMode === mode) return;
    terminal.viewMode = mode;
    terminal.viewToggle?.querySelectorAll('[data-mode]').forEach(button => {
      button.classList.toggle('active', button.dataset.mode === mode);
    });
    terminal.viewToggle?.closest('.chart-card')?.setAttribute('data-view-mode', mode);
    if (terminal.displayNote) {
      terminal.displayNote.textContent = mode === 'indexed'
        ? `Indexed view rebases every chain to 100 at the first ${terminal.resolution === '5m' ? 'loaded five-minute' : '2026 half-day'} observation. Exact VIX levels remain in cards and tooltip.`
        : 'Level view shows the exact model-free VIX values. Select a chain to isolate it with Overall and tighten the comparison scale.';
    }
    renderMainSeries(terminal);
    applyTerminalFocus(terminal);
    renderTooltip(terminal, terminal.points.length ? terminal.points[terminal.points.length - 1] : null);
  }

  function setTerminalData(terminal, points) {
    terminal.points = points;
    terminal.actualByTime.clear();
    const mapped = chartPoints(points, terminal.resolution);
    terminal.mapped = mapped;
    mapped.forEach(item => terminal.actualByTime.set(item.chartTime, item));
    renderMainSeries(terminal);
    state.config.spreads.forEach(meta => {
      terminal.spreadSeries[meta.group].setData(mapped
        .filter(item => item.point[meta.key] != null)
        .map(item => ({ time: item.chartTime, value: Number(item.point[meta.key]) })));
    });
    terminal.empty.classList.toggle('hidden', points.length > 0);

    // All five spread panes use the same symmetric scale, so their magnitudes
    // are visually comparable rather than independently auto-scaled.
    const spreadValues = [];
    points.forEach(point => state.config.spreads.forEach(meta => {
      const value = Number(point[meta.key]);
      if (Number.isFinite(value)) spreadValues.push(Math.abs(value));
    }));
    const spreadLimit = Math.max(1, ...spreadValues) * 1.12;
    for (let paneIndex = 1; paneIndex <= 5; paneIndex++) {
      try {
        const scale = terminal.chart.priceScale('right', paneIndex);
        scale.setAutoScale(false);
        scale.setVisibleRange({ from: -spreadLimit, to: spreadLimit });
      } catch (err) {
        console.debug('spread scale fallback', err);
      }
    }

    if (points.length && !terminal.hasInitialFit) {
      terminal.chart.timeScale().fitContent();
      terminal.hasInitialFit = true;
    }
    renderTooltip(terminal, points.length ? points[points.length - 1] : null);
    applyTerminalFocus(terminal);
  }

  function renderTooltip(terminal, point) {
    if (!point) {
      terminal.tooltip.innerHTML = '<span>Move across the chart to inspect all VIX values and spreads.</span>';
      return;
    }
    const time = `<span class="tooltip-time">${fullDateTime(point.timestamp)}${point.session ? ` · ${point.session}` : ''}</span>`;
    const values = state.config.series.map(meta => {
      const spread = meta.key === 'overall' ? null : point[`spread_${meta.key}_overall`];
      let indexed = '';
      if (terminal.viewMode === 'indexed') {
        const basePoint = terminal.points.find(p => Number.isFinite(Number(p[meta.key])));
        const base = basePoint ? Number(basePoint[meta.key]) : null;
        const current = Number(point[meta.key]);
        if (Number.isFinite(base) && base !== 0 && Number.isFinite(current)) indexed = `<small>idx ${fmt(100 * current / base, 1)}</small>`;
      }
      return `<span class="tooltip-item"><span style="color:${meta.color}">${meta.label}</span><b>${fmt(point[meta.key])}</b>${indexed}${spread == null ? '' : `<em class="${signClass(spread)}">${signed(spread)}</em>`}</span>`;
    }).join('');
    terminal.tooltip.innerHTML = time + values;
  }

  function setFocus(key) {
    state.focus = key;
    Object.values(state.terminals).forEach(applyTerminalFocus);
    updateFocusClasses();
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
    state.config.spreads.forEach(meta => {
      const strong = state.focus == null || state.focus === meta.group;
      terminal.spreadSeries[meta.group].applyOptions({
        topLineColor: strong ? meta.color : rgba(meta.color, .12),
        topFillColor1: rgba(meta.color, strong ? .38 : .07),
        topFillColor2: rgba(meta.color, strong ? .06 : .01),
        bottomLineColor: strong ? '#c7555d' : 'rgba(199,85,93,.12)',
        bottomFillColor1: strong ? 'rgba(199,85,93,.08)' : 'rgba(199,85,93,.01)',
        bottomFillColor2: strong ? 'rgba(199,85,93,.36)' : 'rgba(199,85,93,.07)',
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
    terminal.labelLayer.querySelectorAll('.pane-label').forEach(el => {
      el.style.opacity = state.focus == null || el.dataset.group === state.focus ? '1' : '.30';
    });
  }

  function updateFocusClasses() {
    document.querySelectorAll('.metric-card').forEach(card => {
      card.classList.toggle('active', state.focus === card.dataset.key);
      card.classList.toggle('dimmed', state.focus != null && state.focus !== card.dataset.key && card.dataset.key !== 'overall');
    });
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
      renderCards(latest);
      renderAverages(averages);
      renderStatus(status);
      setTerminalData(state.terminals.five, five.points);
      setTerminalData(state.terminals.half, half.points);
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
    state.terminals.five = makeTerminal({ resolution: '5m', chartId: 'chart5m', legendId: 'legend5m', tooltipId: 'tooltip5m', labelsId: 'paneLabels5m', emptyId: 'empty5m', toggleId: 'viewToggle5m', noteId: 'displayNote5m' });
    state.terminals.half = makeTerminal({ resolution: 'halfday', chartId: 'chartHalfday', legendId: 'legendHalfday', tooltipId: 'tooltipHalfday', labelsId: 'paneLabelsHalfday', emptyId: 'emptyHalfday', toggleId: 'viewToggleHalfday', noteId: 'displayNoteHalfday' });
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

  init().catch(err => {
    console.error(err);
    $('marketBadge').className = 'market-badge delayed';
    $('marketBadge').innerHTML = `<span class="status-dot"></span><span>INIT ERROR</span>`;
  });
})();
