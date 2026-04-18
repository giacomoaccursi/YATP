/**
 * Shared alert banner for failed instruments.
 * Call showFailedBanner(data) after fetching /api/portfolio.
 */
window.showFailedBanner = function (data) {
  // Remove any existing banner
  var existing = document.getElementById('failed-banner');
  if (existing) existing.remove();

  var failed = data.failed_instruments || [];
  var marketError = data.market_error;

  if (!marketError && !failed.length) return;

  var banner = document.createElement('div');
  banner.id = 'failed-banner';
  banner.className = 'max-w-7xl mx-auto px-6 mt-4';

  var inner = document.createElement('div');
  inner.className = 'bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-4 flex items-start gap-3';

  var icon = '<svg class="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>';

  var text = '';
  if (marketError) {
    text = '<div class="text-sm font-medium text-amber-800 dark:text-amber-200">Unable to fetch market data</div>' +
           '<div class="text-xs text-amber-600 dark:text-amber-400 mt-0.5">Showing data from transactions only. Market value, P&L and charts require an internet connection.</div>';
  } else if (failed.length) {
    text = '<div class="text-sm font-medium text-amber-800 dark:text-amber-200">Some instruments could not be loaded</div>' +
           '<div class="text-xs text-amber-600 dark:text-amber-400 mt-0.5">Failed to fetch market data for: <span class="font-medium">' +
           failed.join(', ') + '</span>. Data shown excludes these instruments.</div>';
  }

  inner.innerHTML = icon + '<div>' + text + '</div>';
  banner.appendChild(inner);

  // Insert after navbar
  var nav = document.getElementById('main-nav');
  if (nav && nav.nextSibling) {
    nav.parentNode.insertBefore(banner, nav.nextSibling);
  } else {
    document.body.insertBefore(banner, document.body.firstChild);
  }
};
