/**
 * Vue app for the dashboard page.
 */

const CHART_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

const { createApp, ref, onMounted, nextTick } = Vue;

createApp({
  setup() {
    const loading = ref(true);
    const historyLoading = ref(true);
    const instruments = ref([]);
    const summary = ref(null);
    const rebalance = ref([]);
    const allocChart = ref(null);
    const classChart = ref(null);
    const valueChart = ref(null);
    let allocChartInstance = null;
    let classChartInstance = null;
    let valueChartInstance = null;

    function renderDoughnut(canvas, labels, data, existing) {
      if (existing) existing.destroy();
      return new Chart(canvas, {
        type: 'doughnut',
        data: {
          labels,
          datasets: [{ data, backgroundColor: CHART_COLORS.slice(0, data.length), borderWidth: 0 }],
        },
        options: {
          responsive: true,
          plugins: { legend: { position: 'bottom', labels: { color: '#9ca3af', padding: 16 } } },
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
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            fill: true,
            tension: 0.3,
            pointRadius: 0,
            pointHitRadius: 10,
            borderWidth: 2,
          }],
        },
        options: {
          responsive: true,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx) => fmt(ctx.parsed.y) + ' €',
              },
            },
          },
          scales: {
            x: {
              ticks: { color: '#6b7280', maxTicksLimit: 12 },
              grid: { color: 'rgba(75, 85, 99, 0.3)' },
            },
            y: {
              ticks: { color: '#6b7280', callback: (v) => fmt(v) + ' €' },
              grid: { color: 'rgba(75, 85, 99, 0.3)' },
            },
          },
        },
      });
    }

    async function fetchData() {
      try {
        const [portfolioRes, rebalanceRes] = await Promise.all([
          fetch('/api/portfolio'),
          fetch('/api/rebalance'),
        ]);
        const portfolioData = await portfolioRes.json();
        instruments.value = portfolioData.instruments;
        summary.value = portfolioData.summary;
        rebalance.value = (await rebalanceRes.json()).actions;
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
        historyLoading.value = true;
        const res = await fetch('/api/portfolio/history');
        const data = await res.json();
        historyLoading.value = false;
        await nextTick();
        renderValueChart(data.dates, data.values);
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

    onMounted(fetchData);

    return {
      loading, historyLoading, instruments, summary, rebalance,
      allocChart, classChart, valueChart,
      fmt, fmtSigned, pnlColor, refreshPrices,
    };
  },
}).mount('#app');
