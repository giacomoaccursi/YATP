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
  return val >= 0 ? 'text-green-400' : 'text-red-400';
}

/** Compute net transaction value from form fields. */
function computeNetValue(form) {
  const shares = parseFloat(form.shares) || 0;
  const quote = parseFloat(form.quote) || 0;
  const fees = parseFloat(form.fees) || 0;
  const taxes = parseFloat(form.taxes) || 0;
  const amount = shares * quote;

  if (form.type === 'Buy') return (amount + fees).toFixed(2);
  if (form.type === 'Sell') return (amount - fees - taxes).toFixed(2);
  return form.net_transaction_value || '0.00';
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
