/**
 * Vue app for the sell simulator page.
 * No business logic — all calculations done by /api/simulate/sell.
 */

const { createApp, ref, computed, watch, onMounted } = Vue;

createApp({
  setup() {
    const loading = ref(true);
    const instruments = ref([]);
    const selectedSecurity = ref('');
    const sharesToSell = ref(0);
    const result = ref(null);
    const error = ref(null);
    let debounceTimer = null;

    const selectedInstrument = computed(function () {
      return instruments.value.find(function (i) { return i.security === selectedSecurity.value; }) || null;
    });

    async function fetchInstruments() {
      try {
        var res = await fetch('/api/portfolio');
        var data = await res.json();
        instruments.value = data.instruments;
        loading.value = false;
        if (window.__updateNavTimestamp) window.__updateNavTimestamp();
        if (window.showFailedBanner) window.showFailedBanner(data);
      } catch (err) {
        console.error('Failed to fetch instruments:', err);
        loading.value = false;
      }
    }

    async function simulate() {
      error.value = null;
      result.value = null;

      if (!selectedSecurity.value || !sharesToSell.value || sharesToSell.value <= 0) {
        return;
      }

      try {
        var res = await fetch('/api/simulate/sell', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            security: selectedSecurity.value,
            shares: sharesToSell.value,
          }),
        });
        var data = await res.json();
        if (res.ok) {
          result.value = data;
        } else {
          error.value = data.error || 'Simulation failed';
        }
      } catch (err) {
        error.value = 'Unable to connect to server';
      }
    }

    function debouncedSimulate() {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(simulate, 300);
    }

    watch([selectedSecurity, sharesToSell], function () {
      result.value = null;
      error.value = null;
      debouncedSimulate();
    });

    onMounted(fetchInstruments);

    return {
      loading, instruments, selectedSecurity, sharesToSell,
      selectedInstrument, result, error,
      fmt, fmtSigned, pnlColor,
    };
  },
}).mount('#app');
