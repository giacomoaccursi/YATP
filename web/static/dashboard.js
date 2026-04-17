/**
 * Vue app for the dashboard page.
 * Loads offline data first (always available), then market data (may fail).
 */

const CHART_COLORS = [
  '#6366f1', '#22d3ee', '#f59e0b', '#ef4444',
  '#a78bfa', '#34d399', '#fb923c', '#f472b6',
  '#38bdf8', '#a3e635',
];

const { createApp, ref, onMounted, onUnmounted, nextTick } = Vue;

createApp({
  setup() {
    const loading = ref(true);
    const historyLoading = ref(true);
    const historyError = ref(null);
    const marketError = ref(null);
    const failedInstruments = ref([]);
    const summary = ref(null);
    const offline = ref(null);
    const dailyChange = ref(null);
    const allocChart = ref(null);
    const classChart = ref(null);
    const valueChart = ref(null);
    let allocChartInstance = null;
    let classChartInstance = null;
    let valueChartInstance = null;
    let historyData = null;

    function renderDoughnut(canvas, labels, data, existing) {
      if (existing) existing.destroy();
      var t = chartTheme();
      var total = data.reduce(function (a, b) { return a + b; }, 0);
      return new Chart(canvas, {
        type: 'doughnut',
        data: {
          labels: labels,
          datasets: [{
            data: data,
            backgroundColor: CHART_COLORS.slice(0, data.length),
            borderColor: t.doughnutBorder,
            borderWidth: 2,
            hoverOffset: 8,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '65%',
          plugins: {
            legend: {
              position: 'right',
              labels: { color: t.text, padding: 10, usePointStyle: true, pointStyle: 'circle', font: { size: 11 }, boxWidth: 8 },
            },
            tooltip: chartTooltip({
              label: function (ctx) {
                var pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                return ' ' + ctx.label + ': ' + pct + '%';
              },
            }),
          },
        },
      });
    }

    function renderCharts() {
      if (!summary.value) return;
      if (allocChart.value) {
        allocChartInstance = renderDoughnut(
          allocChart.value,
          Object.keys(summary.value.allocations),
          Object.values(summary.value.allocations),
          allocChartInstance,
        );
      }
      if (classChart.value) {
        classChartInstance = renderDoughnut(
          classChart.value,
          Object.keys(summary.value.allocations_by_class),
          Object.values(summary.value.allocations_by_class),
          classChartInstance,
        );
      }
    }

    function renderValueChart(dates, values) {
      if (!valueChart.value || !dates.length) return;
      if (valueChartInstance) valueChartInstance.destroy();
      valueChartInstance = new Chart(valueChart.value, {
        type: 'line',
        data: {
          labels: dates,
          datasets: [{
            label: 'Portfolio Value (€)',
            data: values,
            borderColor: '#6366f1',
            backgroundColor: 'rgba(99, 102, 241, 0.1)',
            fill: true, tension: 0.3, pointRadius: 0, pointHitRadius: 10, borderWidth: 2,
          }],
        },
        options: {
          responsive: true,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: { display: false },
            tooltip: chartTooltip({ label: function (ctx) { return fmt(ctx.parsed.y) + ' €'; } }),
          },
          scales: chartScales({ beginAtZero: true, yFormat: function (v) { return fmt(v) + ' €'; } }),
        },
      });
    }

    function reRenderAll() {
      renderCharts();
      if (historyData) renderValueChart(historyData.dates, historyData.values);
    }

    async function fetchData() {
      try {
        var res = await fetch('/api/portfolio');
        var data = await res.json();

        // Offline data always available
        offline.value = data.offline;

        // Market data may be null
        summary.value = data.summary;
        dailyChange.value = data.daily_change;
        marketError.value = data.market_error;
        failedInstruments.value = data.failed_instruments || [];

        loading.value = false;
        await nextTick();
        renderCharts();
        fetchHistory();
      } catch (err) {
        console.error('Failed to fetch data:', err);
        marketError.value = 'Unable to connect to server';
        loading.value = false;
      }
    }

    async function fetchHistory() {
      try {
        var res = await fetch('/api/portfolio/history');
        var data = await res.json();
        if (data.dates && data.dates.length) {
          historyData = data;
          historyLoading.value = false;
          await nextTick();
          renderValueChart(data.dates, data.values);
        } else {
          historyError.value = 'No history data available';
          historyLoading.value = false;
        }
      } catch (err) {
        console.error('Failed to fetch history:', err);
        historyError.value = 'Unable to load market data';
        historyLoading.value = false;
      }
    }

    async function refreshPrices() {
      loading.value = true;
      marketError.value = null;
      historyError.value = null;
      historyLoading.value = true;
      await fetch('/api/refresh', { method: 'POST' });
      await fetchData();
    }

    function onThemeChange() { nextTick(reRenderAll); }

    onMounted(function () {
      fetchData();
      window.addEventListener('themechange', onThemeChange);
    });
    onUnmounted(function () { window.removeEventListener('themechange', onThemeChange); });

    return {
      loading, historyLoading, historyError, marketError, failedInstruments,
      summary, offline, dailyChange,
      allocChart, classChart, valueChart,
      fmt, fmtSigned, pnlColor, refreshPrices,
    };
  },
}).mount('#app');
