/**
 * Vue app for the transactions page.
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

    // Delete state
    const deleteIndex = ref(null);

    // Computed
    const securities = computed(() => [...new Set(transactions.value.map(t => t.security))].sort());
    const hasFilters = computed(() => Object.values(filters.value).some(v => v));
    const computedNetValue = computed(() => computeNetValue(form.value));
    const isEditing = computed(() => editIndex.value !== null);

    const filteredTransactions = computed(() => {
      return transactions.value.filter(tx => {
        if (filters.value.security && tx.security !== filters.value.security) return false;
        if (filters.value.type && tx.type !== filters.value.type) return false;
        if (filters.value.dateFrom && tx.date < filters.value.dateFrom) return false;
        if (filters.value.dateTo && tx.date > filters.value.dateTo) return false;
        return true;
      });
    });

    // Methods
    function typeBadge(type) {
      const map = {
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
        const res = await fetch('/api/transactions/' + deleteIndex.value, { method: 'DELETE' });
        if (res.ok) await fetchData();
      } catch (err) {
        console.error('Delete failed:', err);
      }
      deleteIndex.value = null;
    }

    async function fetchData() {
      const [txRes, instRes] = await Promise.all([
        fetch('/api/transactions/list'),
        fetch('/api/instruments'),
      ]);
      transactions.value = (await txRes.json()).transactions;
      availableInstruments.value = (await instRes.json()).instruments;
      if (!form.value.security && availableInstruments.value.length) {
        form.value.security = availableInstruments.value[0];
      }
    }

    async function saveTransaction(keepOpen) {
      formMessage.value = '';
      formError.value = false;
      try {
        let result;
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
          } else {
            showAddForm.value = false;
          }
        }
      } catch (err) {
        formMessage.value = 'Network error';
        formError.value = true;
      }
    }

    watch(() => form.value.security, (val) => {
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
