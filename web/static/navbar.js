/**
 * Shared navbar component. Injected into all pages.
 * Loads translations from JSON files for the current language.
 */
(function () {
  var icons = {
    dashboard: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/></svg>',
    instruments: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>',
    performance: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg>',
    rebalance: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3"/></svg>',
    sellsim: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 15.75V18m-7.5-6.75h.008v.008H8.25v-.008zm0 2.25h.008v.008H8.25V13.5zm0 2.25h.008v.008H8.25v-.008zm0 2.25h.008v.008H8.25V18zm2.498-6.75h.007v.008h-.007v-.008zm0 2.25h.007v.008h-.007V13.5zm0 2.25h.007v.008h-.007v-.008zm0 2.25h.007v.008h-.007V18zm2.504-6.75h.008v.008h-.008v-.008zm0 2.25h.008v.008h-.008V13.5zm3.75-2.25h-3.75m3.75 0V9.75m0 1.5l-3.75 3.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
    transactions: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/></svg>',
    methodology: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg>',
  };

  var refreshIcon = '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>';

  var currentLang = localStorage.getItem('lang') || navigator.language.slice(0, 2) || 'en';
  if (!['en', 'it', 'es'].includes(currentLang)) currentLang = 'en';

  // Load translations and build navbar
  fetch('/static/i18n/' + currentLang + '.json')
    .then(function (r) { return r.json(); })
    .then(function (t) { buildNavbar(t.nav); })
    .catch(function () { buildNavbar(null); });

  function buildNavbar(t) {
    if (!t) t = { dashboard: 'Dashboard', instruments: 'Instruments', performance: 'Performance', rebalance: 'Rebalance', sell_simulator: 'Sell Simulator', transactions: 'Transactions', refresh_prices: 'Refresh Prices', refreshing: 'refreshing...' };

    var pages = [
      { href: '/', label: t.dashboard, icon: 'dashboard' },
      { href: '/instruments', label: t.instruments, icon: 'instruments' },
      { href: '/performance', label: t.performance, icon: 'performance' },
      { href: '/rebalance', label: t.rebalance, icon: 'rebalance' },
      { href: '/sell-simulator', label: t.sell_simulator, icon: 'sellsim' },
      { href: '/transactions', label: t.transactions, icon: 'transactions' },
      { href: '/methodology', label: t.methodology, icon: 'methodology' },
    ];

    var current = window.location.pathname;

    var nav = document.createElement('nav');
    nav.className = 'border-b border-gray-200 dark:border-gray-700 px-6 py-2.5 flex items-center gap-1 bg-white/95 dark:bg-gray-900/95 backdrop-blur-sm sticky top-0 z-50';
    nav.id = 'main-nav';

    // Brand
    var brand = document.createElement('a');
    brand.href = '/';
    brand.className = 'text-sm font-semibold tracking-tight text-gray-900 dark:text-white mr-6 flex items-center gap-2';
    brand.innerHTML = '<svg class="w-5 h-5 text-indigo-500 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg> Portfolio';
    nav.appendChild(brand);

    // Links
    pages.forEach(function (page) {
      var a = document.createElement('a');
      a.href = page.href;
      var isActive = (page.href === '/' && current === '/') || (page.href !== '/' && current.startsWith(page.href));
      a.className = isActive
        ? 'px-3 py-2 text-sm text-gray-900 dark:text-white bg-gray-100 dark:bg-gray-800 rounded-lg flex items-center gap-2'
        : 'px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/50 dark:hover:bg-gray-800/50 rounded-lg transition flex items-center gap-2';
      a.innerHTML = icons[page.icon] + '<span>' + page.label + '</span>';
      nav.appendChild(a);
    });

    // Spacer
    var spacer = document.createElement('div');
    spacer.className = 'flex-1';
    nav.appendChild(spacer);

    // Refresh button
    var refreshBtn = document.createElement('button');
    refreshBtn.className = 'px-3 py-1.5 text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 rounded-lg transition flex items-center gap-2 mr-2';

    var refreshLabel = document.createElement('span');
    refreshLabel.className = 'flex items-center gap-1.5';
    refreshLabel.innerHTML = refreshIcon + ' ' + t.refresh_prices;

    var timestamp = document.createElement('span');
    timestamp.className = 'text-[11px] text-gray-500 dark:text-gray-500 font-normal';
    timestamp.textContent = '';

    refreshBtn.appendChild(refreshLabel);
    refreshBtn.appendChild(timestamp);

    function updateTimestamp() {
      fetch('/api/price-status')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.fetched_at) {
            timestamp.textContent = '· ' + data.fetched_at;
          } else {
            timestamp.textContent = '';
          }
        })
        .catch(function () {});
    }

    refreshBtn.addEventListener('click', function () {
      refreshBtn.style.opacity = '0.5';
      timestamp.textContent = '· ' + t.refreshing;
      fetch('/api/refresh', { method: 'POST' })
        .then(function () {
          refreshBtn.style.opacity = '1';
          window.location.reload();
        })
        .catch(function () {
          refreshBtn.style.opacity = '1';
          timestamp.textContent = '· failed';
        });
    });

    nav.appendChild(refreshBtn);

    // Language selector (dropdown with flags)
    var langs = [
      { code: 'en', flag: '🇬🇧', label: 'English' },
      { code: 'it', flag: '🇮🇹', label: 'Italiano' },
      { code: 'es', flag: '🇪🇸', label: 'Español' },
    ];
    var currentLangObj = langs.find(function (l) { return l.code === currentLang; }) || langs[0];

    var langWrapper = document.createElement('div');
    langWrapper.className = 'relative';

    var langBtn = document.createElement('button');
    langBtn.className = 'px-2 py-1.5 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition flex items-center gap-1.5';
    langBtn.innerHTML = '<span>' + currentLangObj.flag + '</span><span class="text-xs uppercase">' + currentLang + '</span>';

    var langMenu = document.createElement('div');
    langMenu.className = 'absolute right-0 top-full mt-1 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg py-1 hidden z-50 min-w-[140px]';

    langs.forEach(function (lang) {
      var item = document.createElement('button');
      item.className = 'w-full px-3 py-2 text-sm text-left flex items-center gap-2 hover:bg-gray-100 dark:hover:bg-gray-800 transition' + (lang.code === currentLang ? ' font-medium text-indigo-600 dark:text-indigo-400' : ' text-gray-700 dark:text-gray-300');
      item.innerHTML = '<span>' + lang.flag + '</span><span>' + lang.label + '</span>';
      item.addEventListener('click', function () {
        localStorage.setItem('lang', lang.code);
        window.location.reload();
      });
      langMenu.appendChild(item);
    });

    langBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      langMenu.classList.toggle('hidden');
    });
    document.addEventListener('click', function () { langMenu.classList.add('hidden'); });

    langWrapper.appendChild(langBtn);
    langWrapper.appendChild(langMenu);
    nav.appendChild(langWrapper);

    // Theme toggle
    var sunIcon = '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/></svg>';
    var moonIcon = '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>';

    var themeBtn = document.createElement('button');
    themeBtn.className = 'p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition';
    themeBtn.title = 'Toggle theme';
    function updateThemeIcon() {
      var isDark = document.documentElement.classList.contains('dark');
      themeBtn.innerHTML = isDark ? sunIcon : moonIcon;
    }
    updateThemeIcon();
    themeBtn.addEventListener('click', function () {
      window.__toggleTheme();
      updateThemeIcon();
    });
    nav.appendChild(themeBtn);

    document.body.prepend(nav);

    // Fetch timestamp on load
    updateTimestamp();
    window.__updateNavTimestamp = updateTimestamp;
  }
})();
