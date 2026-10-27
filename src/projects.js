"use strict";
(() => {
  const filters = document.querySelector('.categories');
  const buttons = [...filters.querySelectorAll('[data-category]')];
  const projects = [...document.querySelectorAll('.project')];
  const status = document.querySelector('#project-status');
  const track = document.querySelector('.projects');
  const viewport = document.createElement('div');
  viewport.className = 'project-carousel';
  viewport.tabIndex = 0;
  viewport.setAttribute('aria-label', '프로젝트 목록. 트랙패드 좌우 스크롤, 방향키 또는 터치 드래그로 이동');
  track.before(viewport);
  viewport.append(track);
  const shell = document.createElement('div');
  shell.className = 'project-carousel-shell';
  viewport.before(shell);
  shell.append(viewport);
  const controls = document.createElement('div');
  controls.className = 'project-carousel-controls';
  controls.innerHTML = '<button type="button" class="project-carousel-arrow project-carousel-arrow--previous" aria-label="이전 프로젝트" title="클릭하면 한 장 이동, 길게 누르면 연속 이동"><svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="m15 6-6 6 6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button><button type="button" class="project-carousel-arrow project-carousel-arrow--next" aria-label="다음 프로젝트" title="클릭하면 한 장 이동, 길게 누르면 연속 이동"><svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="m9 6 6 6-6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>';
  shell.append(controls);
  let category = 'all';
  let offset = 0;
  let position = 0;
  let frame = 0;
  let velocity = 0;
  let step = 1;
  const items = () => projects.filter(p => category === 'all' || p.dataset.type === category);
  // Measure every card together so filtering does not change card height or role alignment.
  const alignRoles = () => {
    const fields = ['.project__period', '.project__heading', '.project__intro', '.project__stack'];
    const hidden = projects.map(p => p.hidden);
    projects.forEach(p => { p.hidden = false; p.style.minHeight = ''; fields.forEach(f => p.querySelector(f).style.minHeight = ''); });
    fields.forEach(f => {
      const height = Math.max(...projects.map(p => p.querySelector(f).getBoundingClientRect().height));
      projects.forEach(p => p.querySelector(f).style.minHeight = height + 'px');
    });
    const height = Math.max(...projects.map(p => p.getBoundingClientRect().height));
    projects.forEach((p, i) => { p.style.minHeight = height + 'px'; p.hidden = hidden[i]; });
  };
  const stop = () => { cancelAnimationFrame(frame); frame = 0; velocity = 0; };
  const paint = () => { track.style.transform = `translate3d(${-position}px,0,0)`; };
  const render = () => {
    track.querySelectorAll('[data-loop-copy]').forEach(p => p.remove());
    const selected = items();
    projects.forEach(p => { p.hidden = !selected.includes(p); });
    const ordered = selected.slice(offset).concat(selected.slice(0, offset));
    ordered.forEach(p => track.append(p));
    step = ordered[0].getBoundingClientRect().width + parseFloat(getComputedStyle(track).gap);
    // Only the trailing edge needs visual copies; all full cards are original nodes.
    if (selected.length > 1) ordered.slice(0, 3).forEach(p => {
      const copy = p.cloneNode(true);
      copy.dataset.loopCopy = p.id;
      copy.removeAttribute('id');
      copy.setAttribute('aria-hidden', 'true');
      copy.querySelectorAll('[id]').forEach(el => el.removeAttribute('id'));
      copy.querySelectorAll('a, button, summary, [tabindex]').forEach(el => el.tabIndex = -1);
      copy.querySelectorAll('button').forEach((button, i) => button.addEventListener('click', () => p.querySelectorAll('button')[i]?.click()));
      track.append(copy);
    });
    controls.hidden = selected.length < 2;
    viewport.classList.toggle('is-movable', selected.length > 1);
    paint();
  };
  const travel = distance => {
    const count = items().length;
    if (count < 2) return;
    position += distance;
    let changed = false;
    while (position >= step) { position -= step; offset = (offset + 1) % count; changed = true; }
    while (position < 0) { position += step; offset = (offset - 1 + count) % count; changed = true; }
    if (changed) render(); else paint();
  };
  const coast = () => {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    let last = performance.now();
    const tick = now => {
      const dt = Math.min(now - last, 32); last = now;
      travel(velocity * dt);
      velocity *= Math.exp(-dt / 220);
      if (Math.abs(velocity) > .015) frame = requestAnimationFrame(tick);
      else { frame = 0; status.textContent = `${items().length}개 프로젝트 중 ${offset + 1}번째부터 표시합니다.`; }
    };
    frame = requestAnimationFrame(tick);
  };
  const advance = direction => {
    stop();
    const distance = direction * step;
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) { travel(distance); return; }
    let startTime, applied = 0;
    const tick = now => {
      startTime ??= now;
      const t = Math.min(1, (now - startTime) / 420);
      const next = distance * (1 - Math.pow(1 - t, 3));
      travel(next - applied); applied = next;
      if (t < 1) frame = requestAnimationFrame(tick); else frame = 0;
    };
    frame = requestAnimationFrame(tick);
  };
  controls.querySelectorAll('button').forEach((button, index) => {
    const direction = index === 0 ? -1 : 1;
    let timer, held = false, pressed = false;
    button.addEventListener('pointerdown', e => {
      if (e.button !== 0) return;
      stop(); pressed = true; held = false;
      button.setPointerCapture(e.pointerId);
      timer = setTimeout(() => {
        held = true;
        let last = performance.now();
        const tick = now => {
          travel(direction * Math.min(now - last, 32) * .65); last = now;
          frame = requestAnimationFrame(tick);
        };
        frame = requestAnimationFrame(tick);
      }, 220);
    });
    const release = cancel => {
      if (!pressed) return;
      pressed = false; clearTimeout(timer);
      if (held) { stop(); if (!cancel) { velocity = direction * .65; coast(); } }
    };
    button.addEventListener('pointerup', () => release(false));
    button.addEventListener('pointercancel', () => release(true));
    button.addEventListener('lostpointercapture', () => release(true));
    button.addEventListener('click', e => { if (e.detail === 0 || !held) advance(direction); held = false; });
  });
  const filter = value => {
    stop(); category = value; offset = 0; position = 0;
    buttons.forEach(button => {
      const active = button.dataset.category === value;
      button.classList.toggle('category--selected', active);
      button.setAttribute('aria-pressed', String(active));
    });
    render();
  };
  viewport.addEventListener('keydown', e => {
    if (e.target !== viewport || !['ArrowRight','ArrowLeft'].includes(e.key)) return;
    e.preventDefault(); stop();
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) travel(e.key === 'ArrowRight' ? step : -step);
    else { velocity = (e.key === 'ArrowRight' ? 1 : -1) * step / 220; coast(); }
  });
  let pointer = null;
  let dragged = false;
  viewport.addEventListener('pointerdown', e => {
    if (e.pointerType === 'mouse' || e.button !== 0 || items().length < 2 || e.target.closest('a, button, summary, .project__gallery')) return;
    stop(); dragged = false;
    pointer = {x:e.clientX, y:e.clientY, lastX:e.clientX, time:performance.now()};
    viewport.setPointerCapture(e.pointerId);
  });
  viewport.addEventListener('pointermove', e => {
    if (!pointer) return;
    if (!dragged && Math.abs(e.clientX-pointer.x) > 4 && Math.abs(e.clientX-pointer.x) > Math.abs(e.clientY-pointer.y)) {
      dragged = true; viewport.classList.add('is-dragging');
    }
    if (!dragged) return;
    const now = performance.now(), dt = Math.max(1, now-pointer.time);
    const distance = pointer.lastX-e.clientX;
    velocity = velocity * .25 + Math.max(-2.5, Math.min(2.5, distance / dt)) * .75;
    travel(distance);
    pointer.lastX = e.clientX; pointer.time = now;
  });
  viewport.addEventListener('pointerup', () => {
    if (!pointer) return;
    if (performance.now()-pointer.time > 80) velocity = 0;
    pointer = null; viewport.classList.remove('is-dragging');
    if (dragged) coast();
  });
  viewport.addEventListener('pointercancel', () => { pointer = null; stop(); viewport.classList.remove('is-dragging'); });
  viewport.addEventListener('click', e => { if (dragged) { e.preventDefault(); e.stopPropagation(); dragged = false; } }, true);
  viewport.addEventListener('wheel', e => {
    if (pointer || Math.abs(e.deltaX) <= Math.abs(e.deltaY) || e.target.closest('.project__gallery') || items().length < 2) return;
    e.preventDefault(); stop();
    // Trackpads already supply momentum. Preserve every delta without snapping.
    travel(e.deltaX * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? viewport.clientWidth : 1));
  }, {passive:false});
  window.addEventListener('resize', () => { stop(); position = 0; alignRoles(); render(); });
  document.fonts.ready.then(() => { alignRoles(); render(); });
  buttons.forEach((button) => {
    const category = button.dataset.category;
    const count = projects.filter((project) => category === 'all' || project.dataset.type === category).length;
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
    if (project) {
      filter(project.dataset.type);
      offset = items().indexOf(project);
      render();
    }
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
