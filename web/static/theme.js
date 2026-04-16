/**
 * Theme manager: dark/light mode toggle with localStorage persistence.
 * Must be loaded before other scripts (no defer) to prevent flash.
 */
(function () {
  var STORAGE_KEY = 'portfolio-theme';

  function getPreferred() {
    var stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark') return stored;
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }

  function apply(theme) {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    localStorage.setItem(STORAGE_KEY, theme);
  }

  // Apply immediately to prevent flash
  apply(getPreferred());

  // Expose toggle for navbar button
  window.__toggleTheme = function () {
    var current = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
    var next = current === 'dark' ? 'light' : 'dark';
    apply(next);
    // Dispatch event so charts can re-render with new colors
    window.dispatchEvent(new CustomEvent('themechange', { detail: { theme: next } }));
  };

  // Expose theme colors for Chart.js
  window.__chartTheme = function () {
    var isDark = document.documentElement.classList.contains('dark');
    return {
      text: isDark ? '#d1d5db' : '#374151',
      textMuted: isDark ? '#6b7280' : '#9ca3af',
      grid: isDark ? 'rgba(75, 85, 99, 0.3)' : 'rgba(209, 213, 219, 0.5)',
      tooltipBg: isDark ? '#1f2937' : '#ffffff',
      tooltipTitle: isDark ? '#f3f4f6' : '#111827',
      tooltipBody: isDark ? '#d1d5db' : '#374151',
      tooltipBorder: isDark ? '#374151' : '#e5e7eb',
      doughnutBorder: isDark ? '#111827' : '#ffffff',
    };
  };
})();
