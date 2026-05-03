/**
 * Info tooltip definitions. Maps field keys to explanations.
 * Renders a ? icon in the top-right corner of the parent element.
 * Language-aware: reads from localStorage.
 */
(function () {
  var lang = localStorage.getItem('lang') || navigator.language.slice(0, 2) || 'en';
  if (lang !== 'en' && lang !== 'it') lang = 'en';

  var definitions_en = {
    'cost-basis': 'Total amount invested across all instruments, net of accrued interest for bonds.',
    'market-value': 'Total current value of all holdings at today\'s market prices.',
    'total-pnl': 'Total profit or loss: unrealized (current holdings) + realized (from past sales). Income shown separately.',
    'income': 'Total dividends and bond coupons received since inception.',
    'xirr': 'Annualized money-weighted return (XIRR). Accounts for the timing and size of each cash flow.',
    'volatility': 'Annualized standard deviation of daily returns. Measures how much returns fluctuate.',
    'sharpe-ratio': 'Return per unit of risk. Above 1 is good, above 2 is excellent.',
    'sortino-ratio': 'Like Sharpe but only penalizes downside volatility. Higher is better.',
    'max-drawdown': 'Largest peak-to-trough decline. Shows the worst loss you would have experienced.',
  };

  var definitions_it = {
    'cost-basis': 'Importo totale investito in tutti gli strumenti, al netto del rateo per le obbligazioni.',
    'market-value': 'Valore attuale di tutte le posizioni ai prezzi di mercato odierni.',
    'total-pnl': 'Profitto o perdita totale: non realizzato (posizioni aperte) + realizzato (vendite passate). Rendite mostrate separatamente.',
    'income': 'Totale dividendi e cedole obbligazionarie ricevuti dall\'inizio.',
    'xirr': 'Rendimento annualizzato ponderato per il denaro (XIRR). Tiene conto dei tempi e dell\'entità di ogni flusso.',
    'volatility': 'Deviazione standard annualizzata dei rendimenti giornalieri. Misura la variabilità.',
    'sharpe-ratio': 'Rendimento per unità di rischio. Sopra 1 è buono, sopra 2 è eccellente.',
    'sortino-ratio': 'Come Sharpe ma penalizza solo la volatilità al ribasso. Più alto è meglio.',
    'max-drawdown': 'Maggior calo dal picco al minimo. Mostra la peggior perdita che avresti subito.',
  };

  var definitions = lang === 'it' ? definitions_it : definitions_en;

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
