(() => {
  const root = document.documentElement;
  const themePreference = root.dataset.themePreference;
  const systemTheme = window.matchMedia?.('(prefers-color-scheme: dark)');

  const applySystemTheme = () => {
    if (root.dataset.themePreference !== 'auto') return;
    root.dataset.theme = systemTheme?.matches ? 'dark' : 'light';
  };

  applySystemTheme();
  if (themePreference === 'auto' && systemTheme) {
    systemTheme.addEventListener?.('change', applySystemTheme);
  }

  document.querySelectorAll('[data-clear-session-form]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      const confirmed = window.confirm('ต้องการล้างข้อมูลบริษัทของงานปัจจุบันหรือไม่?');
      if (!confirmed) event.preventDefault();
    });
  });

  const sharedFields = [...document.querySelectorAll('[data-shared-key]')];

  const syncSharedFields = (source) => {
    const sharedKey = source.dataset.sharedKey;
    if (!sharedKey) return;

    sharedFields
      .filter((field) => field !== source && field.dataset.sharedKey === sharedKey)
      .forEach((field) => {
        if (field.value !== source.value) field.value = source.value;
      });
  };

  const normalizeNumericField = (field) => {
    if (!field.matches('[data-number-only]')) return;
    const digitsOnly = field.value.replace(/[^0-9]/g, '');
    if (field.value !== digitsOnly) field.value = digitsOnly;
  };

  sharedFields.forEach((field) => {
    field.addEventListener('input', () => {
      normalizeNumericField(field);
      syncSharedFields(field);
    });
    field.addEventListener('change', () => {
      normalizeNumericField(field);
      syncSharedFields(field);
    });
  });

  const dateDisplays = [...document.querySelectorAll('[data-date-display]')];

  const parseDateInput = (value) => {
    const text = value.trim();
    if (!text) return '';

    const isoMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text);
    const parts = isoMatch
      ? [Number(isoMatch[3]), Number(isoMatch[2]), Number(isoMatch[1])]
      : text.split('/').map(Number);
    if (parts.length !== 3 || parts.some((part) => !Number.isInteger(part))) return '';

    let [day, month, year] = parts;
    if (!isoMatch && year >= 2400) year -= 543;
    const parsed = new Date(Date.UTC(year, month - 1, day));
    if (
      parsed.getUTCFullYear() !== year
      || parsed.getUTCMonth() !== month - 1
      || parsed.getUTCDate() !== day
    ) return '';
    return `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  };

  const formatThaiDateInput = (isoValue) => {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(isoValue);
    if (!match) return '';
    const [, year, month, day] = match;
    return `${day}/${month}/${Number(year) + 543}`;
  };

  const syncNativeDate = (display) => {
    const native = document.getElementById(display.dataset.dateNativeTarget ?? '');
    if (!native) return;
    const parsed = parseDateInput(display.value);
    native.value = parsed;
  };

  dateDisplays.forEach((display) => {
    display.addEventListener('input', () => {
      const normalized = display.value.replace(/[^0-9/]/g, '');
      if (display.value !== normalized) display.value = normalized;
      if (!display.value.trim() || parseDateInput(display.value)) {
        display.setCustomValidity('');
        syncNativeDate(display);
      }
    });

    display.addEventListener('change', () => {
      const isValid = !display.value.trim() || Boolean(parseDateInput(display.value));
      display.setCustomValidity(isValid ? '' : 'กรุณาใช้รูปแบบ วว/ดด/พ.ศ. เช่น 01/09/2569');
      if (isValid) syncNativeDate(display);
    });
  });

  document.querySelectorAll('[data-date-native]').forEach((native) => {
    native.addEventListener('change', () => {
      const display = document.querySelector(`[data-date-native-target="${native.id}"]`);
      if (!display) return;
      display.value = formatThaiDateInput(native.value);
      display.setCustomValidity('');
      display.dispatchEvent(new Event('input', { bubbles: true }));
    });
  });

  document.querySelectorAll('[data-date-trigger]').forEach((trigger) => {
    trigger.addEventListener('click', () => {
      const native = document.getElementById(trigger.dataset.dateTrigger ?? '');
      if (!native) return;
      try {
        if (typeof native.showPicker === 'function') native.showPicker();
        else native.click();
      } catch {
        native.focus();
      }
    });
  });

  dateDisplays[0]?.form?.addEventListener('submit', (event) => {
    let hasInvalidDate = false;
    dateDisplays.forEach((display) => {
      const isValid = !display.value.trim() || Boolean(parseDateInput(display.value));
      display.setCustomValidity(isValid ? '' : 'กรุณาใช้รูปแบบ วว/ดด/พ.ศ. เช่น 01/09/2569');
      if (!isValid) hasInvalidDate = true;
      if (isValid) syncNativeDate(display);
    });
    if (hasInvalidDate) event.preventDefault();
  });

  const tabs = [...document.querySelectorAll('[data-document-tab]')];
  const panels = [...document.querySelectorAll('[data-document-panel]')];

  const activateDocumentTab = (tab, moveFocus = false) => {
    const targetId = tab.dataset.documentTab;
    if (!targetId) return;

    tabs.forEach((item) => {
      const isActive = item === tab;
      item.classList.toggle('is-active', isActive);
      item.setAttribute('aria-selected', String(isActive));
      item.tabIndex = isActive ? 0 : -1;
    });
    panels.forEach((panel) => {
      panel.hidden = panel.id !== targetId;
      panel.classList.toggle('is-active', panel.id === targetId);
    });
    if (moveFocus) tab.focus();
  };

  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => activateDocumentTab(tab));
    tab.addEventListener('keydown', (event) => {
      if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      const targetIndex = event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? tabs.length - 1
          : event.key === 'ArrowDown'
            ? (index + 1) % tabs.length
            : (index - 1 + tabs.length) % tabs.length;
      activateDocumentTab(tabs[targetIndex], true);
    });
  });

  const hashTab = tabs.find((tab) => `#${tab.id}` === window.location.hash);
  if (hashTab) activateDocumentTab(hashTab);

  const documentStatusTabs = tabs;
  const updateDocumentStatuses = () => {
    documentStatusTabs.forEach((tab) => {
      const panel = document.getElementById(tab.dataset.documentTab ?? '');
      const fields = panel ? [...panel.querySelectorAll('[data-document-field]')] : [];
      const complete = fields.length === 0 || fields.every((field) => field.value.trim());
      const statusDot = tab.querySelector('[data-document-status]');
      statusDot?.classList.toggle('is-complete', complete);
      statusDot?.classList.toggle('is-incomplete', !complete);
      const title = tab.dataset.documentTitle ?? 'เอกสาร';
      tab.setAttribute('aria-label', `${title} - ${complete ? 'กรอกข้อมูลครบแล้ว' : 'กรอกข้อมูลยังไม่ครบ'}`);
    });
  };

  document.querySelectorAll('[data-document-field]').forEach((field) => {
    field.addEventListener('input', updateDocumentStatuses);
    field.addEventListener('change', updateDocumentStatuses);
  });
  updateDocumentStatuses();

  const reviewItems = [...document.querySelectorAll('[data-review-document]')];
  const reviewButtons = [...document.querySelectorAll('[data-review-document-button]')];
  const reviewPanels = [...document.querySelectorAll('[data-review-panel]')];
  const reviewSearch = document.querySelector('[data-review-search]');
  const reviewFilters = [...document.querySelectorAll('[data-review-filter]')];
  const reviewEmpty = document.querySelector('[data-review-empty]');

  if (reviewItems.length && reviewButtons.length && reviewPanels.length) {
    let activeReviewFilter = 'all';

    const activateReviewDocument = (button, moveFocus = false) => {
      const panelId = button.getAttribute('aria-controls');
      if (!panelId) return;

      reviewButtons.forEach((item) => {
        const isActive = item === button;
        item.classList.toggle('is-active', isActive);
        item.setAttribute('aria-pressed', String(isActive));
        item.tabIndex = isActive ? 0 : -1;
      });
      reviewPanels.forEach((panel) => {
        const isActive = panel.id === panelId;
        panel.hidden = !isActive;
        panel.classList.toggle('is-active', isActive);
      });
      if (moveFocus) button.focus();
    };

    const visibleReviewButtons = () => reviewButtons.filter((button) => {
      const item = button.closest('[data-review-document]');
      return item && !item.hidden;
    });

    const applyReviewFilter = () => {
      const query = reviewSearch?.value.trim().toLocaleLowerCase() ?? '';
      let visibleCount = 0;

      reviewItems.forEach((item) => {
        const title = (item.dataset.reviewTitle ?? '').toLocaleLowerCase();
        const matchesQuery = !query || title.includes(query);
        const matchesStatus = activeReviewFilter === 'all'
          || item.dataset.reviewStatus === activeReviewFilter;
        item.hidden = !(matchesQuery && matchesStatus);
        if (!item.hidden) visibleCount += 1;
      });

      if (reviewEmpty) reviewEmpty.hidden = visibleCount > 0;
      const activeButton = reviewButtons.find((button) => button.classList.contains('is-active'));
      const activeItem = activeButton?.closest('[data-review-document]');
      const nextButton = visibleReviewButtons()[0];
      if (nextButton && (!activeItem || activeItem.hidden)) activateReviewDocument(nextButton);
      if (!nextButton) {
        reviewButtons.forEach((button) => {
          button.classList.remove('is-active');
          button.setAttribute('aria-pressed', 'false');
          button.tabIndex = -1;
        });
        reviewPanels.forEach((panel) => { panel.hidden = true; });
      }
    };

    reviewButtons.forEach((button) => {
      button.addEventListener('click', () => activateReviewDocument(button));
      button.addEventListener('keydown', (event) => {
        if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
        event.preventDefault();
        const visibleButtons = visibleReviewButtons();
        const currentIndex = visibleButtons.indexOf(button);
        if (currentIndex < 0) return;
        const targetIndex = event.key === 'Home'
          ? 0
          : event.key === 'End'
            ? visibleButtons.length - 1
            : event.key === 'ArrowDown'
              ? (currentIndex + 1) % visibleButtons.length
              : (currentIndex - 1 + visibleButtons.length) % visibleButtons.length;
        activateReviewDocument(visibleButtons[targetIndex], true);
      });
    });

    reviewFilters.forEach((filterButton) => {
      filterButton.addEventListener('click', () => {
        activeReviewFilter = filterButton.dataset.reviewFilter ?? 'all';
        reviewFilters.forEach((item) => {
          const isActive = item === filterButton;
          item.classList.toggle('is-active', isActive);
          item.setAttribute('aria-pressed', String(isActive));
        });
        applyReviewFilter();
      });
    });

    reviewSearch?.addEventListener('input', applyReviewFilter);
    applyReviewFilter();
  }

  const orderList = document.querySelector('[data-order-list]');
  const orderForm = document.querySelector('[data-document-order-form]');
  const orderInput = document.querySelector('[data-order-input]');
  const orderStatus = document.querySelector('[data-order-status]');

  if (orderList && orderForm && orderInput) {
    let draggedItem = null;
    let dropTarget = null;

    const orderItems = () => [...orderList.querySelectorAll('[data-order-item]')];

    const announceOrder = (message) => {
      if (orderStatus) orderStatus.textContent = message;
    };

    const syncOrderState = () => {
      const items = orderItems();
      items.forEach((item, index) => {
        const position = item.querySelector('[data-order-position]');
        if (position) position.value = String(index + 1).padStart(2, '0');
      });
      orderInput.value = items
        .map((item) => item.dataset.documentId)
        .filter(Boolean)
        .join(',');
    };

    const clearDropTarget = () => {
      dropTarget?.classList.remove('is-drop-target');
      dropTarget = null;
    };

    const moveItemToPosition = (item, rawPosition, shouldAnnounce = true) => {
      const items = orderItems();
      const currentIndex = items.indexOf(item);
      if (currentIndex < 0) return;

      const parsedPosition = Number.parseInt(rawPosition, 10);
      const targetIndex = Number.isNaN(parsedPosition)
        ? currentIndex
        : Math.min(Math.max(parsedPosition, 1), items.length) - 1;
      const targetItem = items[targetIndex];

      if (targetItem && targetItem !== item) {
        const reference = currentIndex < targetIndex ? targetItem.nextElementSibling : targetItem;
        if (reference !== item) orderList.insertBefore(item, reference);
      }

      syncOrderState();
      if (shouldAnnounce && targetIndex !== currentIndex) {
        announceOrder(`ย้าย ${item.querySelector('strong')?.textContent ?? 'เอกสาร'} ไปอยู่ลำดับ ${targetIndex + 1}`);
      }
    };

    const findOrderItem = (target) => target instanceof Element
      ? target.closest('[data-order-item]')
      : null;

    orderList.querySelectorAll('[data-order-position]').forEach((position) => {
      position.addEventListener('input', () => {
        const digitsOnly = position.value.replace(/[^0-9]/g, '');
        if (position.value !== digitsOnly) position.value = digitsOnly;
      });
      position.addEventListener('change', () => {
        const item = position.closest('[data-order-item]');
        if (item) moveItemToPosition(item, position.value);
      });
      position.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter') return;
        event.preventDefault();
        position.blur();
      });
    });

    orderList.addEventListener('dragstart', (event) => {
      const item = findOrderItem(event.target);
      if (!item) return;
      draggedItem = item;
      item.classList.add('is-dragging');
      if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', item.dataset.documentId ?? '');
      }
    });

    orderList.addEventListener('dragover', (event) => {
      if (!draggedItem) return;
      event.preventDefault();
      const target = findOrderItem(event.target);
      if (!target || target === draggedItem) return;

      clearDropTarget();
      const bounds = target.getBoundingClientRect();
      const insertAfter = event.clientY > bounds.top + bounds.height / 2;
      const reference = insertAfter ? target.nextElementSibling : target;
      if (reference !== draggedItem) orderList.insertBefore(draggedItem, reference);
      target.classList.add('is-drop-target');
      dropTarget = target;
      syncOrderState();
    });

    orderList.addEventListener('drop', (event) => {
      if (!draggedItem) return;
      event.preventDefault();
      syncOrderState();
      announceOrder('จัดลำดับเอกสารแล้ว');
    });

    orderList.addEventListener('dragend', () => {
      draggedItem?.classList.remove('is-dragging');
      clearDropTarget();
      draggedItem = null;
      syncOrderState();
    });

    orderForm.addEventListener('submit', () => {
      const activePosition = document.activeElement?.matches('[data-order-position]')
        ? document.activeElement
        : null;
      const activeItem = activePosition?.closest('[data-order-item]');
      if (activeItem && activePosition) moveItemToPosition(activeItem, activePosition.value, false);
      syncOrderState();
    });

    syncOrderState();
  }

  const modal = document.querySelector('#settings-modal');
  const triggers = [...document.querySelectorAll('[data-settings-open]')];
  if (!modal || triggers.length === 0) return;

  const closeControls = [...modal.querySelectorAll('[data-settings-close]')];
  let lastFocusedElement = null;

  const focusableElements = () => [...modal.querySelectorAll(
    'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])'
  )].filter((element) => !element.hidden && element.offsetParent !== null);

  const openModal = () => {
    lastFocusedElement = document.activeElement;
    modal.hidden = false;
    document.body.classList.add('modal-open');
    triggers.forEach((trigger) => trigger.setAttribute('aria-expanded', 'true'));
    const firstControl = modal.querySelector('select, input, button');
    firstControl?.focus();
  };

  const closeModal = () => {
    modal.hidden = true;
    document.body.classList.remove('modal-open');
    triggers.forEach((trigger) => trigger.setAttribute('aria-expanded', 'false'));
    lastFocusedElement?.focus();
  };

  const handleKeydown = (event) => {
    if (modal.hidden) return;

    if (event.key === 'Escape') {
      event.preventDefault();
      closeModal();
      return;
    }

    if (event.key !== 'Tab') return;
    const focusables = focusableElements();
    if (focusables.length === 0) return;

    const first = focusables[0];
    const last = focusables.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last?.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  triggers.forEach((trigger) => trigger.addEventListener('click', openModal));
  closeControls.forEach((control) => control.addEventListener('click', closeModal));
  document.addEventListener('keydown', handleKeydown);
})();
