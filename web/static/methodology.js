/**
 * Vue app for the methodology page.
 * Displays metric cards with formulas and detail modals.
 */

const { createApp, ref, computed, onMounted } = Vue;

(async function () {
  const i18n = await createI18nInstance();

  const app = createApp({
  setup() {
    const selectedMetric = ref(null);

    function renderFormula(latex) {
      try {
        return katex.renderToString(latex, { throwOnError: false, displayMode: true });
      } catch (e) {
        return '<code>' + latex + '</code>';
      }
    }

    function openMetric(metric) {
      selectedMetric.value = metric;
    }

    const categories = computed(function () {
      var t = i18n.global.t;
      return [
        {
          key: 'returns',
          label: t('methodology.cat_returns'),
          metrics: [
            {
              key: 'simple_return',
              name: t('methodology.m_simple_return'),
              tag: t('methodology.tag_basic'),
              formula: 'R = \\frac{V_{market} - C_{basis}}{C_{basis}} \\times 100',
              short: t('methodology.m_simple_return_short'),
              detail: t('methodology.m_simple_return_detail'),
              example: t('methodology.m_simple_return_example'),
            },
            {
              key: 'twr',
              name: 'TWR',
              tag: t('methodology.tag_advanced'),
              formula: 'TWR = \\prod_{i=1}^{n} \\frac{V_{before,i}}{V_{after,i-1}} - 1',
              short: t('methodology.m_twr_short'),
              detail: t('methodology.m_twr_detail'),
              example: t('methodology.m_twr_example'),
            },
            {
              key: 'xirr',
              name: 'XIRR / MWRR',
              tag: t('methodology.tag_advanced'),
              formula: '\\sum_{i=1}^{n} \\frac{CF_i}{(1+r)^{t_i}} = 0',
              short: t('methodology.m_xirr_short'),
              detail: t('methodology.m_xirr_detail'),
              example: t('methodology.m_xirr_example'),
            },
          ],
        },
        {
          key: 'risk',
          label: t('methodology.cat_risk'),
          metrics: [
            {
              key: 'volatility',
              name: t('methodology.m_volatility'),
              tag: t('methodology.tag_risk'),
              formula: '\\sigma = \\sqrt{\\frac{\\sum(r_i - \\bar{r})^2}{n-1}} \\times \\sqrt{252}',
              short: t('methodology.m_volatility_short'),
              detail: t('methodology.m_volatility_detail'),
              example: null,
            },
            {
              key: 'sharpe',
              name: 'Sharpe Ratio',
              tag: t('methodology.tag_risk'),
              formula: 'S = \\frac{R_p - R_f}{\\sigma_p}',
              short: t('methodology.m_sharpe_short'),
              detail: t('methodology.m_sharpe_detail'),
              example: t('methodology.m_sharpe_example'),
            },
            {
              key: 'sortino',
              name: 'Sortino Ratio',
              tag: t('methodology.tag_risk'),
              formula: 'So = \\frac{R_p - R_f}{\\sigma_{down}}',
              short: t('methodology.m_sortino_short'),
              detail: t('methodology.m_sortino_detail'),
              example: null,
            },
            {
              key: 'drawdown',
              name: 'Max Drawdown',
              tag: t('methodology.tag_risk'),
              formula: 'DD = \\frac{TWR_t - TWR_{peak}}{TWR_{peak}} \\times 100',
              short: t('methodology.m_drawdown_short'),
              detail: t('methodology.m_drawdown_detail'),
              example: null,
            },
          ],
        },
        {
          key: 'tax',
          label: t('methodology.cat_tax'),
          metrics: [
            {
              key: 'est_tax',
              name: t('methodology.m_est_tax'),
              tag: t('methodology.tag_tax'),
              formula: 'Tax = \\max(0,\\; V_{market} - C_{basis}) \\times rate',
              short: t('methodology.m_est_tax_short'),
              detail: t('methodology.m_est_tax_detail'),
              example: t('methodology.m_est_tax_example'),
            },
            {
              key: 'cost_basis',
              name: t('methodology.m_cost_basis'),
              tag: t('methodology.tag_basic'),
              formula: 'C_{basis} = \\sum Buy_i - \\sum \\frac{C_{basis}}{shares} \\times sold_i',
              short: t('methodology.m_cost_basis_short'),
              detail: t('methodology.m_cost_basis_detail'),
              example: null,
            },
          ],
        },
      ];
    });

    return {
      categories, selectedMetric, openMetric, renderFormula,
    };
  },
  });

  app.use(i18n);
  app.mount('#app');
})();
