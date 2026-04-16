/**
 * Vue app for the performance page.
 */

const { createApp, ref, computed, onMounted, onUnmounted, nextTick } = Vue;

createApp({
  setup() {
    const historyLoading = ref(true);
    const periodsLoading = ref(true);
    const periods = ref([]);
    const compareChart = ref(null);
    const returnChart = ref(null);
    let compareChartInstance = null;
    let returnChartInstance = null;

    // Full history data (fetched once)
    let allDates = [];
    let allValues = [];
    let allCosts = [];

    // Period filter state
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

    const periodSummary = ref(null);

    function getFilteredRange() {
      if (!allDates.length) return { dates: [], values: [], costs: [] };

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

      var dates = [];
      var values = [];
      var costs = [];
      for (var i = 0; i < allDates.length; i++) {
        if (allDates[i] >= fromDate && allDates[i] <= toDate) {
          dates.push(allDates[i]);
          values.push(allValues[i]);
          costs.push(allCosts[i]);
        }
      }
      return { dates: dates, values: values, costs: costs };
    }

    function computeCumulativeReturn(values) {
      if (!values.length || values[0] === 0) return [];
      var base = values[0];
      return values.map(function (v) { return base > 0 ? ((v - base) / base) * 100 : 0; });
    }

    function updateReturnChart() {
      var range = getFilteredRange();
      if (!range.dates.length) {
        periodSummary.value = null;
        return;
      }

      var cumReturn = computeCumulativeReturn(range.values);

      // Period summary
      var startVal = range.values[0];
      var endVal = range.values[range.values.length - 1];
      var gain = endVal - startVal;
      var returnPct = startVal > 0 ? ((endVal - startVal) / startVal) * 100 : 0;
      periodSummary.value = {
        startValue: startVal,
        endValue: endVal,
        gain: Math.round(gain * 100) / 100,
        returnPct: Math.round(returnPct * 100) / 100,
      };

      renderReturnChart(range.dates, cumReturn);
    }

    function renderReturnChart(dates, cumReturn) {
      if (!returnChart.value || !dates.length) return;
      if (returnChartInstance) returnChartInstance.destroy();

      returnChartInstance = new Chart(returnChart.value, {
        type: 'line',
        data: {
          labels: dates,
          datasets: [{
            label: 'Cumulative Return (%)',
            data: cumReturn,
            borderColor: '#6366f1',
            backgroundColor: function (ctx) {
              if (!ctx.raw && ctx.raw !== 0) return 'transparent';
              return ctx.raw >= 0 ? 'rgba(99, 102, 241, 0.1)' : 'rgba(239, 68, 68, 0.1)';
            },
            fill: true, tension: 0.3, pointRadius: 0, pointHitRadius: 10, borderWidth: 2,
          }],
        },
        options: {
          responsive: true,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: { display: false },
            tooltip: chartTooltip({ label: function (ctx) { return fmtSigned(ctx.parsed.y) + '%'; } }),
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
            {
              label: 'TWR',
              data: twrValues,
              backgroundColor: 'rgba(99, 102, 241, 0.7)',
              borderColor: '#6366f1',
              borderWidth: 1,
              borderRadius: 4,
            },
            {
              label: 'MWRR',
              data: mwrrValues,
              backgroundColor: 'rgba(34, 211, 238, 0.7)',
              borderColor: '#22d3ee',
              borderWidth: 1,
              borderRadius: 4,
            },
          ],
        },
        options: {
          responsive: true,
          plugins: {
            legend: {
              labels: { color: chartTheme().text, usePointStyle: true, pointStyle: 'circle', font: { size: 11 } },
            },
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
        allValues = data.values;
        allCosts = data.costs || [];
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
      compareChart, returnChart,
      activePreset, customFrom, customTo, presets,
      periodSummary,
      selectPreset, applyCustomRange,
      fmt, fmtSigned, pnlColor,
    };
  },
}).mount('#app');
