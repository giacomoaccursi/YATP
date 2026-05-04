/**
 * Vue app for the instruments page.
 */

const { createApp, ref, onMounted, onUnmounted, nextTick } = Vue;

(async function () {
  const i18n = await createI18nInstance();

  const app = createApp({
  setup() {
    const loading = ref(true);
    const detailLoading = ref(false);
    const instruments = ref([]);
    const selected = ref(null);
    const priceChart = ref(null);
    const pnlChart = ref(null);
    const dcaChart = ref(null);
    const returnChart = ref(null);
    let priceChartInstance = null;
    let pnlChartInstance = null;
    let dcaChartInstance = null;
    let returnChartInstance = null;
    const lastDetailData = ref(null);

    function makeLineChart(canvas, labels, datasets, existing, opts) {
      return createLineChart(canvas, labels, datasets, existing, opts);
    }

    function renderDetailCharts(data) {
      if (!data.dates.length) return;

      // Build buy points for the price chart (scatter overlay)
      var buyPointData = [];
      if (data.buy_dates) {
        data.buy_dates.forEach(function (buyDate, idx) {
          var dateIdx = data.dates.indexOf(buyDate);
          if (dateIdx >= 0 && data.buy_prices[idx]) {
            buyPointData.push({ x: buyDate, y: data.buy_prices[idx] });
          }
        });
      }

      if (priceChart.value) {
        var datasets = [
          { label: 'Price', data: data.prices, borderColor: '#6366f1', backgroundColor: 'rgba(99, 102, 241, 0.1)', fill: false, tension: 0.3, pointRadius: 0, pointHitRadius: 10, borderWidth: 2 },
          { label: 'Avg Cost', data: data.cost_avg, borderColor: '#f59e0b', borderDash: [6, 3], fill: false, tension: 0.3, pointRadius: 0, pointHitRadius: 10, borderWidth: 2 },
        ];

        // Add buy markers as scatter points on the price line
        if (buyPointData.length) {
          var buyMarkerData = data.dates.map(function (date) {
            var match = buyPointData.find(function (bp) { return bp.x === date; });
            return match ? match.y : null;
          });
          datasets.push({
            label: 'Buy', data: buyMarkerData, borderColor: '#22c55e', backgroundColor: '#22c55e',
            pointRadius: 5, pointHoverRadius: 7, pointStyle: 'triangle',
            showLine: false, fill: false,
          });
        }

        priceChartInstance = makeLineChart(
          priceChart.value, data.dates, datasets, priceChartInstance,
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

      // Value vs Cost chart
      if (dcaChart.value && data.values && data.costs) {
        if (dcaChartInstance) dcaChartInstance.destroy();

        dcaChartInstance = makeLineChart(
          dcaChart.value, data.dates,
          [
            { label: 'Market Value', data: data.values, borderColor: '#6366f1', backgroundColor: function (context) {
              var chart = context.chart;
              var ctx = chart.ctx;
              var area = chart.chartArea;
              if (!area) return 'rgba(99, 102, 241, 0.1)';
              var gradient = ctx.createLinearGradient(0, area.top, 0, area.bottom);
              gradient.addColorStop(0, 'rgba(99, 102, 241, 0.2)');
              gradient.addColorStop(1, 'rgba(99, 102, 241, 0.0)');
              return gradient;
            }, fill: true, tension: 0.3, pointRadius: 0, pointHitRadius: 10, borderWidth: 2 },
            { label: 'Cost Basis', data: data.costs, borderColor: '#f59e0b', borderDash: [6, 3], fill: false, tension: 0.3, pointRadius: 0, pointHitRadius: 10, borderWidth: 2 },
          ],
          null,
          { tooltipCallbacks: { label: function (ctx) { return ctx.dataset.label + ': ' + fmt(ctx.parsed.y) + ' €'; } }, yTickFormat: function (v) { return fmt(v) + ' €'; } },
        );
      }

      // Return % chart (TWR)
      if (returnChart.value && data.twr_pcts) {
        if (returnChartInstance) returnChartInstance.destroy();

        returnChartInstance = makeLineChart(
          returnChart.value, data.dates,
          [{
            label: 'TWR', data: data.twr_pcts, borderColor: '#22d3ee',
            backgroundColor: function (context) {
              var chart = context.chart;
              var ctx = chart.ctx;
              var area = chart.chartArea;
              if (!area) return 'rgba(34, 211, 238, 0.1)';
              var gradient = ctx.createLinearGradient(0, area.top, 0, area.bottom);
              gradient.addColorStop(0, 'rgba(34, 211, 238, 0.2)');
              gradient.addColorStop(1, 'rgba(34, 211, 238, 0.0)');
              return gradient;
            },
            fill: true, tension: 0.3, pointRadius: 0, pointHitRadius: 10, borderWidth: 2,
          }],
          null,
          { beginAtZero: true, tooltipCallbacks: { label: function (ctx) { return 'TWR: ' + fmtSigned(ctx.parsed.y) + '%'; } }, yTickFormat: function (v) { return fmtSigned(v) + '%'; } },
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
        if (window.showFailedBanner) window.showFailedBanner(data);
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
        lastDetailData.value = await res.json();
        detailLoading.value = false;
        await nextTick();
        renderDetailCharts(lastDetailData.value);
      } catch (err) {
        console.error('Failed to fetch instrument history:', err);
        detailLoading.value = false;
      }
    }

    function onThemeChange() {
      if (lastDetailData.value) { nextTick(function () { renderDetailCharts(lastDetailData.value); }); }
    }

    onMounted(function () {
      fetchData();
      window.addEventListener('themechange', onThemeChange);
    });
    onUnmounted(function () { window.removeEventListener('themechange', onThemeChange); });

    return {
      loading, detailLoading, instruments, selected,
      priceChart, pnlChart, dcaChart, returnChart, selectInstrument,
      fmt, fmtSigned, pnlColor,
    };
  },
  });

  app.use(i18n);
  app.mount('#app');
})();
