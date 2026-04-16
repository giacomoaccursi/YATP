/**
 * Vue app for the instruments page.
 */

const { createApp, ref, onMounted, nextTick } = Vue;

createApp({
  setup() {
    const loading = ref(true);
    const detailLoading = ref(false);
    const instruments = ref([]);
    const selected = ref(null);
    const priceChart = ref(null);
    const pnlChart = ref(null);
    let priceChartInstance = null;
    let pnlChartInstance = null;

    function makeLineChart(canvas, labels, datasets, existing, opts) {
      if (existing) existing.destroy();
      return new Chart(canvas, {
        type: 'line',
        data: { labels, datasets },
        options: {
          responsive: true,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: {
              labels: { color: '#d1d5db', usePointStyle: true, pointStyle: 'circle', font: { size: 11 } },
            },
            tooltip: {
              backgroundColor: '#1f2937',
              titleColor: '#f3f4f6',
              bodyColor: '#d1d5db',
              borderColor: '#374151',
              borderWidth: 1,
              padding: 10,
              cornerRadius: 8,
              callbacks: opts.tooltipCallbacks || {},
            },
          },
          scales: {
            x: {
              ticks: { color: '#6b7280', maxTicksLimit: 10 },
              grid: { color: 'rgba(75, 85, 99, 0.3)' },
            },
            y: {
              beginAtZero: opts.beginAtZero || false,
              ticks: { color: '#6b7280', callback: opts.yTickFormat || ((v) => v) },
              grid: { color: 'rgba(75, 85, 99, 0.3)' },
            },
          },
        },
      });
    }

    async function fetchData() {
      try {
        const res = await fetch('/api/portfolio');
        const data = await res.json();
        instruments.value = data.instruments;
        loading.value = false;
      } catch (err) {
        console.error('Failed to fetch instruments:', err);
        loading.value = false;
      }
    }

    async function selectInstrument(security) {
      selected.value = security;
      detailLoading.value = true;
      try {
        const res = await fetch('/api/instruments/' + encodeURIComponent(security) + '/history');
        const data = await res.json();
        detailLoading.value = false;
        await nextTick();
        renderDetailCharts(data);
      } catch (err) {
        console.error('Failed to fetch instrument history:', err);
        detailLoading.value = false;
      }
    }

    function renderDetailCharts(data) {
      if (!data.dates.length) return;

      // Price vs Avg Cost chart
      if (priceChart.value) {
        priceChartInstance = makeLineChart(
          priceChart.value,
          data.dates,
          [
            {
              label: 'Price',
              data: data.prices,
              borderColor: '#6366f1',
              backgroundColor: 'rgba(99, 102, 241, 0.1)',
              fill: false,
              tension: 0.3,
              pointRadius: 0,
              pointHitRadius: 10,
              borderWidth: 2,
            },
            {
              label: 'Avg Cost',
              data: data.cost_avg,
              borderColor: '#f59e0b',
              borderDash: [6, 3],
              fill: false,
              tension: 0.3,
              pointRadius: 0,
              pointHitRadius: 10,
              borderWidth: 2,
            },
          ],
          priceChartInstance,
          {
            tooltipCallbacks: { label: (ctx) => ctx.dataset.label + ': ' + fmt(ctx.parsed.y) + ' €' },
            yTickFormat: (v) => fmt(v) + ' €',
          },
        );
      }

      // P&L chart
      if (pnlChart.value) {
        const colors = data.pnl.map(v => v >= 0 ? 'rgba(34, 197, 94, 0.6)' : 'rgba(239, 68, 68, 0.6)');
        const borderColors = data.pnl.map(v => v >= 0 ? '#22c55e' : '#ef4444');
        pnlChartInstance = makeLineChart(
          pnlChart.value,
          data.dates,
          [{
            label: 'Unrealized P&L',
            data: data.pnl,
            borderColor: '#22d3ee',
            backgroundColor: (ctx) => {
              const val = ctx.raw;
              return val >= 0 ? 'rgba(34, 211, 238, 0.1)' : 'rgba(239, 68, 68, 0.1)';
            },
            fill: true,
            tension: 0.3,
            pointRadius: 0,
            pointHitRadius: 10,
            borderWidth: 2,
          }],
          pnlChartInstance,
          {
            beginAtZero: true,
            tooltipCallbacks: { label: (ctx) => fmtSigned(ctx.parsed.y) + ' €' },
            yTickFormat: (v) => fmtSigned(v) + ' €',
          },
        );
      }
    }

    onMounted(fetchData);

    return {
      loading, detailLoading, instruments, selected,
      priceChart, pnlChart,
      selectInstrument,
      fmt, fmtSigned, pnlColor,
    };
  },
}).mount('#app');
