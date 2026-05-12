document.addEventListener('DOMContentLoaded', () => {
  const { initDatePicker, isInteractiveTarget, setModalErrors, syncBodyScrollLock } = window.HomeApp.utils;
  const modalRoot = document.getElementById('order-dashboard-modal-root');
  const confirmModal = document.getElementById('picked-up-confirm-modal');
  const deleteConfirmModal = document.getElementById('order-delete-confirm-modal');
  if (!modalRoot) {
    return;
  }

  const body = document.body;
  let pendingPickedUpForm = null;
  let pendingPickedUpCheckbox = null;
  let pendingDeleteForm = null;

  const closeModalContent = () => {
    modalRoot.innerHTML = '';
    syncBodyScrollLock();
  };

  const closeConfirmModal = () => {
    if (!confirmModal) {
      return;
    }

    confirmModal.classList.remove('is-open');
    confirmModal.setAttribute('aria-hidden', 'true');
    pendingPickedUpForm = null;
    if (pendingPickedUpCheckbox) {
      pendingPickedUpCheckbox.checked = false;
    }
    pendingPickedUpCheckbox = null;
    syncBodyScrollLock();
  };

  const closeDeleteConfirmModal = () => {
    if (!deleteConfirmModal) {
      return;
    }

    deleteConfirmModal.classList.remove('is-open');
    deleteConfirmModal.setAttribute('aria-hidden', 'true');
    pendingDeleteForm = null;
    syncBodyScrollLock();
  };

  const openConfirmModal = (form, checkbox) => {
    if (!confirmModal) {
      form.submit();
      return;
    }

    pendingPickedUpForm = form;
    pendingPickedUpCheckbox = checkbox;
    const customerTarget = confirmModal.querySelector('[data-confirm-customer-name]');
    if (customerTarget) {
      customerTarget.textContent = form.dataset.customerName || 'tohoto zákazníka';
    }

    confirmModal.classList.add('is-open');
    confirmModal.setAttribute('aria-hidden', 'false');
    syncBodyScrollLock();
  };

  const openDeleteConfirmModal = (form) => {
    if (!deleteConfirmModal) {
      form.dataset.confirmed = 'true';
      form.requestSubmit();
      return;
    }

    pendingDeleteForm = form;
    const customerTarget = deleteConfirmModal.querySelector('[data-delete-customer-name]');
    if (customerTarget) {
      customerTarget.textContent = form.dataset.customerName || 'tohoto zákazníka';
    }

    deleteConfirmModal.classList.add('is-open');
    deleteConfirmModal.setAttribute('aria-hidden', 'false');
    syncBodyScrollLock();
  };

  const bindOrderItemEditor = (modal) => {
    const itemStorage = modal.querySelector('#order-edit-items-storage');
    const totalFormsInput = modal.querySelector('input[name="order_items_edit-TOTAL_FORMS"]');
    const itemList = modal.querySelector('#order-edit-items-list');
    const emptyState = modal.querySelector('#order-edit-items-empty');
    const minError = modal.querySelector('#order-edit-items-min-error');
    const itemModal = modal.querySelector('#order-edit-item-modal');
    const itemModalForm = modal.querySelector('#order-edit-item-modal-form');
    if (!itemStorage || !totalFormsInput || !itemList || !itemModal || !itemModalForm) {
      return;
    }

    const itemModalTitle = itemModal.querySelector('[data-order-item-modal-title]');
    const itemModalSubmitLabel = itemModal.querySelector('[data-order-item-modal-submit-label]');
    const openItemTrigger = modal.querySelector('[data-open-order-item-modal]');
    const bedInput = itemModalForm.querySelector('select[name="order_item_modal-raised_bed"]');
    const quantityInput = itemModalForm.querySelector('input[name="order_item_modal-quantity"]');
    const unitPriceInput = itemModalForm.querySelector('input[name="order_item_modal-unit_price"]');

    const getItemRows = () => Array.from(itemStorage.querySelectorAll('[data-form-index]'));
    const getRowFields = (row) => ({
      id: row.querySelector('input[name$="-id"]'),
      bed: row.querySelector('[name$="-raised_bed"]'),
      quantity: row.querySelector('[name$="-quantity"]'),
      unitPrice: row.querySelector('[name$="-unit_price"]'),
      deleted: row.querySelector('[name$="-DELETE"]'),
    });

    const findBedLabel = (bedId) => {
      const option = Array.from(bedInput?.options || []).find((item) => item.value === String(bedId));
      return option?.text?.trim() || 'Záhon není vybraný';
    };

    const parseMoney = (value) => Number(String(value || '0').replace(',', '.'));
    const formatMoney = (value) => `${parseMoney(value).toFixed(2).replace('.', ',')} Kč`;

    const activeItems = () => {
      return getItemRows()
        .map((row) => ({ row, fields: getRowFields(row) }))
        .filter(({ fields }) => fields.bed && fields.quantity && !(fields.deleted && fields.deleted.checked))
        .map(({ row, fields }) => ({
          index: row.dataset.formIndex,
          bedId: fields.bed.value,
          bedLabel: findBedLabel(fields.bed.value),
          quantity: Number(fields.quantity.value || 0),
          unitPrice: parseMoney(fields.unitPrice.value),
        }))
        .filter((item) => item.bedId && item.quantity > 0);
    };

    const renderItems = () => {
      const items = activeItems();
      itemList.innerHTML = items
        .map(
          (item) => `
            <article class="item-summary-card" data-form-index="${item.index}">
              <div class="item-summary-main">
                <strong>${item.bedLabel}</strong>
                <span>${item.quantity} ks</span>
              </div>
              <div class="item-summary-side">
                <span>${formatMoney(item.unitPrice)} / ks</span>
                <div class="item-summary-actions">
                  <button type="button" class="button button-link" data-order-item-edit="${item.index}">Upravit</button>
                  <button type="button" class="button button-link" data-order-item-remove="${item.index}">Odebrat</button>
                </div>
              </div>
            </article>
          `
        )
        .join('');

      const hasItems = items.length > 0;
      emptyState.classList.toggle('is-hidden', hasItems);
      minError?.classList.toggle('is-hidden', hasItems);
    };

    const closeItemModal = () => {
      itemModal.classList.remove('is-open');
      itemModal.setAttribute('aria-hidden', 'true');
      itemModalForm.reset();
      delete itemModalForm.dataset.editIndex;
      setModalErrors(itemModalForm, []);
      syncBodyScrollLock();
    };

    const openItemModal = (index = null) => {
      setModalErrors(itemModalForm, []);

      if (index !== null) {
        const row = itemStorage.querySelector(`[data-form-index="${index}"]`);
        const fields = row ? getRowFields(row) : null;
        if (!fields) {
          return;
        }

        itemModalForm.dataset.editIndex = String(index);
        if (itemModalTitle) {
          itemModalTitle.textContent = 'Úprava položky objednávky';
        }
        if (itemModalSubmitLabel) {
          itemModalSubmitLabel.textContent = 'Uložit položku';
        }
        if (bedInput) {
          bedInput.value = fields.bed.value;
        }
        if (quantityInput) {
          quantityInput.value = fields.quantity.value;
        }
        if (unitPriceInput) {
          unitPriceInput.value = String(fields.unitPrice.value || '').replace(',', '.');
        }
      } else {
        itemModalForm.reset();
        delete itemModalForm.dataset.editIndex;
        if (itemModalTitle) {
          itemModalTitle.textContent = 'Přidání položky objednávky';
        }
        if (itemModalSubmitLabel) {
          itemModalSubmitLabel.textContent = 'Přidat položku';
        }
      }

      itemModal.classList.add('is-open');
      itemModal.setAttribute('aria-hidden', 'false');
      syncBodyScrollLock();
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
      const index = Number(totalFormsInput.value || 0);
      const row = document.createElement('div');
      row.className = 'stored-item-row';
      row.dataset.orderItem = 'true';
      row.dataset.formIndex = String(index);
      addHiddenInput(row, `order_items_edit-${index}-id`, '');
      addHiddenInput(row, `order_items_edit-${index}-raised_bed`, String(bedId));
      addHiddenInput(row, `order_items_edit-${index}-quantity`, String(quantity));
      addHiddenInput(row, `order_items_edit-${index}-unit_price`, String(unitPrice).replace('.', ','));
      const deleteInput = addHiddenInput(row, `order_items_edit-${index}-DELETE`, 'on', 'checkbox');
      deleteInput.checked = false;
      itemStorage.appendChild(row);
      totalFormsInput.value = String(index + 1);
    };

    openItemTrigger?.addEventListener('click', () => openItemModal());

    itemList.addEventListener('click', (event) => {
      const editButton = event.target.closest('[data-order-item-edit]');
      if (editButton) {
        openItemModal(editButton.getAttribute('data-order-item-edit'));
        return;
      }

      const removeButton = event.target.closest('[data-order-item-remove]');
      if (!removeButton) {
        return;
      }

      const row = itemStorage.querySelector(`[data-form-index="${removeButton.getAttribute('data-order-item-remove')}"]`);
      const deleteInput = row?.querySelector('[name$="-DELETE"]');
      if (deleteInput) {
        deleteInput.checked = true;
      }
      renderItems();
    });

    itemModal.querySelectorAll('[data-order-item-modal-close]').forEach((control) => {
      control.addEventListener('click', closeItemModal);
    });

    itemModal.addEventListener('click', (event) => {
      if (event.target === itemModal) {
        closeItemModal();
      }
    });

    itemModalForm.addEventListener('submit', (event) => {
      event.preventDefault();
      const bedId = bedInput?.value || '';
      const quantity = Number(quantityInput?.value || 0);
      const unitPrice = String(unitPriceInput?.value || '').trim();
      const errors = [];

      if (!bedId) {
        errors.push('Vyberte záhon.');
      }
      if (!quantity || quantity < 1) {
        errors.push('Množství musí být alespoň 1 ks.');
      }
      if (unitPrice === '' || Number.isNaN(parseMoney(unitPrice)) || parseMoney(unitPrice) < 0) {
        errors.push('Cena za kus musí být vyplněná a nesmí být záporná.');
      }

      if (errors.length) {
        setModalErrors(itemModalForm, errors);
        return;
      }

      const editIndex = itemModalForm.dataset.editIndex;
      if (editIndex !== undefined) {
        const row = itemStorage.querySelector(`[data-form-index="${editIndex}"]`);
        const fields = row ? getRowFields(row) : null;
        if (fields) {
          fields.bed.value = bedId;
          fields.quantity.value = String(quantity);
          fields.unitPrice.value = unitPrice.replace(',', '.');
          if (fields.deleted) {
            fields.deleted.checked = false;
          }
        }
      } else {
        appendItemRow({ bedId, quantity, unitPrice: unitPrice.replace(',', '.') });
      }

      closeItemModal();
      renderItems();
    });

    renderItems();
  };

  const bindModal = () => {
    const modal = modalRoot.querySelector('.modal');
    if (!modal) {
      return;
    }

    modal.classList.add('is-open');
    syncBodyScrollLock();
    initDatePicker(modal.querySelector('input[name="order_edit-ordered_date"]'));
    initDatePicker(modal.querySelector('input[name="order_edit-pickup_date"]'));
    bindOrderItemEditor(modal);

    modal.querySelectorAll('[data-order-edit-close]').forEach((control) => {
      control.addEventListener('click', closeModalContent);
    });

    modal.addEventListener('click', (event) => {
      if (event.target === modal) {
        closeModalContent();
      }
    });

    const form = modal.querySelector('#order-edit-modal-form');
    form?.addEventListener('submit', async (event) => {
      event.preventDefault();
      const response = await fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        },
      });

      const contentType = response.headers.get('content-type') || '';
      if (response.ok && contentType.includes('application/json')) {
        window.location.reload();
        return;
      }

      modalRoot.innerHTML = await response.text();
      bindModal();
    });
  };

  const openOrderModal = async (url) => {
    const response = await fetch(url, {
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
      },
    });
    modalRoot.innerHTML = await response.text();
    bindModal();
  };

  const bindPickedUpConfirmForms = () => {
    document.querySelectorAll('form[data-confirm-picked-up-toggle]').forEach((form) => {
      if (form.dataset.confirmBound === 'true') {
        return;
      }

      const checkbox = form.querySelector('[data-picked-up-checkbox]');
      if (!checkbox) {
        return;
      }

      form.dataset.confirmBound = 'true';
      checkbox.addEventListener('change', () => {
        if (!checkbox.checked) {
          return;
        }

        openConfirmModal(form, checkbox);
      });
    });
  };

  const bindOrderDeleteForms = () => {
    document.querySelectorAll('form[data-confirm-order-delete]').forEach((form) => {
      if (form.dataset.confirmBound === 'true') {
        return;
      }

      form.dataset.confirmBound = 'true';
      form.addEventListener('submit', (event) => {
        if (form.dataset.confirmed === 'true') {
          delete form.dataset.confirmed;
          return;
        }

        event.preventDefault();
        openDeleteConfirmModal(form);
      });
    });
  };

  const bindConfirmModal = () => {
    if (!confirmModal) {
      return;
    }

    confirmModal.querySelectorAll('[data-modal-close]').forEach((control) => {
      control.addEventListener('click', closeConfirmModal);
    });

    confirmModal.addEventListener('click', (event) => {
      if (event.target === confirmModal) {
        closeConfirmModal();
      }
    });

    confirmModal.querySelector('[data-confirm-submit]')?.addEventListener('click', () => {
      if (!pendingPickedUpForm) {
        closeConfirmModal();
        return;
      }

      const formToSubmit = pendingPickedUpForm;
      const checkboxToKeep = pendingPickedUpCheckbox;
      pendingPickedUpCheckbox = null;
      closeConfirmModal();
      if (checkboxToKeep) {
        checkboxToKeep.checked = true;
      }
      formToSubmit.submit();
    });
  };

  const bindDeleteConfirmModal = () => {
    if (!deleteConfirmModal) {
      return;
    }

    deleteConfirmModal.querySelectorAll('[data-order-delete-close]').forEach((control) => {
      control.addEventListener('click', closeDeleteConfirmModal);
    });

    deleteConfirmModal.addEventListener('click', (event) => {
      if (event.target === deleteConfirmModal) {
        closeDeleteConfirmModal();
      }
    });

    deleteConfirmModal.querySelector('[data-order-delete-submit]')?.addEventListener('click', () => {
      if (!pendingDeleteForm) {
        closeDeleteConfirmModal();
        return;
      }

      const formToSubmit = pendingDeleteForm;
      closeDeleteConfirmModal();
      formToSubmit.dataset.confirmed = 'true';
      formToSubmit.requestSubmit();
    });
  };

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      if (confirmModal?.classList.contains('is-open')) {
        closeConfirmModal();
        return;
      }

      if (deleteConfirmModal?.classList.contains('is-open')) {
        closeDeleteConfirmModal();
        return;
      }

      const nestedItemModal = modalRoot.querySelector('#order-edit-item-modal.is-open');
      if (nestedItemModal) {
        nestedItemModal.classList.remove('is-open');
        nestedItemModal.setAttribute('aria-hidden', 'true');
        syncBodyScrollLock();
        return;
      }

      closeModalContent();
    }
  });

  document.querySelectorAll('[data-order-edit-url]').forEach((card) => {
    const url = card.getAttribute('data-order-edit-url');
    if (!url) {
      return;
    }

    card.addEventListener('click', (event) => {
      if (isInteractiveTarget(event.target)) {
        return;
      }
      openOrderModal(url);
    });

    card.addEventListener('keydown', (event) => {
      if ((event.key === 'Enter' || event.key === ' ') && !isInteractiveTarget(event.target)) {
        event.preventDefault();
        openOrderModal(url);
      }
    });
  });

  bindConfirmModal();
  bindDeleteConfirmModal();
  bindPickedUpConfirmForms();
  bindOrderDeleteForms();
});