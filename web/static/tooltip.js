/**
 * Info tooltip definitions. Maps field keys to explanations.
 * Renders a ? icon in the top-right corner of the parent element.
 */
(function () {
  var definitions = {
    'cost-basis': 'Total amount invested across all instruments, net of accrued interest for bonds.',
    'market-value': 'Total current value of all holdings at today\'s market prices.',
    'total-pnl': 'Total profit or loss: unrealized (current holdings) + realized (from past sales). Income shown separately.',
    'income': 'Total dividends and bond coupons received since inception.',
    'simple-return': 'Percentage gain or loss relative to total cost basis. Does not account for timing of cash flows.',
    'xirr': 'Annualized money-weighted return (XIRR). Accounts for the timing and size of each cash flow.',
    'twr': 'Time-Weighted Return. Measures portfolio performance independent of cash flow timing.',
    'mwrr': 'Money-Weighted Return for the period. Reflects the actual return experienced by the investor.',
    'unrealized': 'Gain or loss on positions you still hold. Only realized when you sell.',
    'est-tax': 'Estimated capital gains tax on unrealized profits at your configured tax rate.',
    'net-after-tax': 'Market value minus estimated tax on unrealized gains.',
    'avg-cost': 'Weighted average purchase price per share, adjusted as you buy more.',
    'daily-change': 'Change in portfolio market value compared to the previous trading day.',
    'market-gain': 'Change in portfolio value due to market price movements (excludes new money added).',
    'cumulative-return': 'Percentage P&L relative to cost basis at each point in time.',
    'volatility': 'Annualized standard deviation of daily returns. Measures how much returns fluctuate. Lower is more stable.',
    'sharpe-ratio': 'Return per unit of risk. Above 1 is good, above 2 is excellent. Compares return to volatility.',
    'sortino-ratio': 'Like Sharpe but only penalizes downside volatility. Higher is better.',
    'max-drawdown': 'Largest peak-to-trough decline. Shows the worst loss you would have experienced.',
  };

  var style = document.createElement('style');
  style.textContent = [
    '[data-info] { position: relative; }',
    '.info-btn { position: absolute; top: 4px; right: 4px; width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; line-height: 1; cursor: help; z-index: 10; transition: opacity 0.15s; border: 1.5px solid; }',
    '.info-btn:hover { opacity: 1; }',
    '.info-popup { display: none; position: absolute; top: 26px; right: 0; padding: 8px 12px; border-radius: 8px; font-size: 12px; font-weight: 400; line-height: 1.5; width: 220px; z-index: 100; text-transform: none; letter-spacing: normal; }',
    '.info-btn:hover + .info-popup { display: block; }',
    '.dark .info-btn { color: #e5e7eb; border-color: #e5e7eb; opacity: 0.6; }',
    '.dark .info-popup { background: #1f2937; color: #d1d5db; border: 1px solid #374151; }',
    'html:not(.dark) .info-btn { color: #374151; border-color: #374151; opacity: 0.5; }',
    'html:not(.dark) .info-popup { background: #fff; color: #374151; border: 1px solid #e5e7eb; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }',
  ].join('\n');
  document.head.appendChild(style);

  function init() {
    document.querySelectorAll('[data-info]:not([data-info-done])').forEach(function (el) {
      var key = el.getAttribute('data-info');
      var text = definitions[key];
      if (!text) return;

      el.setAttribute('data-info-done', '1');

      var btn = document.createElement('span');
      btn.className = 'info-btn';
      btn.textContent = '?';

      var popup = document.createElement('span');
      popup.className = 'info-popup';
      popup.textContent = text;

      el.appendChild(btn);
      el.appendChild(popup);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { setTimeout(init, 500); });
  } else {
    setTimeout(init, 500);
  }

  var observer = new MutationObserver(function () {
    if (document.querySelectorAll('[data-info]:not([data-info-done])').length) init();
  });
  observer.observe(document.body, { childList: true, subtree: true });
})();
