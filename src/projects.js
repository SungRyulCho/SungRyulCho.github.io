"use strict";
(() => {
  const filters = document.querySelector('.categories');
  const buttons = [...filters.querySelectorAll('[data-category]')];
  const projects = [...document.querySelectorAll('.project')];
  const status = document.querySelector('#project-status');
  // Match the content above the role heading within each visible card row.
  const alignRoles = () => {
    const selectors = ['.project__period', '.project__heading', '.project__intro', '.project__stack'];
    projects.forEach(project => selectors.forEach(selector => {
      project.querySelector(selector).style.minHeight = '';
    }));
    if (window.matchMedia('(max-width: 768px)').matches) return;
    const rows = new Map();
    projects.filter(project => !project.hidden).forEach(project => {
      const top = Math.round(project.getBoundingClientRect().top);
      if (!rows.has(top)) rows.set(top, []);
      rows.get(top).push(project);
    });
    rows.forEach(row => selectors.forEach(selector => {
      const elements = row.map(project => project.querySelector(selector));
      const height = Math.max(...elements.map(element => element.getBoundingClientRect().height));
      elements.forEach(element => { element.style.minHeight = height + 'px'; });
    }));
  };
  window.addEventListener('resize', alignRoles);
  document.fonts.ready.then(alignRoles);

  const filter = (category, announce = true) => {
    buttons.forEach((button) => {
      const selected = button.dataset.category === category;
      button.classList.toggle('category--selected', selected);
      button.setAttribute('aria-pressed', String(selected));
    });
    projects.forEach((project) => {
      project.hidden = category === 'all'
        ? project.dataset.featured !== 'true'
        : project.dataset.type !== category;
    });
    alignRoles();
    if (announce) status.textContent = projects.filter((project) => !project.hidden).length + '개 프로젝트를 표시합니다.';
  };
  buttons.forEach((button) => {
    const category = button.dataset.category;
    const count = projects.filter((project) => category === 'all'
      ? project.dataset.featured === 'true' : project.dataset.type === category).length;
    button.querySelector('.category__count').textContent = count;
  });
  filters.hidden = false;
  filter('all', false);
  filters.addEventListener('click', (event) => {
    const button = event.target.closest('[data-category]');
    if (button && filters.contains(button)) filter(button.dataset.category);
  });
  const revealProject = (hash) => {
    const project = projects.find((item) => '#' + item.id === hash);
    if (project?.hidden) filter(project.dataset.type, false);
    return project;
  };
  document.addEventListener('click', (event) => {
    const link = event.target.closest('a[href^="#project-"]');
    if (link) revealProject(link.hash);
  });
  window.addEventListener('hashchange', () => {
    const project = revealProject(location.hash);
    if (project) project.scrollIntoView();
  });
  revealProject(location.hash);
})();
