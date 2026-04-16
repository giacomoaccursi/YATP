/**
 * Vue app for the interactive rebalance page.
 * No business logic — all calculations done by /api/rebalance/simulate.
 */

const CHART_COLORS = [
  '#6366f1', '#22d3ee', '#f59e0b', '#ef4444',
  '#a78bfa', '#34d399', '#fb923c', '#f472b6',
];

const { createApp, ref, computed, watch, onMounted, onUnmounted, nextTick } = Vue;

createApp({
  setup() {
    const loading = ref(true);
    const simulatedActions = ref([]);
    const classes = ref([]);
    const targets = ref({});
    const newInvestment = ref(0);
    const currentChart = ref(null);
    const afterChart = ref(null);
    let currentChartInstance = null;
    let afterChartInstance = null;
    let debounceTimer = null;

    const totalTarget = computed(function () {
      return Object.values(targets.value).reduce(function (a, b) { return a + b; }, 0);
    });

    function renderDoughnut(canvas, labels, data, existing) {
      if (existing) existing.destroy();
      var t = chartTheme();
      return new Chart(canvas, {
        type: 'doughnut',
        data: {
          labels: labels,
          datasets: [{ data: data, backgroundColor: CHART_COLORS.slice(0, data.length), borderColor: t.doughnutBorder, borderWidth: 2, hoverOffset: 8 }],
        },
        options: {
          responsive: true, cutout: '68%',
          plugins: {
            legend: { position: 'bottom', labels: { color: t.text, padding: 16, usePointStyle: true, pointStyle: 'circle', font: { size: 12 } } },
            tooltip: chartTooltip(),
          },
        },
      });
    }

    function renderCharts() {
      var rows = simulatedActions.value;
      if (!rows.length) return;
      var labels = rows.map(function (a) { return a.asset_class; });
      var currentData = rows.map(function (a) { return a.current_value > 0 ? a.current_value : 0; });
      var afterData = rows.map(function (a) { return a.target_value > 0 ? a.target_value : 0; });
      if (currentChart.value) currentChartInstance = renderDoughnut(currentChart.value, labels, currentData, currentChartInstance);
      if (afterChart.value) afterChartInstance = renderDoughnut(afterChart.value, labels, afterData, afterChartInstance);
    }

    async function fetchSimulation() {
      try {
        var res = await fetch('/api/rebalance/simulate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ new_investment: newInvestment.value, targets: targets.value }),
        });
        var data = await res.json();
        simulatedActions.value = data.actions;
        await nextTick();
        renderCharts();
      } catch (err) {
        console.error('Failed to simulate rebalance:', err);
      }
    }

    function debouncedSimulate() {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(fetchSimulation, 200);
    }

    async function fetchInitialData() {
      try {
        var res = await fetch('/api/rebalance');
        var data = await res.json();
        simulatedActions.value = data.actions;
        classes.value = data.actions.map(function (a) { return a.asset_class; });
        var tgt = {};
        data.actions.forEach(function (a) { tgt[a.asset_class] = a.target_weight; });
        targets.value = tgt;
        loading.value = false;
        await nextTick();
        renderCharts();
      } catch (err) {
        console.error('Failed to fetch rebalance data:', err);
        loading.value = false;
      }
    }

    watch([targets, newInvestment], debouncedSimulate, { deep: true });

    function onThemeChange() { nextTick(renderCharts); }

    onMounted(function () {
      fetchInitialData();
      window.addEventListener('themechange', onThemeChange);
    });
    onUnmounted(function () { window.removeEventListener('themechange', onThemeChange); });

    return {
      loading, simulatedActions, classes, targets, newInvestment,
      totalTarget, currentChart, afterChart,
      fmt, fmtSigned, pnlColor,
    };
  },
}).mount('#app');
