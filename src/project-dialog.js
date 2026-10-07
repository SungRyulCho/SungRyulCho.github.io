"use strict";
(() => {
  const dialog = document.querySelector('#project-case-dialog');
  // Keep native inline details usable without JavaScript or dialog support.
  if (!dialog || typeof dialog.showModal !== 'function') return;

  const tablist = dialog.querySelector('[role="tablist"]');
  const content = dialog.querySelector('.case-dialog__content');
  const closeButton = dialog.querySelector('.case-dialog__close');
  const projectLabel = dialog.querySelector('.case-dialog__project');
  const projectMeta = dialog.querySelector('.case-dialog__meta');
  const root = document.documentElement;
  let activeEntry = null;
  let savedPosition = null;
  let pointerStartedOutside = false;

  // Cards explain the developer's scope in the service flow. Their only detail
  // action opens improvement cases, with native inline details as a fallback.
  const entries = [...document.querySelectorAll('.project')].map((project) => {
      const trigger = project.querySelector('.project__detail-trigger');
      const fallback = project.querySelector('.project__detail');
      const body = fallback?.querySelector('.project__cases');
      if (!trigger || !body) return null;
      const entry = {
        project, trigger, body,
        name: project.querySelector('.project__title').textContent,
        cases: [...body.querySelectorAll('.project__case')],
        repository: body.querySelector('.project__link'),
        tabs: [],
        selectedIndex: 0,
      };
      // A repository belongs to the project, not to an individual case.
      // Move the original link so the non-JavaScript fallback stays intact.
      if (entry.repository) {
        entry.repository.classList.add('case-dialog__repository');
        entry.repository.textContent = 'GitHub ↗';
        entry.repository.hidden = true;
        projectMeta.append(entry.repository);
      }
      if (entry.cases.length > 1) {
        entry.tabs = entry.cases.map((panel, index) => {
          const tab = document.createElement('button');
          tab.type = 'button';
          tab.className = 'case-dialog__tab';
          tab.id = panel.id + '-tab';
          tab.textContent = panel.dataset.caseLabel;
          tab.setAttribute('role', 'tab');
          tab.setAttribute('aria-controls', panel.id);
          tab.hidden = true;
          panel.setAttribute('role', 'tabpanel');
          panel.setAttribute('aria-labelledby', tab.id);
          panel.tabIndex = 0;
          tablist.append(tab);
          tab.addEventListener('click', () => selectCase(index));
          return tab;
        });
      }
      body.hidden = true;
      content.append(body);
      fallback.open = false;
      fallback.hidden = true;
      trigger.hidden = false;
      trigger.addEventListener('click', () => openProject(entry));
      return entry;
  }).filter(Boolean);

  function selectCase(index, moveFocus = false) {
    const {tabs, cases} = activeEntry;
    activeEntry.selectedIndex = index;
    cases.forEach((panel, position) => { panel.hidden = position !== index; });
    tabs.forEach((tab, position) => {
      const selected = position === index;
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
    });
    content.scrollTop = 0;
    if (moveFocus) tabs[index].focus({preventScroll: true});
  }

  function restorePage() {
    if (!savedPosition) return;
    const {x, y, trigger} = savedPosition;
    savedPosition = null;
    root.classList.remove('case-dialog-open');
    root.style.removeProperty('--case-dialog-scroll-top');
    root.style.removeProperty('--case-dialog-scrollbar');
    window.scrollTo(x, y);
    trigger.focus({preventScroll: true});
  }

  function openProject(entry, index = entry.selectedIndex) {
    activeEntry = entry;
    entries.forEach((item) => {
      item.body.hidden = item !== entry;
      if (item.repository) item.repository.hidden = item !== entry;
      item.tabs.forEach((tab) => { tab.hidden = item !== entry; });
    });
    projectLabel.textContent = entry.name;
    closeButton.setAttribute('aria-label', entry.name + ' 상세 닫기');
    tablist.setAttribute('aria-label', entry.name + ' 개선 사례');
    tablist.style.setProperty('--case-count', entry.tabs.length || 1);
    tablist.hidden = entry.tabs.length === 0;
    selectCase(index);
    if (!dialog.open) {
      savedPosition = {x: window.scrollX, y: window.scrollY, trigger: entry.trigger};
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
    (entry.tabs[index] || closeButton).focus({preventScroll: true});
  }

  tablist.addEventListener('keydown', (event) => {
    if (!activeEntry) return;
    const {tabs} = activeEntry;
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
    for (const entry of entries) {
      const index = entry.cases.findIndex((panel) => '#' + panel.id === location.hash);
      if (index < 0) continue;
      if (entry.project.hidden) document.querySelector('[data-category="all"]').click();
      openProject(entry, index);
      break;
    }
  };
  window.addEventListener('hashchange', openFromHash);
  window.addEventListener('load', openFromHash, {once: true});
})();
