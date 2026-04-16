/**
 * Vue app for the interactive rebalance page.
 */

const CHART_COLORS = [
  '#6366f1', '#22d3ee', '#f59e0b', '#ef4444',
  '#a78bfa', '#34d399', '#fb923c', '#f472b6',
];

const { createApp, ref, computed, watch, onMounted, nextTick } = Vue;

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

    const totalTarget = computed(() => {
      return Object.values(targets.value).reduce((a, b) => a + b, 0);
    });

    const computedActions = computed(() => {
      const totalValue = actions.value.reduce((sum, a) => sum + a.current_value, 0) + newInvestment.value;
      if (totalValue <= 0) return actions.value;

      return classes.value.map(cls => {
        const original = actions.value.find(a => a.asset_class === cls);
        const currentValue = original ? original.current_value : 0;
        const currentWeight = totalValue > 0 ? (currentValue / totalValue) * 100 : 0;
        const targetWeight = targets.value[cls] || 0;
        const targetValue = totalValue * (targetWeight / 100);
        return {
          asset_class: cls,
          current_value: currentValue,
          current_weight: currentWeight,
          target_weight: targetWeight,
          target_value: targetValue,
          difference: targetValue - currentValue,
        };
      });
    });

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
                  return ' ' + ctx.label + ': ' + pct + '% (' + fmt(ctx.parsed) + ' €)';
                },
              },
            },
          },
        },
      });
    }

    function renderCharts() {
      const computed = computedActions.value;
      if (!computed.length) return;

      const labels = computed.map(a => a.asset_class);
      const currentData = computed.map(a => Math.max(0, a.current_value));
      const afterData = computed.map(a => Math.max(0, a.target_value));

      if (currentChart.value) {
        currentChartInstance = renderDoughnut(currentChart.value, labels, currentData, currentChartInstance);
      }
      if (afterChart.value) {
        afterChartInstance = renderDoughnut(afterChart.value, labels, afterData, afterChartInstance);
      }
    }

    async function fetchData() {
      try {
        const res = await fetch('/api/rebalance');
        const data = await res.json();
        actions.value = data.actions;

        const cls = data.actions.map(a => a.asset_class);
        classes.value = cls;

        const tgt = {};
        for (const a of data.actions) {
          tgt[a.asset_class] = a.target_weight;
        }
        targets.value = tgt;

        loading.value = false;
        await nextTick();
        renderCharts();
      } catch (err) {
        console.error('Failed to fetch rebalance data:', err);
        loading.value = false;
      }
    }

    watch([targets, newInvestment], async () => {
      await nextTick();
      renderCharts();
    }, { deep: true });

    onMounted(fetchData);

    return {
      loading, actions, classes, targets, newInvestment,
      totalTarget, computedActions,
      currentChart, afterChart,
      fmt, fmtSigned, pnlColor,
    };
  },
}).mount('#app');
