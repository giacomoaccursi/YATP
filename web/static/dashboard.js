/**
 * Vue app for the dashboard page.
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
    const summary = ref(null);
    const rebalance = ref([]);
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
          cutout: '68%',
          plugins: {
            legend: {
              position: 'bottom',
              labels: { color: t.text, padding: 16, usePointStyle: true, pointStyle: 'circle', font: { size: 12 } },
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
        var responses = await Promise.all([fetch('/api/portfolio'), fetch('/api/rebalance')]);
        var portfolioData = await responses[0].json();
        summary.value = portfolioData.summary;
        rebalance.value = (await responses[1].json()).actions;
        loading.value = false;
        await nextTick();
        renderCharts();
        fetchHistory();
      } catch (err) {
        console.error('Failed to fetch data:', err);
        loading.value = false;
      }
    }

    async function fetchHistory() {
      try {
        var res = await fetch('/api/portfolio/history');
        historyData = await res.json();
        historyLoading.value = false;
        await nextTick();
        renderValueChart(historyData.dates, historyData.values);
      } catch (err) {
        console.error('Failed to fetch history:', err);
        historyLoading.value = false;
      }
    }

    async function refreshPrices() {
      loading.value = true;
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
      loading, historyLoading, summary, rebalance,
      allocChart, classChart, valueChart,
      fmt, fmtSigned, pnlColor, refreshPrices,
    };
  },
}).mount('#app');
