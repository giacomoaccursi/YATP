/**
 * Shared chart rendering utilities.
 * Used by dashboard.js, instruments.js, performance.js, rebalance.js.
 */

var CHART_COLORS = [
  '#6366f1', '#22d3ee', '#f59e0b', '#ef4444',
  '#a78bfa', '#34d399', '#fb923c', '#f472b6',
  '#38bdf8', '#a3e635',
];

/**
 * Create a line chart with standard options.
 * @param {HTMLCanvasElement} canvas - Canvas element
 * @param {string[]} labels - X-axis labels
 * @param {object[]} datasets - Chart.js dataset objects
 * @param {Chart|null} existing - Existing chart instance to destroy
 * @param {object} opts - Options: tooltipCallbacks, yTickFormat, beginAtZero, xMaxTicks
 * @returns {Chart} New chart instance
 */
function createLineChart(canvas, labels, datasets, existing, opts) {
  if (existing) existing.destroy();
  opts = opts || {};
  return new Chart(canvas, {
    type: 'line',
    data: { labels: labels, datasets: datasets },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          labels: { color: chartTheme().text, usePointStyle: true, pointStyle: 'circle', font: { size: 11 } },
        },
        tooltip: chartTooltip(opts.tooltipCallbacks || {}),
      },
      scales: chartScales({
        xMaxTicks: opts.xMaxTicks || 10,
        beginAtZero: opts.beginAtZero || false,
        yFormat: opts.yTickFormat,
      }),
    },
  });
}

/**
 * Create a doughnut chart with standard options.
 * @param {HTMLCanvasElement} canvas - Canvas element
 * @param {string[]} labels - Segment labels
 * @param {number[]} data - Segment values
 * @param {Chart|null} existing - Existing chart instance to destroy
 * @returns {Chart} New chart instance
 */
function createDoughnutChart(canvas, labels, data, existing) {
  if (existing) existing.destroy();
  var t = chartTheme();
  var total = data.reduce(function (a, b) { return a + b; }, 0);
  return new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: CHART_COLORS.slice(0, data.length),
        borderColor: t.doughnutBorder,
        borderWidth: 2,
        hoverOffset: 8,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '65%',
      plugins: {
        legend: {
          position: 'right',
          labels: { color: t.text, padding: 10, usePointStyle: true, pointStyle: 'circle', font: { size: 11 }, boxWidth: 8 },
        },
        tooltip: chartTooltip({
          label: function (ctx) {
            var pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
            return ' ' + ctx.label + ': ' + pct + '%';
          },
        }),
      },
    },
  });
}

/**
 * Create a gradient fill function for Chart.js datasets.
 * @param {string} colorRgb - RGB values, e.g. "99, 102, 241"
 * @param {number} topOpacity - Opacity at top (0-1)
 * @param {number} bottomOpacity - Opacity at bottom (0-1)
 * @returns {function} Chart.js backgroundColor function
 */
function gradientFill(colorRgb, topOpacity, bottomOpacity) {
  return function (context) {
    var chart = context.chart;
    var ctx = chart.ctx;
    var area = chart.chartArea;
    if (!area) return 'rgba(' + colorRgb + ', ' + topOpacity + ')';
    var gradient = ctx.createLinearGradient(0, area.top, 0, area.bottom);
    gradient.addColorStop(0, 'rgba(' + colorRgb + ', ' + topOpacity + ')');
    gradient.addColorStop(1, 'rgba(' + colorRgb + ', ' + bottomOpacity + ')');
    return gradient;
  };
}
