document.addEventListener('DOMContentLoaded', () => {
  const body = document.body;
  const mainForm = document.getElementById('order-create-form');
  if (!mainForm) {
    return;
  }

  const csrfToken = mainForm.querySelector('input[name="csrfmiddlewaretoken"]')?.value || '';
  const modals = Array.from(document.querySelectorAll('.modal'));
  const customerSelect = mainForm.querySelector('select[name="customer"]');
  const statusSelect = mainForm.querySelector('select[name="status"]');
  const pickupInput = mainForm.querySelector('input[name="pickup_at"]');
  const totalFormsInput = mainForm.querySelector('input[name="items-TOTAL_FORMS"]');
  const itemStorage = document.getElementById('order-items-storage');
  const itemsSummary = document.getElementById('order-items-summary');
  const itemsEmpty = document.getElementById('order-items-empty');
  const summaryItemsList = document.getElementById('summary-items-list');
  const summaryItemsEmpty = document.getElementById('summary-items-empty');
  const summaryCustomer = document.getElementById('summary-customer');
  const summaryStatus = document.getElementById('summary-status');
  const summaryPickup = document.getElementById('summary-pickup');
  const summaryTotal = document.getElementById('summary-total');
  const itemModalForm = document.getElementById('order-item-modal-form');
  const itemModalBed = itemModalForm?.querySelector('select[name="item_modal-raised_bed"]');
  const itemModalQuantity = itemModalForm?.querySelector('input[name="item_modal-quantity"]');
  const itemModalUnitPrice = itemModalForm?.querySelector('input[name="item_modal-unit_price"]');

  const bedsPayloadElement = document.getElementById('beds-payload');
  const beds = new Map();
  if (bedsPayloadElement?.textContent) {
    JSON.parse(bedsPayloadElement.textContent).forEach((bed) => {
      beds.set(String(bed.id), bed);
    });
  }

  const resolveModal = (target) => {
    if (!target) {
      return null;
    }
    if (target.startsWith('#')) {
      return document.querySelector(target);
    }
    return document.getElementById(target) || document.querySelector(`[data-modal-name="${target}"]`);
  };

  const closeModal = (modal) => {
    if (!modal) {
      return;
    }
    modal.classList.remove('is-open');
    modal.setAttribute('aria-hidden', 'true');
    if (!document.querySelector('.modal.is-open')) {
      body.classList.remove('modal-open');
    }
  };

  const openModal = (modal) => {
    if (!modal) {
      return;
    }
    modal.classList.add('is-open');
    modal.setAttribute('aria-hidden', 'false');
    body.classList.add('modal-open');
  };

  document.querySelectorAll('[data-modal-open]').forEach((trigger) => {
    trigger.addEventListener('click', () => {
      openModal(resolveModal(trigger.getAttribute('data-modal-open')));
    });
  });

  modals.forEach((modal) => {
    modal.querySelectorAll('[data-modal-close]').forEach((control) => {
      control.addEventListener('click', () => closeModal(modal));
    });
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      document.querySelectorAll('.modal.is-open').forEach((modal) => closeModal(modal));
    }
  });

  const setModalErrors = (form, errors) => {
    const box = form.querySelector('[data-modal-errors]');
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

  const postModalForm = async (form) => {
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

  const updateSummaryHeader = () => {
    if (summaryCustomer && customerSelect) {
      summaryCustomer.textContent = customerSelect.selectedOptions[0]?.text?.trim() || 'Nevybrán';
    }
    if (summaryStatus && statusSelect) {
      summaryStatus.textContent = statusSelect.selectedOptions[0]?.text?.trim() || 'Objednáno';
    }
    if (summaryPickup && pickupInput) {
      summaryPickup.textContent = pickupInput.value ? pickupInput.value.replace('T', ' ') : 'Bez termínu';
    }
  };

  const getItemRows = () => Array.from(itemStorage?.querySelectorAll('[data-form-index]') || []);

  const getRowFields = (row) => ({
    id: row.querySelector('input[name$="-id"]'),
    bed: row.querySelector('[name$="-raised_bed"]'),
    quantity: row.querySelector('[name$="-quantity"]'),
    unitPrice: row.querySelector('[name$="-unit_price"]'),
    deleted: row.querySelector('[name$="-DELETE"]'),
  });

  const activeItems = () => {
    return getItemRows()
      .map((row) => ({ row, fields: getRowFields(row) }))
      .filter(({ fields }) => fields.bed && fields.quantity && !(fields.deleted && fields.deleted.checked))
      .map(({ row, fields }) => {
        const bedId = fields.bed.value;
        const bed = beds.get(String(bedId));
        const quantity = Number(fields.quantity.value || 0);
        const unitPrice = String(fields.unitPrice?.value || '0').replace(',', '.');
        const lineTotal = quantity * Number(unitPrice || 0);
        return {
          index: row.dataset.formIndex,
          bedId,
          bedLabel: bed?.label || 'Záhon není vybraný',
          quantity,
          unitPrice: Number(unitPrice || 0),
          lineTotal,
        };
      })
      .filter((item) => item.bedId && item.quantity > 0);
  };

  const formatMoney = (value) => `${value.toFixed(2).replace('.', ',')} Kč`;

  const renderItems = () => {
    const items = activeItems();

    if (itemsSummary) {
      itemsSummary.innerHTML = items
        .map(
          (item) => `
            <article class="item-summary-card" data-form-index="${item.index}">
              <div class="item-summary-main">
                <strong>${item.bedLabel}</strong>
                <span>${item.quantity} ks</span>
              </div>
              <div class="item-summary-side">
                <span>${formatMoney(item.unitPrice)} / ks</span>
                <button type="button" class="button button-link item-remove-button" data-item-remove="${item.index}">Odebrat</button>
              </div>
            </article>
          `
        )
        .join('');
    }

    if (summaryItemsList) {
      summaryItemsList.innerHTML = items
        .map(
          (item) => `
            <div class="summary-item">
              <strong>${item.bedLabel}</strong>
              <span class="summary-meta">${item.quantity} ks</span>
            </div>
          `
        )
        .join('');
    }

    const hasItems = items.length > 0;
    itemsEmpty?.classList.toggle('is-hidden', hasItems);
    summaryItemsEmpty?.classList.toggle('is-hidden', hasItems);

    if (summaryTotal) {
      const total = items.reduce((sum, item) => sum + item.lineTotal, 0);
      summaryTotal.textContent = formatMoney(total);
    }
  };

  const addHiddenInput = (row, name, value, type = 'hidden') => {
    const input = document.createElement('input');
    input.type = type;
    input.name = name;
    input.value = value;
    row.appendChild(input);
    return input;
  };

  const appendItemRow = ({ bedId, quantity, unitPrice }) => {
    if (!itemStorage || !totalFormsInput) {
      return;
    }
    const index = Number(totalFormsInput.value || 0);
    const row = document.createElement('div');
    row.className = 'stored-item-row';
    row.dataset.orderItem = 'true';
    row.dataset.formIndex = String(index);
    addHiddenInput(row, `items-${index}-id`, '');
    addHiddenInput(row, `items-${index}-raised_bed`, String(bedId));
    addHiddenInput(row, `items-${index}-quantity`, String(quantity));
    addHiddenInput(row, `items-${index}-unit_price`, String(unitPrice).replace('.', ','));
    const deleteInput = addHiddenInput(row, `items-${index}-DELETE`, '', 'checkbox');
    deleteInput.value = 'on';
    deleteInput.checked = false;
    itemStorage.appendChild(row);
    totalFormsInput.value = String(index + 1);
  };

  itemsSummary?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-item-remove]');
    if (!button) {
      return;
    }
    const row = itemStorage?.querySelector(`[data-form-index="${button.getAttribute('data-item-remove')}"]`);
    const deleteInput = row?.querySelector('[name$="-DELETE"]');
    if (deleteInput) {
      deleteInput.checked = true;
    }
    renderItems();
  });

  customerSelect?.addEventListener('change', updateSummaryHeader);
  statusSelect?.addEventListener('change', updateSummaryHeader);
  pickupInput?.addEventListener('input', updateSummaryHeader);

  const customerModalForm = document.getElementById('customer-modal-form');
  customerModalForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      const payload = await postModalForm(customerModalForm);
      setModalErrors(customerModalForm, []);
      if (customerSelect && payload.customer) {
        const option = new Option(payload.customer.label, payload.customer.id, true, true);
        customerSelect.add(option);
        customerSelect.value = String(payload.customer.id);
      }
      updateSummaryHeader();
      customerModalForm.reset();
      closeModal(resolveModal('customer-modal'));
    } catch (payload) {
      setModalErrors(customerModalForm, payload.errors || ['Uložení zákazníka se nepodařilo.']);
    }
  });

  const addBedOption = (select, bed) => {
    if (!select || !bed) {
      return;
    }
    const optionExists = Array.from(select.options).some((option) => option.value === String(bed.id));
    if (!optionExists) {
      select.add(new Option(bed.label, bed.id));
    }
  };

  const raisedBedModalForm = document.getElementById('raised-bed-modal-form');
  raisedBedModalForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      const payload = await postModalForm(raisedBedModalForm);
      setModalErrors(raisedBedModalForm, []);
      if (payload.raised_bed) {
        beds.set(String(payload.raised_bed.id), payload.raised_bed);
        addBedOption(itemModalBed, payload.raised_bed);
        if (itemModalBed) {
          itemModalBed.value = String(payload.raised_bed.id);
        }
        if (itemModalUnitPrice) {
          itemModalUnitPrice.value = payload.raised_bed.base_price;
        }
      }
      raisedBedModalForm.reset();
      closeModal(resolveModal('raised-bed-modal'));
    } catch (payload) {
      setModalErrors(raisedBedModalForm, payload.errors || ['Uložení záhonu se nepodařilo.']);
    }
  });

  itemModalBed?.addEventListener('change', () => {
    const selected = beds.get(String(itemModalBed.value));
    if (selected && itemModalUnitPrice && !itemModalUnitPrice.dataset.userEdited) {
      itemModalUnitPrice.value = selected.base_price;
    }
  });

  itemModalUnitPrice?.addEventListener('input', () => {
    itemModalUnitPrice.dataset.userEdited = 'true';
  });

  itemModalForm?.addEventListener('submit', (event) => {
    event.preventDefault();
    const errors = [];
    const bedId = itemModalBed?.value;
    const quantity = Number(itemModalQuantity?.value || 0);
    const unitPrice = String(itemModalUnitPrice?.value || '').trim();

    if (!bedId) {
      errors.push('Vyber záhon.');
    }
    if (!quantity || quantity < 1) {
      errors.push('Zadej počet kusů.');
    }
    if (!unitPrice) {
      errors.push('Zadej cenu za kus.');
    }
    if (errors.length) {
      setModalErrors(itemModalForm, errors);
      return;
    }

    appendItemRow({ bedId, quantity, unitPrice });
    itemModalForm.reset();
    if (itemModalUnitPrice) {
      delete itemModalUnitPrice.dataset.userEdited;
    }
    setModalErrors(itemModalForm, []);
    renderItems();
    closeModal(resolveModal('order-item-modal'));
  });

  updateSummaryHeader();
  renderItems();
});
