/**
 * Vue app for the transactions page.
 * No business logic — net value computed by /api/transactions/net-value.
 */

const { createApp, ref, computed, onMounted, watch } = Vue;

createApp({
  setup() {
    // Data
    const transactions = ref([]);
    const availableInstruments = ref([]);

    // Filters
    const filters = ref({ security: '', type: '', dateFrom: '', dateTo: '' });

    // Form state
    const showAddForm = ref(false);
    const customSecurity = ref(false);
    const formMessage = ref('');
    const formError = ref(false);
    const form = ref(createEmptyForm());
    const editIndex = ref(null);
    const computedNetValue = ref('0.00');
    let netValueTimer = null;

    // Delete state
    const deleteIndex = ref(null);

    // Computed
    const securities = computed(function () { return [...new Set(transactions.value.map(function (t) { return t.security; }))].sort(); });
    const hasFilters = computed(function () { return Object.values(filters.value).some(function (v) { return v; }); });
    const isEditing = computed(function () { return editIndex.value !== null; });

    const filteredTransactions = computed(function () {
      return transactions.value.filter(function (tx) {
        if (filters.value.security && tx.security !== filters.value.security) return false;
        if (filters.value.type && tx.type !== filters.value.type) return false;
        if (filters.value.dateFrom && tx.date < filters.value.dateFrom) return false;
        if (filters.value.dateTo && tx.date > filters.value.dateTo) return false;
        return true;
      });
    });

    // Fetch net value from backend (debounced)
    function updateNetValue() {
      clearTimeout(netValueTimer);
      netValueTimer = setTimeout(async function () {
        var val = await fetchNetValue(form.value);
        computedNetValue.value = val;
      }, 150);
    }

    // Watch form fields that affect net value
    watch(function () {
      return [form.value.type, form.value.shares, form.value.quote, form.value.fees, form.value.taxes];
    }, updateNetValue, { deep: true });

    // Methods
    function typeBadge(type) {
      var map = {
        Buy: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-400',
        Sell: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-400',
        Dividend: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-400',
        Coupon: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-400',
      };
      return map[type] || 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400';
    }

    function clearFilters() {
      filters.value = { security: '', type: '', dateFrom: '', dateTo: '' };
    }

    function openAddForm() {
      editIndex.value = null;
      form.value = createEmptyForm();
      computedNetValue.value = '0.00';
      if (availableInstruments.value.length) {
        form.value.security = availableInstruments.value[0];
      }
      customSecurity.value = false;
      formMessage.value = '';
      formError.value = false;
      showAddForm.value = true;
    }

    function openEditForm(tx) {
      editIndex.value = tx.index;
      form.value = {
        date: tx.date,
        type: tx.type,
        security: tx.security,
        shares: tx.shares > 0 ? String(tx.shares) : '',
        quote: tx.quote > 0 ? String(tx.quote) : '',
        fees: tx.fees > 0 ? String(tx.fees) : '',
        taxes: tx.taxes > 0 ? String(tx.taxes) : '',
        net_transaction_value: String(tx.net_transaction_value),
      };
      computedNetValue.value = String(tx.net_transaction_value);
      customSecurity.value = !availableInstruments.value.includes(tx.security);
      formMessage.value = '';
      formError.value = false;
      showAddForm.value = true;
    }

    function confirmDelete(index) {
      deleteIndex.value = index;
    }

    async function executeDelete() {
      try {
        var res = await fetch('/api/transactions/' + deleteIndex.value, { method: 'DELETE' });
        if (res.ok) await fetchData();
      } catch (err) {
        console.error('Delete failed:', err);
      }
      deleteIndex.value = null;
    }

    async function fetchData() {
      var responses = await Promise.all([
        fetch('/api/transactions/list'),
        fetch('/api/instruments'),
      ]);
      transactions.value = (await responses[0].json()).transactions;
      availableInstruments.value = (await responses[1].json()).instruments;
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

    watch(function () { return form.value.security; }, function (val) {
      if (val === '__custom__') {
        customSecurity.value = true;
        form.value.security = '';
      }
    });

    onMounted(fetchData);

    return {
      transactions, availableInstruments, filters, securities,
      hasFilters, filteredTransactions, clearFilters, typeBadge,
      showAddForm, customSecurity, form, formMessage, formError,
      computedNetValue, saveTransaction, isEditing,
      openAddForm, openEditForm,
      deleteIndex, confirmDelete, executeDelete,
      fmt, fmtSigned, pnlColor,
    };
  },
}).mount('#app');
