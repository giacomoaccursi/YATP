/**
 * Vue app for the performance page.
 * No business logic — all return calculations come from the API.
 * Date filtering is pure UI slicing on pre-computed data.
 */

const { createApp, ref, watch, onMounted, onUnmounted, nextTick } = Vue;

createApp({
  setup() {
    const historyLoading = ref(true);
    const periodsLoading = ref(true);
    const periods = ref([]);
    const compareChart = ref(null);
    const returnChart = ref(null);
    let compareChartInstance = null;
    let returnChartInstance = null;

    // Pre-computed data from API (fetched once)
    let allDates = [];
    let allReturnPcts = [];
    let allTotalReturnPcts = [];
    let allTwrPcts = [];
    let allMwrrPcts = [];

    // Toggle: include realized gains
    const includeRealized = ref(false);

    // Period filter state (UI only)
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

    // UI-only: slice arrays by date range
    function getFilteredIndices() {
      if (!allDates.length) return { start: 0, end: 0 };

      var fromDate = allDates[0];
      var toDate = allDates[allDates.length - 1];

      if (activePreset.value === 'custom') {
        if (customFrom.value) fromDate = customFrom.value;
        if (customTo.value) toDate = customTo.value;
      } else if (activePreset.value === 'ytd') {
        fromDate = new Date().getFullYear() + '-01-01';
      } else {
        var preset = presets.find(function (p) { return p.key === activePreset.value; });
        if (preset && preset.days) {
          var d = new Date();
          d.setDate(d.getDate() - preset.days);
          fromDate = d.toISOString().split('T')[0];
        }
      }

      var start = -1;
      var end = -1;
      for (var i = 0; i < allDates.length; i++) {
        if (allDates[i] <= fromDate) start = i;
        if (allDates[i] <= toDate) end = i;
      }
      if (start === -1) start = 0;
      return { start: start, end: end + 1 };
    }

    function updateReturnChart() {
      var idx = getFilteredIndices();
      var dates = allDates.slice(idx.start, idx.end);
      var rawPcts = includeRealized.value
        ? allTotalReturnPcts.slice(idx.start, idx.end)
        : allReturnPcts.slice(idx.start, idx.end);

      // Rebase simple return to start of filtered period
      var pcts = rawPcts;
      if (rawPcts.length > 0) {
        var base = rawPcts[0];
        pcts = rawPcts.map(function (v) { return Math.round((v - base) * 100) / 100; });
      }

      var twrPcts = null;
      var rawTwr = allTwrPcts.slice(idx.start, idx.end);
      if (rawTwr.length > 0) {
        var startFactor = 1 + rawTwr[0] / 100;
        twrPcts = rawTwr.map(function (v) {
          var factor = 1 + v / 100;
          return startFactor > 0 ? Math.round((factor / startFactor - 1) * 10000) / 100 : 0;
        });
      }

      var mwrrPcts = null;

      renderReturnChart(dates, pcts, twrPcts, mwrrPcts);
    }

    function renderReturnChart(dates, returnPcts, twrPcts, mwrrPcts) {
      if (!returnChart.value || !dates.length) return;
      if (returnChartInstance) returnChartInstance.destroy();

      var datasets = [{
        label: 'Simple Return',
        data: returnPcts,
        borderColor: '#6366f1',
        backgroundColor: function (ctx) {
          if (!ctx.raw && ctx.raw !== 0) return 'transparent';
          return ctx.raw >= 0 ? 'rgba(99, 102, 241, 0.1)' : 'rgba(239, 68, 68, 0.1)';
        },
        fill: true, tension: 0.3, pointRadius: 0, pointHitRadius: 10, borderWidth: 2,
      }];

      if (twrPcts) {
        datasets.push({
          label: 'TWR',
          data: twrPcts,
          borderColor: '#22d3ee',
          fill: false, tension: 0.3, pointRadius: 0, pointHitRadius: 10, borderWidth: 2, borderDash: [4, 2],
        });
      }

      if (mwrrPcts && mwrrPcts.length) {
        datasets.push({
          label: 'MWRR (p.a.)',
          data: mwrrPcts,
          borderColor: '#f59e0b',
          fill: false, tension: 0.3, pointRadius: 0, pointHitRadius: 10, borderWidth: 2, borderDash: [8, 4],
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

    function renderCompareChart(periodsData) {
      if (!compareChart.value) return;
      if (compareChartInstance) compareChartInstance.destroy();

      var available = periodsData.filter(function (p) { return p.available; });
      if (!available.length) return;

      var labels = available.map(function (p) { return p.period; });
      var twrValues = available.map(function (p) { return p.twr; });
      var mwrrValues = available.map(function (p) { return p.mwrr; });

      compareChartInstance = new Chart(compareChart.value, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [
            { label: 'TWR', data: twrValues, backgroundColor: 'rgba(99, 102, 241, 0.7)', borderColor: '#6366f1', borderWidth: 1, borderRadius: 4 },
            { label: 'MWRR', data: mwrrValues, backgroundColor: 'rgba(34, 211, 238, 0.7)', borderColor: '#22d3ee', borderWidth: 1, borderRadius: 4 },
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

    function selectPreset(key) {
      activePreset.value = key;
      nextTick(updateReturnChart);
    }

    watch(includeRealized, function () { nextTick(updateReturnChart); });

    function applyCustomRange() {
      activePreset.value = 'custom';
      nextTick(updateReturnChart);
    }

    function reRenderAll() {
      updateReturnChart();
      if (periods.value.length) renderCompareChart(periods.value);
    }

    async function fetchHistory() {
      try {
        var res = await fetch('/api/portfolio/history');
        var data = await res.json();
        allDates = data.dates;
        allReturnPcts = data.return_pcts || [];
        allTotalReturnPcts = data.total_return_pcts || [];
        allTwrPcts = data.twr_pcts || [];
        allMwrrPcts = data.mwrr_pcts || [];
        historyLoading.value = false;
        await nextTick();
        updateReturnChart();
      } catch (err) {
        console.error('Failed to fetch history:', err);
        historyLoading.value = false;
      }
    }

    async function fetchPeriods() {
      try {
        var res = await fetch('/api/performance/periods');
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

    function onThemeChange() { nextTick(reRenderAll); }

    onMounted(function () {
      fetchHistory();
      fetchPeriods();
      window.addEventListener('themechange', onThemeChange);
    });
    onUnmounted(function () { window.removeEventListener('themechange', onThemeChange); });

    return {
      historyLoading, periodsLoading, periods,
      compareChart, returnChart, includeRealized,
      activePreset, customFrom, customTo, presets,
      selectPreset, applyCustomRange,
      fmt, fmtSigned, pnlColor,
    };
  },
}).mount('#app');
