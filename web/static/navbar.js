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
  };

  var pages = [
    { href: '/', label: 'Dashboard', icon: 'dashboard' },
    { href: '/instruments', label: 'Instruments', icon: 'instruments' },
    { href: '/performance', label: 'Performance', icon: 'performance' },
    { href: '/rebalance', label: 'Rebalance', icon: 'rebalance' },
    { href: '/transactions', label: 'Transactions', icon: 'transactions' },
  ];

  var current = window.location.pathname;

  var nav = document.createElement('nav');
  nav.className = 'border-b border-gray-800 px-6 py-2.5 flex items-center gap-1 bg-gray-950/95 backdrop-blur-sm sticky top-0 z-50';
  nav.id = 'main-nav';

  // Brand
  var brand = document.createElement('a');
  brand.href = '/';
  brand.className = 'text-sm font-semibold tracking-tight text-white mr-6 flex items-center gap-2';
  brand.innerHTML = '<svg class="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg> Portfolio';
  nav.appendChild(brand);

  // Links
  pages.forEach(function (page) {
    var a = document.createElement('a');
    a.href = page.href;
    var isActive = (page.href === '/' && current === '/') || (page.href !== '/' && current.startsWith(page.href));
    a.className = isActive
      ? 'px-3 py-2 text-sm text-white bg-gray-800 rounded-lg flex items-center gap-2'
      : 'px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800/50 rounded-lg transition flex items-center gap-2';
    a.innerHTML = icons[page.icon] + '<span>' + page.label + '</span>';
    nav.appendChild(a);
  });

  document.body.prepend(nav);
})();
