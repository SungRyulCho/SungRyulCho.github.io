"use strict";
(() => {
  const filters = document.querySelector('.categories');
  const buttons = [...filters.querySelectorAll('[data-category]')];
  const projects = [...document.querySelectorAll('.project')];
  const status = document.querySelector('#project-status');
  const filter = (category, announce = true) => {
    buttons.forEach((button) => {
      const selected = button.dataset.category === category;
      button.classList.toggle('category--selected', selected);
      button.setAttribute('aria-pressed', String(selected));
    });
    projects.forEach((project) => {
      project.hidden = category !== 'all' && project.dataset.type !== category;
    });
    if (announce) status.textContent = projects.filter((project) => !project.hidden).length + '개 프로젝트를 표시합니다.';
  };
  filters.hidden = false;
  filters.addEventListener('click', (event) => {
    const button = event.target.closest('[data-category]');
    if (button && filters.contains(button)) filter(button.dataset.category);
  });
  // Restore hidden targets before native anchor navigation.
  const revealProject = (hash) => {
    if (projects.some((project) => '#' + project.id === hash)) filter('all', false);
  };
  document.addEventListener('click', (event) => {
    const link = event.target.closest('a[href^="#project-"]');
    if (link) revealProject(link.hash);
  });
  window.addEventListener('hashchange', () => {
    const project = projects.find((item) => '#' + item.id === location.hash);
    if (project?.hidden) {
      filter('all', false);
      project.scrollIntoView();
    }
  });
  revealProject(location.hash);
})();
