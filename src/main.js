"use strict";
(() => {
  const header = document.querySelector('.header');
  const menu = document.querySelector('.header__menu');
  const toggle = document.querySelector('.header__toggle');
  const arrow = document.querySelector('.arrow-up');
  const mobile = window.matchMedia('(max-width: 768px)');
  const setMenu = (open) => {
    menu.classList.toggle('open', open);
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? '메뉴 닫기' : '메뉴 열기');
    toggle.textContent = open ? '닫기 ×' : '메뉴';
  };
  header.classList.add('header--enhanced');
  toggle.hidden = false;
  toggle.addEventListener('click', () => setMenu(toggle.getAttribute('aria-expanded') !== 'true'));
  menu.addEventListener('click', (event) => {
    if (event.target.closest('a')) setMenu(false);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
      setMenu(false);
      toggle.focus();
    }
  });
  document.addEventListener('click', (event) => {
    if (!header.contains(event.target)) setMenu(false);
  });
  mobile.addEventListener('change', () => setMenu(false));
  const updateScroll = () => {
    header.classList.toggle('header--dark', window.scrollY > 24);
    arrow.hidden = window.scrollY < 300;
  };
  window.addEventListener('scroll', updateScroll, {passive:true});
  updateScroll();
  const copyButton = document.querySelector('.copy-email');
  const copyStatus = document.querySelector('.copy-status');
  if (navigator.clipboard?.writeText && window.isSecureContext) {
    copyButton.hidden = false;
    copyButton.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(document.querySelector('.contact__email').textContent.trim());
        copyStatus.textContent = '이메일 주소를 복사했습니다.';
      } catch {
        copyStatus.textContent = '복사 권한이 없어 복사하지 못했습니다. 위 이메일 주소를 직접 선택해 복사해 주세요.';
      }
    });
  }
})();
