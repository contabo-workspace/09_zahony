window.HomeApp = window.HomeApp || {};

window.HomeApp.utils = (() => {
  const syncBodyScrollLock = () => {
    document.body.classList.toggle('modal-open', Boolean(document.querySelector('.modal.is-open')));
  };

  const resolveModal = (target) => {
    if (!target) {
      return null;
    }
    if (target.startsWith('#')) {
      return document.querySelector(target);
    }
    return document.getElementById(target) || document.querySelector(`[data-modal-name="${target}"]`);
  };

  const openModal = (modal) => {
    if (!modal) {
      return;
    }
    modal.classList.add('is-open');
    modal.setAttribute('aria-hidden', 'false');
    syncBodyScrollLock();
  };

  const closeModal = (modal) => {
    if (!modal) {
      return;
    }
    modal.classList.remove('is-open');
    modal.setAttribute('aria-hidden', 'true');
    syncBodyScrollLock();
  };

  const setModalErrors = (form, errors) => {
    const box = form?.querySelector('[data-modal-errors]');
    if (!box) {
      return;
    }

    box.innerHTML = '';
    if (!errors?.length) {
      return;
    }

    const list = document.createElement('ul');
    list.className = 'errorlist';
    errors.forEach((error) => {
      const item = document.createElement('li');
      item.textContent = error;
      list.appendChild(item);
    });
    box.appendChild(list);
  };

  const postModalForm = async (form, csrfToken = '') => {
    const response = await fetch(form.action, {
      method: 'POST',
      body: new FormData(form),
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': csrfToken,
      },
    });
    const payload = await response.json();
    if (!response.ok) {
      throw payload;
    }
    return payload;
  };

  const initDatePicker = (input) => {
    if (!input || typeof window.flatpickr !== 'function') {
      return;
    }
    window.flatpickr(input, {
      locale: window.flatpickr.l10ns.cs,
      dateFormat: 'Y-m-d',
      altInput: true,
      altFormat: 'j. n. Y',
      appendTo: document.body,
      allowInput: false,
      disableMobile: true,
    });
  };

  const formatCzechDate = (value) => {
    if (!value) {
      return '';
    }
    const isoMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value));
    if (isoMatch) {
      const [, year, month, day] = isoMatch;
      return `${Number(day)}. ${Number(month)}. ${year}`;
    }
    return String(value);
  };

  const isInteractiveTarget = (target) => Boolean(target.closest('[data-card-action], button, form, a, input, select, textarea, label'));

  return {
    closeModal,
    formatCzechDate,
    initDatePicker,
    isInteractiveTarget,
    openModal,
    postModalForm,
    resolveModal,
    setModalErrors,
    syncBodyScrollLock,
  };
})();