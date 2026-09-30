"use strict";
(() => {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  document.querySelectorAll('[data-project-gallery]').forEach((gallery) => {
    const slides = [...gallery.querySelectorAll('.project__gallery-slide')];
    const viewport = gallery.querySelector('.project__gallery-viewport');
    if (slides.length < 2 || !viewport) return;

    let current = 0;
    let timer = null;
    let hovered = gallery.matches(':hover');
    let focused = gallery.contains(document.activeElement);
    let inView = !('IntersectionObserver' in window);
    let paused = false;

    function showSlide(index) {
      const focusWasOnImage = slides.includes(document.activeElement);
      current = (index + slides.length) % slides.length;
      slides.forEach((slide, position) => { slide.hidden = position !== current; });
      viewport.scrollLeft = 0;
      if (focusWasOnImage) slides[current].focus({preventScroll: true});
    }

    function syncPlayback() {
      const shouldPlay = inView && !document.hidden && !reducedMotion.matches &&
        !hovered && !focused && !paused;
      if (!shouldPlay && timer !== null) {
        window.clearInterval(timer);
        timer = null;
      } else if (shouldPlay && timer === null) {
        timer = window.setInterval(() => showSlide(current + 1), 3000);
      }
    }

    // Without JavaScript, the original links remain horizontally scrollable.
    gallery.classList.add('project__gallery--enhanced');
    gallery.setAttribute('aria-description', '3초마다 화면이 바뀝니다. 마우스를 올리거나 키보드로 선택하면 멈춥니다. 좌우 방향키로 전환하고 스페이스 키로 자동 전환을 켜거나 끌 수 있습니다.');
    showSlide(0);
    // Hidden lazy images would otherwise start loading only after their turn.
    function prepareImages() {
      slides.forEach((slide) => {
        const img = slide.querySelector('img');
        if (img) img.loading = 'eager';
      });
    }
    if ('IntersectionObserver' in window) {
      const observer = new window.IntersectionObserver(([entry]) => {
        inView = entry.isIntersecting;
        if (inView) prepareImages();
        syncPlayback();
      });
      observer.observe(gallery);
    } else {
      prepareImages();
    }
    gallery.addEventListener('pointerenter', () => { hovered = true; syncPlayback(); });
    gallery.addEventListener('pointerleave', () => { hovered = false; syncPlayback(); });
    gallery.addEventListener('focusin', () => { focused = true; syncPlayback(); });
    gallery.addEventListener('focusout', (event) => {
      focused = gallery.contains(event.relatedTarget);
      syncPlayback();
    });
    document.addEventListener('visibilitychange', syncPlayback);
    reducedMotion.addEventListener('change', syncPlayback);
    gallery.addEventListener('keydown', (event) => {
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      if (event.key === ' ') {
        event.preventDefault();
        paused = !paused;
        syncPlayback();
        return;
      }
      const index = {
        ArrowLeft: current - 1,
        ArrowRight: current + 1,
        Home: 0,
        End: slides.length - 1,
      }[event.key];
      if (index === undefined) return;
      event.preventDefault();
      showSlide(index);
    });
    // Touch users can inspect adjacent screens without extra visible controls.
    let touchStart = null;
    let suppressClick = false;
    gallery.addEventListener('touchstart', (event) => {
      const touch = event.touches[0];
      touchStart = event.touches.length === 1 ? {x: touch.clientX, y: touch.clientY} : null;
      suppressClick = false;
    }, {passive: true});
    gallery.addEventListener('touchend', (event) => {
      if (!touchStart || event.touches.length) { touchStart = null; return; }
      const touch = event.changedTouches[0];
      const dx = touch.clientX - touchStart.x;
      const dy = touch.clientY - touchStart.y;
      touchStart = null;
      if (Math.abs(dx) < 40 || Math.abs(dx) <= Math.abs(dy)) return;
      showSlide(current + (dx < 0 ? 1 : -1));
      suppressClick = true;
      paused = true;
      syncPlayback();
    }, {passive: true});
    gallery.addEventListener('touchcancel', () => { touchStart = null; });
    gallery.addEventListener('click', (event) => {
      if (!suppressClick) return;
      event.preventDefault();
      suppressClick = false;
    });
    syncPlayback();
  });
})();
