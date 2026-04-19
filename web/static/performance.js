/**
 * Vue app for the performance page.
 * Zero business logic — all calculations done by the backend.
 * The frontend only handles UI state, fetching, and rendering.
 */

const { createApp, ref, computed, watch, onMounted, onUnmounted, nextTick } = Vue;

createApp({
  setup() {
    const historyLoading = ref(true);
    const periodsLoading = ref(true);
    const periods = ref([]);
    const instrumentNames = ref([]);

    // Chip selection
    const selectedSet = ref(new Set());
    const allSelected = computed(function () {
      return instrumentNames.value.length > 0 &&
        selectedSet.value.size === instrumentNames.value.length;
    });

    // Canvas refs
    const compareChart = ref(null);
    const returnChart = ref(null);
    const valueCostChart = ref(null);
    const drawdownChart = ref(null);

    // Chart instances
    let compareChartInstance = null;
    let returnChartInstance = null;
    let valueCostChartInstance = null;
    let drawdownChartInstance = null;

    // Data from API (ready to render, no transformations needed)
    let apiData = {};

    // Toggle: include realized gains
    const includeRealized = ref(false);

    // Period filter
    const activePreset = ref('all');
    const customFrom = ref('');
    const customTo = ref('');
    const presets = [
      { key: '1m', label: '1M', days: 30 },
      { key: '3m', label: '3M', days: 91 },
      { key: '6m', label: '6M', days: 182 },
      { key: '1y', label: '1Y', days: 365 },
      { key: 'ytd', label: 'YTD', days: 0 },
      { key: 'all', label: 'All', days: null },
    ];

    // Heatmap (computed from API TWR data — pure grouping, no math)
    const heatmapMonths = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const heatmapData = ref({ years: [], cells: {}, yearTotals: {} });

    // ── Date range resolution ──

    function getDateRange() {
      if (activePreset.value === 'custom') {
        return { start_date: customFrom.value || null, end_date: customTo.value || null };
      }
      if (activePreset.value === 'ytd') {
        return { start_date: new Date().getFullYear() + '-01-01', end_date: null };
      }
      if (activePreset.value === 'all') {
        return { start_date: null, end_date: null };
      }
      var preset = presets.find(function (p) { return p.key === activePreset.value; });
      if (preset && preset.days) {
        var d = new Date();
        d.setDate(d.getDate() - preset.days);
        return { start_date: d.toISOString().split('T')[0], end_date: null };
      }
      return { start_date: null, end_date: null };
    }

    // ── Chip selection ──

    function selectAll() {
      selectedSet.value = new Set(instrumentNames.value);
      fetchAndRender();
    }

    function toggleChip(name) {
      var next = new Set(selectedSet.value);
      if (next.has(name)) { next.delete(name); } else { next.add(name); }
      if (next.size === 0) { next = new Set(instrumentNames.value); }
      selectedSet.value = next;
      fetchAndRender();
    }

    function selectOnly(name) {
      selectedSet.value = new Set([name]);
      fetchAndRender();
    }

    function selectPreset(key) {
      activePreset.value = key;
      fetchAndRender();
    }

    function applyCustomRange() {
      activePreset.value = 'custom';
      fetchAndRender();
    }

    watch(includeRealized, function () { renderAllCharts(); });

    // ── Fetch + render ──

    async function fetchAndRender() {
      historyLoading.value = true;
      var securities = Array.from(selectedSet.value);
      var isFullPortfolio = allSelected.value;
      var range = getDateRange();

      await Promise.all([
        fetchHistory(securities, isFullPortfolio, range),
        fetchPeriods(securities, isFullPortfolio),
      ]);
    }

    async function fetchHistory(securities, isFullPortfolio, range) {
      try {
        var res;
        if (isFullPortfolio) {
          var params = new URLSearchParams();
          if (range.start_date) params.set('start_date', range.start_date);
          if (range.end_date) params.set('end_date', range.end_date);
          var qs = params.toString();
          res = await fetch('/api/portfolio/history' + (qs ? '?' + qs : ''));
        } else {
          res = await fetch('/api/performance/filtered/history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              securities: securities,
              start_date: range.start_date,
              end_date: range.end_date,
            }),
          });
        }
        apiData = await res.json();
        historyLoading.value = false;
        await nextTick();
        renderAllCharts();
      } catch (err) {
        console.error('Failed to fetch history:', err);
        historyLoading.value = false;
      }
    }

    async function fetchPeriods(securities, isFullPortfolio) {
      try {
        var res;
        if (isFullPortfolio) {
          res = await fetch('/api/performance/periods');
        } else {
          res = await fetch('/api/performance/filtered/periods', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ securities: securities }),
          });
        }
        var data = await res.json();
        periods.value = data.periods;
        periodsLoading.value = false;
        await nextTick();
        renderCompareChart(data.periods);
      } catch (err) {
        console.error('Failed to fetch periods:', err);
        periodsLoading.value = false;
      }
    }

    async function fetchInstrumentNames() {
      try {
        var res = await fetch('/api/portfolio');
        var data = await res.json();
        instrumentNames.value = (data.instruments || []).map(function (i) { return i.security; });
        selectedSet.value = new Set(instrumentNames.value);
      } catch (err) {
        console.error('Failed to fetch instrument names:', err);
      }
    }

    // ── Render (pure rendering, no calculations) ──

    function renderAllCharts() {
      var dates = apiData.dates || [];
      var values = apiData.values || [];
      var costs = apiData.costs || [];
      var returnPcts = includeRealized.value
        ? (apiData.total_return_pcts || [])
        : (apiData.return_pcts || []);
      var twrPcts = apiData.twr_pcts || [];
      var drawdownPcts = apiData.drawdown_pcts || [];

      renderReturnChart(dates, returnPcts, twrPcts);
      renderValueCostChart(dates, values, costs);
      renderDrawdownChart(dates, drawdownPcts);
      computeHeatmap(dates, twrPcts);
    }

    function renderReturnChart(dates, returnPcts, twrPcts) {
      if (!returnChart.value || !dates.length) return;
      if (returnChartInstance) returnChartInstance.destroy();

      var datasets = [{
        label: 'Unrealized Return',
        data: returnPcts,
        borderColor: '#6366f1',
        backgroundColor: function (ctx) {
          if (!ctx.raw && ctx.raw !== 0) return 'transparent';
          return ctx.raw >= 0 ? 'rgba(99, 102, 241, 0.1)' : 'rgba(239, 68, 68, 0.1)';
        },
        fill: true, tension: 0.3, pointRadius: 0, pointHitRadius: 10, borderWidth: 2,
      }];

      if (twrPcts.length) {
        datasets.push({
          label: 'TWR',
          data: twrPcts,
          borderColor: '#22d3ee',
          fill: false, tension: 0.3, pointRadius: 0, pointHitRadius: 10, borderWidth: 2, borderDash: [4, 2],
        });
      }

      returnChartInstance = new Chart(returnChart.value, {
        type: 'line',
        data: { labels: dates, datasets: datasets },
        options: {
          responsive: true,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: { display: true, labels: { color: chartTheme().text, usePointStyle: true, pointStyle: 'circle', font: { size: 11 } } },
            tooltip: chartTooltip({ label: function (ctx) { return ctx.dataset.label + ': ' + fmtSigned(ctx.parsed.y) + '%'; } }),
          },
          scales: chartScales({ yFormat: function (v) { return fmtSigned(v) + '%'; } }),
        },
      });
    }

    function renderValueCostChart(dates, values, costs) {
      if (!valueCostChart.value || !dates.length) return;
      if (valueCostChartInstance) valueCostChartInstance.destroy();

      valueCostChartInstance = new Chart(valueCostChart.value, {
        type: 'line',
        data: {
          labels: dates,
          datasets: [
            { label: 'Market Value', data: values, borderColor: '#6366f1', backgroundColor: 'rgba(99, 102, 241, 0.08)', fill: true, tension: 0.3, pointRadius: 0, pointHitRadius: 10, borderWidth: 2 },
            { label: 'Cost Basis', data: costs, borderColor: '#f59e0b', borderDash: [6, 3], fill: false, tension: 0.3, pointRadius: 0, pointHitRadius: 10, borderWidth: 2 },
          ],
        },
        options: {
          responsive: true,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: { labels: { color: chartTheme().text, usePointStyle: true, pointStyle: 'circle', font: { size: 11 } } },
            tooltip: chartTooltip({ label: function (ctx) { return ctx.dataset.label + ': ' + fmt(ctx.parsed.y) + ' €'; } }),
          },
          scales: chartScales({ yFormat: function (v) { return fmt(v) + ' €'; } }),
        },
      });
    }

    function renderDrawdownChart(dates, drawdownPcts) {
      if (!drawdownChart.value || !dates.length) return;
      if (drawdownChartInstance) drawdownChartInstance.destroy();

      drawdownChartInstance = new Chart(drawdownChart.value, {
        type: 'line',
        data: {
          labels: dates,
          datasets: [{
            label: 'Drawdown', data: drawdownPcts, borderColor: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            fill: true, tension: 0.3, pointRadius: 0, pointHitRadius: 10, borderWidth: 2,
          }],
        },
        options: {
          responsive: true,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: { display: false },
            tooltip: chartTooltip({ label: function (ctx) { return 'Drawdown: ' + ctx.parsed.y.toFixed(2) + '%'; } }),
          },
          scales: chartScales({ yFormat: function (v) { return v.toFixed(1) + '%'; } }),
        },
      });
    }

    function renderCompareChart(periodsData) {
      if (!compareChart.value) return;
      if (compareChartInstance) compareChartInstance.destroy();

      var available = periodsData.filter(function (p) { return p.available; });
      if (!available.length) return;

      compareChartInstance = new Chart(compareChart.value, {
        type: 'bar',
        data: {
          labels: available.map(function (p) { return p.period; }),
          datasets: [
            { label: 'TWR', data: available.map(function (p) { return p.twr; }), backgroundColor: 'rgba(99, 102, 241, 0.7)', borderColor: '#6366f1', borderWidth: 1, borderRadius: 4 },
            { label: 'MWRR', data: available.map(function (p) { return p.mwrr; }), backgroundColor: 'rgba(34, 211, 238, 0.7)', borderColor: '#22d3ee', borderWidth: 1, borderRadius: 4 },
          ],
        },
        options: {
          responsive: true,
          plugins: {
            legend: { labels: { color: chartTheme().text, usePointStyle: true, pointStyle: 'circle', font: { size: 11 } } },
            tooltip: chartTooltip({ label: function (ctx) { return ctx.dataset.label + ': ' + fmtSigned(ctx.parsed.y) + '%'; } }),
          },
          scales: chartScales({ xGrid: false, yFormat: function (v) { return v + '%'; } }),
        },
      });
    }

    // ── Heatmap (pure grouping of API data, no return calculations) ──

    function computeHeatmap(dates, twrPcts) {
      if (!dates || dates.length < 2 || !twrPcts || twrPcts.length < 2) {
        heatmapData.value = { years: [], cells: {}, yearTotals: {} };
        return;
      }

      // Group TWR factors by month — take last factor per month
      var monthlyFactors = {};
      for (var i = 0; i < dates.length; i++) {
        var parts = dates[i].split('-');
        var year = parseInt(parts[0]);
        var month = parseInt(parts[1]) - 1;
        var key = year + '-' + month;
        monthlyFactors[key] = { year: year, month: month, factor: 1 + twrPcts[i] / 100 };
      }

      var sortedKeys = Object.keys(monthlyFactors).sort();
      var cells = {};
      var yearTotals = {};
      var yearsSet = new Set();
      var prevFactor = null;

      for (var k = 0; k < sortedKeys.length; k++) {
        var entry = monthlyFactors[sortedKeys[k]];
        yearsSet.add(entry.year);

        if (prevFactor != null && prevFactor > 0) {
          var monthReturn = (entry.factor / prevFactor - 1) * 100;
          if (!cells[entry.year]) cells[entry.year] = {};
          cells[entry.year][entry.month] = Math.round(monthReturn * 10) / 10;

          if (!yearTotals[entry.year]) yearTotals[entry.year] = 1;
          yearTotals[entry.year] *= (1 + monthReturn / 100);
        }
        prevFactor = entry.factor;
      }

      for (var yr in yearTotals) {
        yearTotals[yr] = Math.round((yearTotals[yr] - 1) * 1000) / 10;
      }

      heatmapData.value = { years: Array.from(yearsSet).sort(), cells: cells, yearTotals: yearTotals };
    }

    function heatmapCellStyle(value) {
      if (value == null) return {};
      var intensity = Math.min(Math.abs(value) / 8, 1);
      if (value >= 0) {
        return { backgroundColor: 'rgba(34, 197, 94, ' + (0.15 + intensity * 0.55) + ')', color: intensity > 0.4 ? '#fff' : '#16a34a' };
      }
      return { backgroundColor: 'rgba(239, 68, 68, ' + (0.15 + intensity * 0.55) + ')', color: intensity > 0.4 ? '#fff' : '#dc2626' };
    }

    // ── Theme ──

    function onThemeChange() { nextTick(renderAllCharts); }

    onMounted(async function () {
      await fetchInstrumentNames();
      await fetchAndRender();
      window.addEventListener('themechange', onThemeChange);
    });
    onUnmounted(function () { window.removeEventListener('themechange', onThemeChange); });

    return {
      historyLoading, periodsLoading, periods,
      instrumentNames, selectedSet, allSelected,
      selectAll, toggleChip, selectOnly,
      compareChart, returnChart, valueCostChart, drawdownChart,
      includeRealized,
      activePreset, customFrom, customTo, presets,
      selectPreset, applyCustomRange,
      heatmapMonths, heatmapData, heatmapCellStyle,
      fmt, fmtSigned, pnlColor,
    };
  },
}).mount('#app');
