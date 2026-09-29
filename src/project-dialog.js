"use strict";
(() => {
  const dialog = document.querySelector('#dekk-case-dialog');
  const trigger = document.querySelector('#dekk-details-open');
  const project = document.querySelector('#project-dekk');
  // Keep native inline details usable without JavaScript or dialog support.
  if (!dialog || !trigger || !project || typeof dialog.showModal !== 'function') return;

  const fallback = project.querySelector('.project__detail');
  const cases = [...fallback.querySelectorAll('.project__case')];
  const tablist = dialog.querySelector('[role="tablist"]');
  const content = dialog.querySelector('.case-dialog__content');
  const closeButton = dialog.querySelector('.case-dialog__close');
  const root = document.documentElement;
  let selectedIndex = 0;
  let savedPosition = null;
  let pointerStartedOutside = false;

  // Move, rather than copy, the source articles: one copy of every paragraph,
  // evidence link and anchor ID, with inline fallback in the original HTML.
  const tabs = cases.map((panel, index) => {
    const tab = document.createElement('button');
    tab.type = 'button';
    tab.className = 'case-dialog__tab';
    tab.id = panel.id + '-tab';
    tab.textContent = panel.dataset.caseLabel;
    tab.setAttribute('role', 'tab');
    tab.setAttribute('aria-controls', panel.id);
    panel.setAttribute('role', 'tabpanel');
    panel.setAttribute('aria-labelledby', tab.id);
    panel.tabIndex = 0;
    tablist.append(tab);
    content.append(panel);
    tab.addEventListener('click', () => selectCase(index));
    return tab;
  });

  function selectCase(index, moveFocus = false) {
    selectedIndex = index;
    tabs.forEach((tab, position) => {
      const selected = position === index;
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
      cases[position].hidden = !selected;
    });
    content.scrollTop = 0;
    if (moveFocus) tabs[index].focus({preventScroll: true});
  }

  function restorePage() {
    if (!savedPosition) return;
    const {x, y} = savedPosition;
    savedPosition = null;
    root.classList.remove('case-dialog-open');
    root.style.removeProperty('--case-dialog-scroll-top');
    root.style.removeProperty('--case-dialog-scrollbar');
    window.scrollTo(x, y);
    trigger.focus({preventScroll: true});
  }

  function openCase(index = selectedIndex) {
    selectCase(index);
    if (!dialog.open) {
      savedPosition = {x: window.scrollX, y: window.scrollY};
      const scrollbar = window.innerWidth - root.clientWidth;
      root.style.setProperty('--case-dialog-scroll-top', -savedPosition.y + 'px');
      root.style.setProperty('--case-dialog-scrollbar', scrollbar + 'px');
      root.classList.add('case-dialog-open');
      try {
        dialog.showModal();
      } catch (error) {
        restorePage();
        throw error;
      }
    }
    tabs[index].focus({preventScroll: true});
  }

  tablist.addEventListener('keydown', (event) => {
    const index = tabs.indexOf(event.target);
    if (index < 0) return;
    const next = {
      ArrowRight: (index + 1) % tabs.length,
      ArrowLeft: (index - 1 + tabs.length) % tabs.length,
      Home: 0,
      End: tabs.length - 1,
    }[event.key];
    if (next === undefined) return;
    event.preventDefault();
    selectCase(next, true);
  });

  trigger.addEventListener('click', () => openCase());
  closeButton.addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', restorePage);
  // Keep keyboard traversal inside the visible case, including at both ends.
  dialog.addEventListener('keydown', (event) => {
    if (event.key !== 'Tab') return;
    const focusable = [...dialog.querySelectorAll('button, a[href], [tabindex="0"]')]
      .filter((element) => element.tabIndex >= 0 && !element.closest('[hidden]'));
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
  // Native modal dialog handles Escape and makes the background inert.
  const isOutside = (event) => {
    const rect = dialog.getBoundingClientRect();
    return event.target === dialog && (event.clientX < rect.left ||
      event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom);
  };
  dialog.addEventListener('pointerdown', (event) => {
    pointerStartedOutside = isOutside(event);
  });
  dialog.addEventListener('click', (event) => {
    if (pointerStartedOutside && isOutside(event)) dialog.close();
    pointerStartedOutside = false;
  });

  // Existing case URLs still open their matching case, including when the
  // project was hidden by a category filter. Tab changes do not alter history.
  const openFromHash = () => {
    const index = cases.findIndex((panel) => '#' + panel.id === location.hash);
    if (index < 0) return;
    if (project.hidden) document.querySelector('[data-category="all"]').click();
    openCase(index);
  };
  window.addEventListener('hashchange', openFromHash);
  window.addEventListener('load', openFromHash, {once: true});

  selectCase(0);
  fallback.open = false;
  fallback.hidden = true;
  trigger.hidden = false;
})();
