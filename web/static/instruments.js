/**
 * Vue app for the instruments page.
 */

const { createApp, ref, onMounted, onUnmounted, nextTick } = Vue;

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
    let lastDetailData = null;

    function makeLineChart(canvas, labels, datasets, existing, opts) {
      if (existing) existing.destroy();
      var t = chartTheme();
      return new Chart(canvas, {
        type: 'line',
        data: { labels: labels, datasets: datasets },
        options: {
          responsive: true,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: {
              labels: { color: t.text, usePointStyle: true, pointStyle: 'circle', font: { size: 11 } },
            },
            tooltip: chartTooltip(opts.tooltipCallbacks || {}),
          },
          scales: chartScales({
            xMaxTicks: 10,
            beginAtZero: opts.beginAtZero || false,
            yFormat: opts.yTickFormat,
          }),
        },
      });
    }

    function renderDetailCharts(data) {
      if (!data.dates.length) return;

      if (priceChart.value) {
        priceChartInstance = makeLineChart(
          priceChart.value, data.dates,
          [
            { label: 'Price', data: data.prices, borderColor: '#6366f1', backgroundColor: 'rgba(99, 102, 241, 0.1)', fill: false, tension: 0.3, pointRadius: 0, pointHitRadius: 10, borderWidth: 2 },
            { label: 'Avg Cost', data: data.cost_avg, borderColor: '#f59e0b', borderDash: [6, 3], fill: false, tension: 0.3, pointRadius: 0, pointHitRadius: 10, borderWidth: 2 },
          ],
          priceChartInstance,
          { tooltipCallbacks: { label: function (ctx) { return ctx.dataset.label + ': ' + fmt(ctx.parsed.y) + ' €'; } }, yTickFormat: function (v) { return fmt(v) + ' €'; } },
        );
      }

      if (pnlChart.value) {
        pnlChartInstance = makeLineChart(
          pnlChart.value, data.dates,
          [{
            label: 'Unrealized P&L', data: data.pnl, borderColor: '#22d3ee',
            backgroundColor: function (ctx) { return ctx.raw >= 0 ? 'rgba(34, 211, 238, 0.1)' : 'rgba(239, 68, 68, 0.1)'; },
            fill: true, tension: 0.3, pointRadius: 0, pointHitRadius: 10, borderWidth: 2,
          }],
          pnlChartInstance,
          { beginAtZero: true, tooltipCallbacks: { label: function (ctx) { return fmtSigned(ctx.parsed.y) + ' €'; } }, yTickFormat: function (v) { return fmtSigned(v) + ' €'; } },
        );
      }
    }

    async function fetchData() {
      try {
        var res = await fetch('/api/portfolio');
        var data = await res.json();
        instruments.value = data.instruments;
        loading.value = false;
        if (window.__updateNavTimestamp) window.__updateNavTimestamp();
      } catch (err) {
        console.error('Failed to fetch instruments:', err);
        loading.value = false;
      }
    }

    async function selectInstrument(security) {
      selected.value = security;
      detailLoading.value = true;
      try {
        var res = await fetch('/api/instruments/' + encodeURIComponent(security) + '/history');
        lastDetailData = await res.json();
        detailLoading.value = false;
        await nextTick();
        renderDetailCharts(lastDetailData);
      } catch (err) {
        console.error('Failed to fetch instrument history:', err);
        detailLoading.value = false;
      }
    }

    function onThemeChange() {
      if (lastDetailData) { nextTick(function () { renderDetailCharts(lastDetailData); }); }
    }

    onMounted(function () {
      fetchData();
      window.addEventListener('themechange', onThemeChange);
    });
    onUnmounted(function () { window.removeEventListener('themechange', onThemeChange); });

    return {
      loading, detailLoading, instruments, selected,
      priceChart, pnlChart, selectInstrument,
      fmt, fmtSigned, pnlColor,
    };
  },
}).mount('#app');
