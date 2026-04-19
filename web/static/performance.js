/**
 * Vue app for the performance page.
 * No business logic — all return calculations come from the API.
 * Date filtering is pure UI slicing on pre-computed data.
 * Supports portfolio-level and instrument-level views via dropdown.
 */

const { createApp, ref, computed, watch, onMounted, onUnmounted, nextTick } = Vue;

createApp({
  setup() {
    const historyLoading = ref(true);
    const periodsLoading = ref(true);
    const periods = ref([]);
    const instrumentNames = ref([]);
    const selectedInstrument = ref('');

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

    // Pre-computed portfolio data from API (fetched once)
    let portfolioDates = [];
    let portfolioValues = [];
    let portfolioCosts = [];
    let portfolioReturnPcts = [];
    let portfolioTotalReturnPcts = [];
    let portfolioTwrPcts = [];
    let portfolioDrawdownPcts = [];

    // Instrument data (fetched on selection)
    let instrumentDates = [];
    let instrumentPrices = [];
    let instrumentCostAvg = [];
    let instrumentPnl = [];
    let instrumentDrawdownPcts = [];

    // Active data pointers (switch between portfolio and instrument)
    let activeDates = [];
    let activeDrawdownPcts = [];

    // Toggle: include realized gains (portfolio only)
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

    // Heatmap
    const heatmapMonths = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const heatmapData = ref({ years: [], cells: {}, yearTotals: {} });

    // ── Date filtering ──

    function getFilteredIndices() {
      if (!activeDates.length) return { start: 0, end: 0 };

      var fromDate = activeDates[0];
      var toDate = activeDates[activeDates.length - 1];

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
      for (var i = 0; i < activeDates.length; i++) {
        if (activeDates[i] <= fromDate) start = i;
        if (activeDates[i] <= toDate) end = i;
      }
      if (start === -1) start = 0;
      return { start: start, end: end + 1 };
    }

    // ── Chart rendering ──

    function updateAllCharts() {
      updateReturnChart();
      updateValueCostChart();
      updateDrawdownChart();
      computeHeatmap();
    }

    function updateReturnChart() {
      var idx = getFilteredIndices();
      var dates = activeDates.slice(idx.start, idx.end);

      if (selectedInstrument.value) {
        // Instrument mode: show price return %
        var prices = instrumentPrices.slice(idx.start, idx.end);
        if (prices.length > 0) {
          var basePrice = prices[0];
          var priceReturnPcts = prices.map(function (p) {
            return basePrice > 0 ? Math.round((p / basePrice - 1) * 10000) / 100 : 0;
          });
          renderReturnChart(dates, priceReturnPcts, null);
        }
      } else {
        // Portfolio mode: show simple return + TWR
        var rawPcts = includeRealized.value
          ? portfolioTotalReturnPcts.slice(idx.start, idx.end)
          : portfolioReturnPcts.slice(idx.start, idx.end);

        var pcts = rawPcts;
        if (rawPcts.length > 0) {
          var base = rawPcts[0];
          pcts = rawPcts.map(function (v) { return Math.round((v - base) * 100) / 100; });
        }

        var twrPcts = null;
        var rawTwr = portfolioTwrPcts.slice(idx.start, idx.end);
        if (rawTwr.length > 0) {
          var startFactor = 1 + rawTwr[0] / 100;
          twrPcts = rawTwr.map(function (v) {
            var factor = 1 + v / 100;
            return startFactor > 0 ? Math.round((factor / startFactor - 1) * 10000) / 100 : 0;
          });
        }

        renderReturnChart(dates, pcts, twrPcts);
      }
    }

    function renderReturnChart(dates, returnPcts, twrPcts) {
      if (!returnChart.value || !dates.length) return;
      if (returnChartInstance) returnChartInstance.destroy();

      var datasets = [{
        label: selectedInstrument.value ? 'Price Return' : 'Simple Return',
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

    function updateValueCostChart() {
      var idx = getFilteredIndices();
      var dates = activeDates.slice(idx.start, idx.end);

      if (selectedInstrument.value) {
        renderValueCostChart(
          dates,
          instrumentPrices.slice(idx.start, idx.end),
          instrumentCostAvg.slice(idx.start, idx.end),
          'Price', 'Avg Cost'
        );
      } else {
        renderValueCostChart(
          dates,
          portfolioValues.slice(idx.start, idx.end),
          portfolioCosts.slice(idx.start, idx.end),
          'Market Value', 'Cost Basis'
        );
      }
    }

    function renderValueCostChart(dates, values, costs, valueLabel, costLabel) {
      if (!valueCostChart.value || !dates.length) return;
      if (valueCostChartInstance) valueCostChartInstance.destroy();

      valueCostChartInstance = new Chart(valueCostChart.value, {
        type: 'line',
        data: {
          labels: dates,
          datasets: [
            {
              label: valueLabel,
              data: values,
              borderColor: '#6366f1',
              backgroundColor: 'rgba(99, 102, 241, 0.08)',
              fill: true, tension: 0.3, pointRadius: 0, pointHitRadius: 10, borderWidth: 2,
            },
            {
              label: costLabel,
              data: costs,
              borderColor: '#f59e0b',
              borderDash: [6, 3],
              fill: false, tension: 0.3, pointRadius: 0, pointHitRadius: 10, borderWidth: 2,
            },
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

    function updateDrawdownChart() {
      var idx = getFilteredIndices();
      var dates = activeDates.slice(idx.start, idx.end);
      var drawdown = activeDrawdownPcts.slice(idx.start, idx.end);

      // Rebase drawdown to filtered period (recalculate from peak within window)
      if (selectedInstrument.value) {
        var prices = instrumentPrices.slice(idx.start, idx.end);
        drawdown = rebaseDrawdown(prices);
      } else {
        var values = portfolioValues.slice(idx.start, idx.end);
        drawdown = rebaseDrawdown(values);
      }

      renderDrawdownChart(dates, drawdown);
    }

    function rebaseDrawdown(values) {
      var peak = 0;
      var result = [];
      for (var i = 0; i < values.length; i++) {
        if (values[i] > peak) peak = values[i];
        var dd = peak > 0 ? Math.round((values[i] - peak) / peak * 10000) / 100 : 0;
        result.push(dd);
      }
      return result;
    }

    function renderDrawdownChart(dates, drawdownPcts) {
      if (!drawdownChart.value || !dates.length) return;
      if (drawdownChartInstance) drawdownChartInstance.destroy();

      drawdownChartInstance = new Chart(drawdownChart.value, {
        type: 'line',
        data: {
          labels: dates,
          datasets: [{
            label: 'Drawdown',
            data: drawdownPcts,
            borderColor: '#ef4444',
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
          scales: chartScales({
            yFormat: function (v) { return v.toFixed(1) + '%'; },
          }),
        },
      });
    }

    // ── Monthly heatmap ──

    function computeHeatmap() {
      var dates, values;
      if (selectedInstrument.value) {
        dates = instrumentDates;
        values = instrumentPrices;
      } else {
        dates = portfolioDates;
        values = portfolioValues;
      }

      if (dates.length < 2) {
        heatmapData.value = { years: [], cells: {}, yearTotals: {} };
        return;
      }

      // Group values by year-month, take first and last value per month
      var monthlyData = {};
      for (var i = 0; i < dates.length; i++) {
        var parts = dates[i].split('-');
        var year = parseInt(parts[0]);
        var month = parseInt(parts[1]) - 1;
        var key = year + '-' + month;
        if (!monthlyData[key]) {
          monthlyData[key] = { year: year, month: month, first: values[i], last: values[i] };
        } else {
          monthlyData[key].last = values[i];
        }
      }

      // Compute monthly returns: (last / prev_month_last - 1) * 100
      var sortedKeys = Object.keys(monthlyData).sort();
      var cells = {};
      var yearTotals = {};
      var yearsSet = new Set();
      var prevLast = null;

      for (var k = 0; k < sortedKeys.length; k++) {
        var entry = monthlyData[sortedKeys[k]];
        yearsSet.add(entry.year);

        if (prevLast != null && prevLast > 0) {
          var monthReturn = (entry.last / prevLast - 1) * 100;
          if (!cells[entry.year]) cells[entry.year] = {};
          cells[entry.year][entry.month] = Math.round(monthReturn * 10) / 10;

          // Accumulate year total (compound)
          if (!yearTotals[entry.year]) yearTotals[entry.year] = 1;
          yearTotals[entry.year] *= (1 + monthReturn / 100);
        }
        prevLast = entry.last;
      }

      // Convert year totals from compound factor to percentage
      for (var year in yearTotals) {
        yearTotals[year] = Math.round((yearTotals[year] - 1) * 1000) / 10;
      }

      var years = Array.from(yearsSet).sort();
      heatmapData.value = { years: years, cells: cells, yearTotals: yearTotals };
    }

    function heatmapCellStyle(value) {
      if (value == null) return {};
      var intensity = Math.min(Math.abs(value) / 8, 1);
      if (value >= 0) {
        return {
          backgroundColor: 'rgba(34, 197, 94, ' + (0.15 + intensity * 0.55) + ')',
          color: intensity > 0.4 ? '#fff' : '#16a34a',
        };
      } else {
        return {
          backgroundColor: 'rgba(239, 68, 68, ' + (0.15 + intensity * 0.55) + ')',
          color: intensity > 0.4 ? '#fff' : '#dc2626',
        };
      }
    }

    // ── Compare chart (TWR vs MWRR bar) ──

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

    // ── Preset / filter controls ──

    function selectPreset(key) {
      activePreset.value = key;
      nextTick(updateAllCharts);
    }

    function applyCustomRange() {
      activePreset.value = 'custom';
      nextTick(updateAllCharts);
    }

    watch(includeRealized, function () { nextTick(updateReturnChart); });

    // ── Instrument switching ──

    async function onInstrumentChange() {
      activePreset.value = 'all';
      if (selectedInstrument.value) {
        await fetchInstrumentHistory(selectedInstrument.value);
      } else {
        setPortfolioActive();
        await nextTick();
        updateAllCharts();
        if (periods.value.length) renderCompareChart(periods.value);
      }
    }

    function setPortfolioActive() {
      activeDates = portfolioDates;
      activeDrawdownPcts = portfolioDrawdownPcts;
    }

    function setInstrumentActive() {
      activeDates = instrumentDates;
      activeDrawdownPcts = instrumentDrawdownPcts;
    }

    // ── Data fetching ──

    async function fetchHistory() {
      try {
        var res = await fetch('/api/portfolio/history');
        var data = await res.json();
        portfolioDates = data.dates || [];
        portfolioValues = data.values || [];
        portfolioCosts = data.costs || [];
        portfolioReturnPcts = data.return_pcts || [];
        portfolioTotalReturnPcts = data.total_return_pcts || [];
        portfolioTwrPcts = data.twr_pcts || [];
        portfolioDrawdownPcts = data.drawdown_pcts || [];
        historyLoading.value = false;
        setPortfolioActive();
        await nextTick();
        updateAllCharts();
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

    async function fetchInstrumentNames() {
      try {
        var res = await fetch('/api/portfolio');
        var data = await res.json();
        instrumentNames.value = (data.instruments || []).map(function (i) { return i.security; });
      } catch (err) {
        console.error('Failed to fetch instrument names:', err);
      }
    }

    async function fetchInstrumentHistory(security) {
      historyLoading.value = true;
      try {
        var res = await fetch('/api/instruments/' + encodeURIComponent(security) + '/history');
        var data = await res.json();
        instrumentDates = data.dates || [];
        instrumentPrices = data.prices || [];
        instrumentCostAvg = data.cost_avg || [];
        instrumentPnl = data.pnl || [];
        instrumentDrawdownPcts = data.drawdown_pcts || [];
        historyLoading.value = false;
        setInstrumentActive();
        await nextTick();
        updateAllCharts();
      } catch (err) {
        console.error('Failed to fetch instrument history:', err);
        historyLoading.value = false;
      }
    }

    // ── Theme change ──

    function reRenderAll() {
      updateAllCharts();
      if (!selectedInstrument.value && periods.value.length) renderCompareChart(periods.value);
    }

    function onThemeChange() { nextTick(reRenderAll); }

    onMounted(function () {
      fetchInstrumentNames();
      fetchHistory();
      fetchPeriods();
      window.addEventListener('themechange', onThemeChange);
    });
    onUnmounted(function () { window.removeEventListener('themechange', onThemeChange); });

    return {
      historyLoading, periodsLoading, periods,
      instrumentNames, selectedInstrument, onInstrumentChange,
      compareChart, returnChart, valueCostChart, drawdownChart,
      includeRealized,
      activePreset, customFrom, customTo, presets,
      selectPreset, applyCustomRange,
      heatmapMonths, heatmapData, heatmapCellStyle,
      fmt, fmtSigned, pnlColor,
    };
  },
}).mount('#app');
