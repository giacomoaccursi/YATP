/**
 * Shared navbar component. Injected into all pages.
 */
(function () {
  const pages = [
    { href: '/', label: 'Dashboard' },
    { href: '/instruments', label: 'Instruments' },
    { href: '/performance', label: 'Performance' },
    { href: '/rebalance', label: 'Rebalance' },
    { href: '/transactions', label: 'Transactions' },
  ];

  const current = window.location.pathname;

  const nav = document.createElement('nav');
  nav.className = 'border-b border-gray-800 px-6 py-3 flex items-center gap-1 bg-gray-950';
  nav.id = 'main-nav';

  pages.forEach(function (page) {
    const a = document.createElement('a');
    a.href = page.href;
    a.textContent = page.label;
    const isActive = (page.href === '/' && current === '/') || (page.href !== '/' && current.startsWith(page.href));
    a.className = isActive
      ? 'px-3 py-1.5 text-sm bg-gray-800 text-white rounded-lg'
      : 'px-3 py-1.5 text-sm text-gray-400 hover:text-white hover:bg-gray-800/50 rounded-lg transition';
    nav.appendChild(a);
  });

  document.body.prepend(nav);
})();
