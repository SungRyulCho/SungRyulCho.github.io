"use strict";
// Touch feedback mirrors the decorative desktop hover.
document.querySelectorAll('.major').forEach(card => {
  let timer;
  const reset = () => { clearTimeout(timer); card.classList.remove('major--reacting'); };
  card.addEventListener('pointerdown', event => {
    if (event.pointerType === 'mouse') return;
    reset();
    card.classList.add('major--reacting');
    timer = setTimeout(reset, 600);
  });
  card.addEventListener('pointercancel', reset);
});
