/**
 * Shared navbar component. Injected into all pages.
 */
(function () {
  var icons = {
    dashboard: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/></svg>',
    instruments: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>',
    performance: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg>',
    rebalance: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3"/></svg>',
    transactions: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/></svg>',
    sellsim: '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 15.75V18m-7.5-6.75h.008v.008H8.25v-.008zm0 2.25h.008v.008H8.25V13.5zm0 2.25h.008v.008H8.25v-.008zm0 2.25h.008v.008H8.25V18zm2.498-6.75h.007v.008h-.007v-.008zm0 2.25h.007v.008h-.007V13.5zm0 2.25h.007v.008h-.007v-.008zm0 2.25h.007v.008h-.007V18zm2.504-6.75h.008v.008h-.008v-.008zm0 2.25h.008v.008h-.008V13.5zm3.75-2.25h-3.75m3.75 0V9.75m0 1.5l-3.75 3.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
  };

  var sunIcon = '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/></svg>';
  var moonIcon = '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>';

  var pages = [
    { href: '/', label: 'Dashboard', icon: 'dashboard' },
    { href: '/instruments', label: 'Instruments', icon: 'instruments' },
    { href: '/performance', label: 'Performance', icon: 'performance' },
    { href: '/rebalance', label: 'Rebalance', icon: 'rebalance' },
    { href: '/sell-simulator', label: 'Sell Sim', icon: 'sellsim' },
    { href: '/transactions', label: 'Transactions', icon: 'transactions' },
  ];

  var current = window.location.pathname;

  var nav = document.createElement('nav');
  nav.className = 'border-b border-gray-200 dark:border-gray-800 px-6 py-2.5 flex items-center gap-1 bg-white/95 dark:bg-gray-950/95 backdrop-blur-sm sticky top-0 z-50';
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
      : 'px-3 py-2 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/50 dark:hover:bg-gray-800/50 rounded-lg transition flex items-center gap-2';
    a.innerHTML = icons[page.icon] + '<span>' + page.label + '</span>';
    nav.appendChild(a);
  });

  // Spacer
  var spacer = document.createElement('div');
  spacer.className = 'flex-1';
  nav.appendChild(spacer);

  // Theme toggle
  var btn = document.createElement('button');
  btn.className = 'p-2 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition';
  btn.title = 'Toggle theme';
  function updateIcon() {
    var isDark = document.documentElement.classList.contains('dark');
    btn.innerHTML = isDark ? sunIcon : moonIcon;
  }
  updateIcon();
  btn.addEventListener('click', function () {
    window.__toggleTheme();
    updateIcon();
  });
  nav.appendChild(btn);

  document.body.prepend(nav);
})();
