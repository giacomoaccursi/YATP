/**
 * Vue app for the transactions page.
 * No business logic — net value computed by /api/transactions/net-value.
 */

const { createApp, ref, computed, onMounted, watch } = Vue;

createApp({
  setup() {
    const transactions = ref([]);
    const availableInstruments = ref([]);
    const instrumentTypes = ref({});
    const filters = ref({ security: '', type: '', dateFrom: '', dateTo: '' });

    // Sorting
    const sortKey = ref('');
    const sortDir = ref('desc');

    function toggleSort(key) {
      if (sortKey.value === key) {
        sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc';
      } else {
        sortKey.value = key;
        sortDir.value = 'desc';
      }
    }

    function sortIcon(key) {
      if (sortKey.value !== key) return '<svg class="w-3 h-3 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"/></svg>';
      if (sortDir.value === 'asc') return '<svg class="w-3 h-3 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 15l7-7 7 7"/></svg>';
      return '<svg class="w-3 h-3 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg>';
    }

    // Transaction form
    const showAddForm = ref(false);
    const formMessage = ref('');
    const formError = ref(false);
    const form = ref(createEmptyForm());
    const editIndex = ref(null);
    const computedNetValue = ref('0.00');
    let netValueTimer = null;

    // New instrument modal
    const showNewInstrument = ref(false);
    const newInstrument = ref({ name: '', ticker: '', isin: '', type: 'ETF', taxRate: 26, customType: '' });
    const newInstrumentError = ref('');

    // Delete
    const deleteIndex = ref(null);

    // Computed
    const securities = computed(function () { return [...new Set(transactions.value.map(function (t) { return t.security; }))].sort(); });
    const hasFilters = computed(function () { return Object.values(filters.value).some(function (v) { return v; }); });
    const isEditing = computed(function () { return editIndex.value !== null; });
    const isSelectedBond = computed(function () {
      return instrumentTypes.value[form.value.security] === 'Bond';
    });

    const filteredTransactions = computed(function () {
      var result = transactions.value.filter(function (tx) {
        if (filters.value.security && tx.security !== filters.value.security) return false;
        if (filters.value.type && tx.type !== filters.value.type) return false;
        if (filters.value.dateFrom && tx.date < filters.value.dateFrom) return false;
        if (filters.value.dateTo && tx.date > filters.value.dateTo) return false;
        return true;
      });
      if (sortKey.value) {
        var key = sortKey.value;
        var dir = sortDir.value === 'asc' ? 1 : -1;
        result = result.slice().sort(function (a, b) {
          var va = a[key] || 0;
          var vb = b[key] || 0;
          if (va < vb) return -1 * dir;
          if (va > vb) return 1 * dir;
          return 0;
        });
      }
      return result;
    });

    // Net value (debounced backend call)
    function updateNetValue() {
      clearTimeout(netValueTimer);
      netValueTimer = setTimeout(async function () {
        computedNetValue.value = await fetchNetValue(form.value);
      }, 150);
    }

    watch(function () {
      return [form.value.type, form.value.shares, form.value.quote, form.value.fees, form.value.taxes];
    }, updateNetValue, { deep: true });

    // Transaction type badge
    function typeBadge(type) {
      var map = {
        Buy: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-400',
        Sell: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-400',
        Dividend: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-400',
        Coupon: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-400',
      };
      return map[type] || 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400';
    }

    function clearFilters() { filters.value = { security: '', type: '', dateFrom: '', dateTo: '' }; }

    function openAddForm() {
      editIndex.value = null;
      form.value = createEmptyForm();
      computedNetValue.value = '0.00';
      if (availableInstruments.value.length) form.value.security = availableInstruments.value[0];
      formMessage.value = '';
      formError.value = false;
      showAddForm.value = true;
    }

    function openEditForm(tx) {
      editIndex.value = tx.index;
      form.value = {
        date: tx.date, type: tx.type, security: tx.security,
        shares: tx.shares > 0 ? String(tx.shares) : '',
        quote: tx.quote > 0 ? String(tx.quote) : '',
        fees: tx.fees > 0 ? String(tx.fees) : '',
        taxes: tx.taxes > 0 ? String(tx.taxes) : '',
        accrued_interest: tx.accrued_interest > 0 ? String(tx.accrued_interest) : '',
        net_transaction_value: String(tx.net_transaction_value),
      };
      computedNetValue.value = String(tx.net_transaction_value);
      formMessage.value = '';
      formError.value = false;
      showAddForm.value = true;
    }

    function confirmDelete(index) { deleteIndex.value = index; }

    async function executeDelete() {
      try {
        var res = await fetch('/api/transactions/' + deleteIndex.value, { method: 'DELETE' });
        if (res.ok) await fetchData();
      } catch (err) { console.error('Delete failed:', err); }
      deleteIndex.value = null;
    }

    async function fetchData() {
      var responses = await Promise.all([fetch('/api/transactions/list'), fetch('/api/instruments')]);
      transactions.value = (await responses[0].json()).transactions;
      var instData = await responses[1].json();
      availableInstruments.value = instData.instruments;
      instrumentTypes.value = instData.instrument_types || {};
      if (!form.value.security && availableInstruments.value.length) {
        form.value.security = availableInstruments.value[0];
      }
    }

    async function saveTransaction(keepOpen) {
      formMessage.value = '';
      formError.value = false;
      try {
        var result;
        if (isEditing.value) {
          result = await updateTransactionApi(editIndex.value, form.value, computedNetValue.value);
        } else {
          result = await submitTransactionToApi(form.value, computedNetValue.value);
        }
        formMessage.value = result.message;
        formError.value = !result.ok;
        if (result.ok) {
          await fetchData();
          if (isEditing.value) {
            showAddForm.value = false;
            editIndex.value = null;
          } else if (keepOpen) {
            form.value.shares = '';
            form.value.quote = '';
            form.value.fees = '';
            form.value.taxes = '';
            form.value.accrued_interest = '';
            form.value.net_transaction_value = '';
            computedNetValue.value = '0.00';
          } else {
            showAddForm.value = false;
          }
        }
      } catch (err) {
        formMessage.value = 'Network error';
        formError.value = true;
      }
    }

    // New instrument modal
    function openNewInstrumentModal() {
      newInstrument.value = { name: '', ticker: '', isin: '', type: 'ETF', taxRate: 26, customType: '' };
      newInstrumentError.value = '';
      showNewInstrument.value = true;
    }

    async function saveNewInstrument() {
      newInstrumentError.value = '';
      var ni = newInstrument.value;
      if (!ni.name.trim()) { newInstrumentError.value = 'Name is required'; return; }

      var instType = ni.type === '__other__' ? ni.customType.trim() : ni.type;
      if (!instType) { newInstrumentError.value = 'Asset type is required'; return; }

      var ticker = ni.ticker.trim();
      var isin = ni.isin.trim();

      if (instType === 'Bond') {
        if (!isin) { newInstrumentError.value = 'ISIN is required for bonds'; return; }
        if (!ticker) ticker = isin;
      } else {
        if (!ticker) { newInstrumentError.value = 'Ticker is required'; return; }
      }

      try {
        var res = await fetch('/api/instruments', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            security: ni.name.trim(),
            ticker: ticker,
            type: instType,
            capital_gains_rate: ni.taxRate / 100,
            isin: isin || null,
          }),
        });
        var data = await res.json();
        if (!res.ok && res.status !== 409) {
          newInstrumentError.value = data.error || 'Failed to add instrument';
          return;
        }
        await fetchData();
        form.value.security = ni.name.trim();
        showNewInstrument.value = false;
      } catch (err) {
        newInstrumentError.value = 'Network error';
      }
    }

    // When user selects __custom__, open the modal
    watch(function () { return form.value.security; }, function (val) {
      if (val === '__custom__') {
        form.value.security = availableInstruments.value[0] || '';
        Vue.nextTick(openNewInstrumentModal);
      }
    });

    onMounted(fetchData);

    return {
      transactions, availableInstruments, instrumentTypes, filters, securities,
      hasFilters, filteredTransactions, clearFilters, typeBadge,
      sortKey, sortDir, toggleSort, sortIcon,
      showAddForm, form, formMessage, formError,
      computedNetValue, saveTransaction, isEditing, isSelectedBond,
      openAddForm, openEditForm,
      showNewInstrument, newInstrument, newInstrumentError, saveNewInstrument,
      deleteIndex, confirmDelete, executeDelete,
      fmt, fmtSigned, pnlColor,
    };
  },
}).mount('#app');
