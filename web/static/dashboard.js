/**
 * Vue app for the dashboard page.
 */

const CHART_COLORS = [
  '#6366f1', '#22d3ee', '#f59e0b', '#ef4444',
  '#a78bfa', '#34d399', '#fb923c', '#f472b6',
  '#38bdf8', '#a3e635',
];

const { createApp, ref, onMounted, nextTick } = Vue;

createApp({
  setup() {
    const loading = ref(true);
    const summary = ref(null);
    const rebalance = ref([]);
    const allocChart = ref(null);
    const classChart = ref(null);
    let allocChartInstance = null;
    let classChartInstance = null;

    function renderDoughnut(canvas, labels, data, existing) {
      if (existing) existing.destroy();
      const total = data.reduce((a, b) => a + b, 0);
      return new Chart(canvas, {
        type: 'doughnut',
        data: {
          labels,
          datasets: [{
            data,
            backgroundColor: CHART_COLORS.slice(0, data.length),
            borderColor: '#111827',
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
              labels: {
                color: '#d1d5db',
                padding: 16,
                usePointStyle: true,
                pointStyle: 'circle',
                font: { size: 12 },
              },
            },
            tooltip: {
              backgroundColor: '#1f2937',
              titleColor: '#f3f4f6',
              bodyColor: '#d1d5db',
              borderColor: '#374151',
              borderWidth: 1,
              padding: 12,
              cornerRadius: 8,
              callbacks: {
                label: (ctx) => {
                  const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                  return ' ' + ctx.label + ': ' + pct + '%';
                },
              },
            },
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

    async function fetchData() {
      try {
        const [portfolioRes, rebalanceRes] = await Promise.all([
          fetch('/api/portfolio'),
          fetch('/api/rebalance'),
        ]);
        const portfolioData = await portfolioRes.json();
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
      loading, summary, rebalance,
      allocChart, classChart,
      fmt, fmtSigned, pnlColor, refreshPrices,
    };
  },
}).mount('#app');
