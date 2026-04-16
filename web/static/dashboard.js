/**
 * Vue app for the dashboard page.
 */

const CHART_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

const { createApp, ref, onMounted, nextTick } = Vue;

createApp({
  setup() {
    const loading = ref(true);
    const instruments = ref([]);
    const summary = ref(null);
    const rebalance = ref([]);
    const allocChart = ref(null);
    const classChart = ref(null);
    let allocChartInstance = null;
    let classChartInstance = null;

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
      } catch (err) {
        console.error('Failed to fetch data:', err);
        loading.value = false;
      }
    }

    async function refreshPrices() {
      loading.value = true;
      await fetch('/api/refresh', { method: 'POST' });
      await fetchData();
    }

    onMounted(fetchData);

    return {
      loading, instruments, summary, rebalance,
      allocChart, classChart,
      fmt, fmtSigned, pnlColor, refreshPrices,
    };
  },
}).mount('#app');
