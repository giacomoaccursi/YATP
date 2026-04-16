/**
 * Vue app for the performance page.
 */

const { createApp, ref, onMounted, nextTick } = Vue;

createApp({
  setup() {
    const historyLoading = ref(true);
    const periodsLoading = ref(true);
    const periods = ref([]);
    const valueChart = ref(null);
    const periodChart = ref(null);
    let valueChartInstance = null;
    let periodChartInstance = null;

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
              backgroundColor: '#1f2937',
              titleColor: '#f3f4f6',
              bodyColor: '#d1d5db',
              borderColor: '#374151',
              borderWidth: 1,
              padding: 10,
              cornerRadius: 8,
              callbacks: { label: (ctx) => fmt(ctx.parsed.y) + ' €' },
            },
          },
          scales: {
            x: {
              ticks: { color: '#6b7280', maxTicksLimit: 12 },
              grid: { color: 'rgba(75, 85, 99, 0.3)' },
            },
            y: {
              beginAtZero: true,
              ticks: { color: '#6b7280', callback: (v) => fmt(v) + ' €' },
              grid: { color: 'rgba(75, 85, 99, 0.3)' },
            },
          },
        },
      });
    }

    function renderPeriodChart(periodsData) {
      if (!periodChart.value) return;
      if (periodChartInstance) periodChartInstance.destroy();

      const available = periodsData.filter(p => p.available && p.twr != null);
      if (!available.length) return;

      const labels = available.map(p => p.period);
      const values = available.map(p => p.twr);
      const colors = values.map(v => v >= 0 ? 'rgba(99, 102, 241, 0.7)' : 'rgba(239, 68, 68, 0.7)');
      const borderColors = values.map(v => v >= 0 ? '#6366f1' : '#ef4444');

      periodChartInstance = new Chart(periodChart.value, {
        type: 'bar',
        data: {
          labels,
          datasets: [{
            label: 'TWR',
            data: values,
            backgroundColor: colors,
            borderColor: borderColors,
            borderWidth: 1,
            borderRadius: 6,
          }],
        },
        options: {
          responsive: true,
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: '#1f2937',
              titleColor: '#f3f4f6',
              bodyColor: '#d1d5db',
              borderColor: '#374151',
              borderWidth: 1,
              padding: 10,
              cornerRadius: 8,
              callbacks: { label: (ctx) => fmtSigned(ctx.parsed.y) + '%' },
            },
          },
          scales: {
            x: {
              ticks: { color: '#6b7280' },
              grid: { display: false },
            },
            y: {
              ticks: { color: '#6b7280', callback: (v) => v + '%' },
              grid: { color: 'rgba(75, 85, 99, 0.3)' },
            },
          },
        },
      });
    }

    async function fetchHistory() {
      try {
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

    async function fetchPeriods() {
      try {
        const res = await fetch('/api/performance/periods');
        const data = await res.json();
        periods.value = data.periods;
        periodsLoading.value = false;
        await nextTick();
        renderPeriodChart(data.periods);
      } catch (err) {
        console.error('Failed to fetch periods:', err);
        periodsLoading.value = false;
      }
    }

    onMounted(() => {
      fetchHistory();
      fetchPeriods();
    });

    return {
      historyLoading, periodsLoading, periods,
      valueChart, periodChart,
      fmt, fmtSigned, pnlColor,
    };
  },
}).mount('#app');
