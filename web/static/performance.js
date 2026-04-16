/**
 * Vue app for the performance page.
 */

const { createApp, ref, onMounted, onUnmounted, nextTick } = Vue;

createApp({
  setup() {
    const historyLoading = ref(true);
    const periodsLoading = ref(true);
    const periods = ref([]);
    const valueChart = ref(null);
    const periodChart = ref(null);
    let valueChartInstance = null;
    let periodChartInstance = null;
    let historyData = null;

    function renderValueChart(dates, values) {
      if (!valueChart.value || !dates.length) return;
      if (valueChartInstance) valueChartInstance.destroy();
      valueChartInstance = new Chart(valueChart.value, {
        type: 'line',
        data: {
          labels: dates,
          datasets: [{
            label: 'Portfolio Value (€)', data: values,
            borderColor: '#6366f1', backgroundColor: 'rgba(99, 102, 241, 0.1)',
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

    function renderPeriodChart(periodsData) {
      if (!periodChart.value) return;
      if (periodChartInstance) periodChartInstance.destroy();

      var available = periodsData.filter(function (p) { return p.available && p.twr != null; });
      if (!available.length) return;

      var labels = available.map(function (p) { return p.period; });
      var values = available.map(function (p) { return p.twr; });
      var colors = values.map(function (v) { return v >= 0 ? 'rgba(99, 102, 241, 0.7)' : 'rgba(239, 68, 68, 0.7)'; });
      var borderColors = values.map(function (v) { return v >= 0 ? '#6366f1' : '#ef4444'; });

      periodChartInstance = new Chart(periodChart.value, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{ label: 'TWR', data: values, backgroundColor: colors, borderColor: borderColors, borderWidth: 1, borderRadius: 6 }],
        },
        options: {
          responsive: true,
          plugins: {
            legend: { display: false },
            tooltip: chartTooltip({ label: function (ctx) { return fmtSigned(ctx.parsed.y) + '%'; } }),
          },
          scales: chartScales({ xGrid: false, yFormat: function (v) { return v + '%'; } }),
        },
      });
    }

    function reRenderAll() {
      if (historyData) renderValueChart(historyData.dates, historyData.values);
      if (periods.value.length) renderPeriodChart(periods.value);
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

    async function fetchPeriods() {
      try {
        var res = await fetch('/api/performance/periods');
        var data = await res.json();
        periods.value = data.periods;
        periodsLoading.value = false;
        await nextTick();
        renderPeriodChart(data.periods);
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
      valueChart, periodChart,
      fmt, fmtSigned, pnlColor,
    };
  },
}).mount('#app');
