"use strict";
(() => {
  const links = [...document.querySelectorAll('.header__menu__item')];
  const sections = links.map((link) => document.querySelector(link.hash));
  let scheduled = false;
  const update = () => {
    const marker = document.querySelector('.header').offsetHeight + 48;
    let active = sections[0];
    for (const section of sections) {
      if (section.getBoundingClientRect().top <= marker) active = section;
    }
    if (window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 4) active = sections.at(-1);
    links.forEach((link) => {
      const selected = link.hash === '#' + active.id;
      link.classList.toggle('active', selected);
      if (selected) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
    scheduled = false;
  };
  const schedule = () => {
    if (!scheduled) { scheduled = true; requestAnimationFrame(update); }
  };
  window.addEventListener('scroll', schedule, {passive:true});
  window.addEventListener('resize', schedule);
  window.addEventListener('hashchange', schedule);
  window.addEventListener('load', schedule);
  update();
})();
