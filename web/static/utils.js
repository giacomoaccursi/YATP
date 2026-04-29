/**
 * Shared utility functions for the portfolio dashboard.
 */

/** Format a number with 2 decimal places. */
function fmt(n) {
  return n != null
    ? n.toLocaleString('en', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : 'N/A';
}

/** Format a number with sign prefix. */
function fmtSigned(n) {
  if (n == null) return 'N/A';
  const sign = n >= 0 ? '+' : '';
  return sign + n.toLocaleString('en', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** Return Tailwind color class based on positive/negative value. */
function pnlColor(val) {
  if (val == null) return 'text-gray-400';
  return val >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400';
}

/** Get current chart theme colors (delegates to theme.js). */
function chartTheme() {
  return window.__chartTheme ? window.__chartTheme() : {
    text: '#d1d5db', textMuted: '#6b7280',
    grid: 'rgba(75, 85, 99, 0.3)',
    tooltipBg: '#1f2937', tooltipTitle: '#f3f4f6',
    tooltipBody: '#d1d5db', tooltipBorder: '#374151',
    doughnutBorder: '#111827',
  };
}

/** Build standard Chart.js tooltip config using current theme. */
function chartTooltip(callbacks) {
  var t = chartTheme();
  return {
    backgroundColor: t.tooltipBg,
    titleColor: t.tooltipTitle,
    bodyColor: t.tooltipBody,
    borderColor: t.tooltipBorder,
    borderWidth: 1,
    padding: 10,
    cornerRadius: 8,
    callbacks: callbacks || {},
  };
}

/** Build standard Chart.js scale config using current theme. */
function chartScales(opts) {
  var t = chartTheme();
  return {
    x: {
      ticks: { color: t.textMuted, maxTicksLimit: opts.xMaxTicks || 12, maxRotation: 45, minRotation: 25 },
      grid: opts.xGrid === false ? { display: false } : { color: t.grid },
    },
    y: {
      beginAtZero: opts.beginAtZero || false,
      ticks: { color: t.textMuted, callback: opts.yFormat || function (v) { return v; } },
      grid: { color: t.grid },
    },
  };
}

/** Fetch net transaction value from backend. Returns string. */
async function fetchNetValue(form) {
  try {
    var res = await fetch('/api/transactions/net-value', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type: form.type,
        shares: form.shares,
        quote: form.quote,
        fees: form.fees,
        taxes: form.taxes,
      }),
    });
    var data = await res.json();
    return String(data.net_transaction_value);
  } catch (err) {
    return '0.00';
  }
}

/** Create a default empty transaction form. */
function createEmptyForm() {
  return {
    date: new Date().toISOString().split('T')[0],
    type: 'Buy',
    security: '',
    shares: '',
    quote: '',
    fees: '',
    taxes: '',
    accrued_interest: '',
    net_transaction_value: '',
  };
}

/** Submit a transaction to the API. Returns {ok, message}. */
async function submitTransactionToApi(form, computedNetValue) {
  const res = await fetch('/api/transactions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...form, net_transaction_value: computedNetValue }),
  });
  const data = await res.json();
  if (res.ok) {
    return { ok: true, message: 'Transaction added successfully' };
  }
  return { ok: false, message: data.error || 'Failed to add transaction' };
}

/** Update an existing transaction by row index. Returns {ok, message}. */
async function updateTransactionApi(rowIndex, form, computedNetValue) {
  const res = await fetch('/api/transactions/' + rowIndex, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...form, net_transaction_value: computedNetValue }),
  });
  const data = await res.json();
  if (res.ok) {
    return { ok: true, message: 'Transaction updated successfully' };
  }
  return { ok: false, message: data.error || 'Failed to update transaction' };
}
