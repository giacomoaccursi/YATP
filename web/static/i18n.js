/**
 * Internationalization setup using vue-i18n.
 * Loads translations from JSON files and provides the i18n instance.
 *
 * Usage in each page's Vue app:
 *   const i18n = await createI18nInstance();
 *   const app = createApp({ ... });
 *   app.use(i18n);
 *   app.mount('#app');
 *
 * In templates: {{ $t('dashboard.title') }}
 * With variables: {{ $t('dashboard.transactions_count', { count: 42 }) }}
 */

var _i18nMessages = {};
var _i18nReady = false;

async function createI18nInstance() {
  var savedLang = localStorage.getItem('lang') || navigator.language.slice(0, 2) || 'en';
  if (savedLang !== 'en' && savedLang !== 'it') savedLang = 'en';

  if (!_i18nReady) {
    var [en, it] = await Promise.all([
      fetch('/static/i18n/en.json').then(function (r) { return r.json(); }),
      fetch('/static/i18n/it.json').then(function (r) { return r.json(); }),
    ]);
    _i18nMessages = { en: en, it: it };
    _i18nReady = true;
  }

  return VueI18n.createI18n({
    locale: savedLang,
    fallbackLocale: 'en',
    messages: _i18nMessages,
  });
}

function switchLanguage(i18n, lang) {
  i18n.global.locale = lang;
  localStorage.setItem('lang', lang);
  document.documentElement.lang = lang;
  window.dispatchEvent(new Event('langchange'));
}

function getCurrentLang() {
  return localStorage.getItem('lang') || navigator.language.slice(0, 2) || 'en';
}
