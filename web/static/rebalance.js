/**
 * Vue app for the interactive rebalance page.
 */

const CHART_COLORS = [
  '#6366f1', '#22d3ee', '#f59e0b', '#ef4444',
  '#a78bfa', '#34d399', '#fb923c', '#f472b6',
];

const { createApp, ref, computed, watch, onMounted, onUnmounted, nextTick } = Vue;

createApp({
  setup() {
    const loading = ref(true);
    const actions = ref([]);
    const classes = ref([]);
    const targets = ref({});
    const newInvestment = ref(0);
    const currentChart = ref(null);
    const afterChart = ref(null);
    let currentChartInstance = null;
    let afterChartInstance = null;

    const totalTarget = computed(function () {
      return Object.values(targets.value).reduce(function (a, b) { return a + b; }, 0);
    });

    const computedActions = computed(function () {
      var totalValue = actions.value.reduce(function (sum, a) { return sum + a.current_value; }, 0) + newInvestment.value;
      if (totalValue <= 0) return actions.value;

      return classes.value.map(function (cls) {
        var original = actions.value.find(function (a) { return a.asset_class === cls; });
        var currentValue = original ? original.current_value : 0;
        var currentWeight = totalValue > 0 ? (currentValue / totalValue) * 100 : 0;
        var targetWeight = targets.value[cls] || 0;
        var targetValue = totalValue * (targetWeight / 100);
        return {
          asset_class: cls, current_value: currentValue, current_weight: currentWeight,
          target_weight: targetWeight, target_value: targetValue, difference: targetValue - currentValue,
        };
      });
    });

    function renderDoughnut(canvas, labels, data, existing) {
      if (existing) existing.destroy();
      var t = chartTheme();
      var total = data.reduce(function (a, b) { return a + b; }, 0);
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
            tooltip: chartTooltip({
              label: function (ctx) {
                var pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                return ' ' + ctx.label + ': ' + pct + '% (' + fmt(ctx.parsed) + ' €)';
              },
            }),
          },
        },
      });
    }

    function renderCharts() {
      var rows = computedActions.value;
      if (!rows.length) return;
      var labels = rows.map(function (a) { return a.asset_class; });
      var currentData = rows.map(function (a) { return Math.max(0, a.current_value); });
      var afterData = rows.map(function (a) { return Math.max(0, a.target_value); });
      if (currentChart.value) currentChartInstance = renderDoughnut(currentChart.value, labels, currentData, currentChartInstance);
      if (afterChart.value) afterChartInstance = renderDoughnut(afterChart.value, labels, afterData, afterChartInstance);
    }

    async function fetchData() {
      try {
        var res = await fetch('/api/rebalance');
        var data = await res.json();
        actions.value = data.actions;
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

    watch([targets, newInvestment], function () { nextTick(renderCharts); }, { deep: true });

    function onThemeChange() { nextTick(renderCharts); }

    onMounted(function () {
      fetchData();
      window.addEventListener('themechange', onThemeChange);
    });
    onUnmounted(function () { window.removeEventListener('themechange', onThemeChange); });

    return {
      loading, actions, classes, targets, newInvestment,
      totalTarget, computedActions, currentChart, afterChart,
      fmt, fmtSigned, pnlColor,
    };
  },
}).mount('#app');
