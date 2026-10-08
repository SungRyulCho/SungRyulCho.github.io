"use strict";
(() => {
  const dialog = document.querySelector('#evidence-dialog');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  const triggers = [...document.querySelectorAll('[data-evidence-open="dekk-deployment"]')];
  if (!triggers.length) return;
  const base = 'images/evidence/dekk-deployment/';
  const captureUrl = (file) => base + file + '?v=20261008-clean';
  const captures = [
    {file: 'guide.webp', title: '배포 가이드', width: 1330, alt: '노션 DEKK 인프라 & CI/CD 자동 배포 6단계 문서 제목과 도메인·DNS 설정 단계'},
    {file: 'dns-records.webp', title: '도메인·DNS', width: 1900, alt: '도메인 구매, Route 53, 네임서버 설정 절차와 Sung Ryul Cho의 3월 3일 완료 댓글'},
    {file: 'network-records.webp', title: '인증서·ALB', width: 1900, alt: 'SSL 인증서, ALB, 보안 그룹 설정 절차와 Sung Ryul Cho의 3월 3일 완료 댓글'},
    {file: 'server-setup.webp', title: '서버 환경 설정', width: 1900, alt: 'Java와 CodeDeploy Agent 설치 가이드 및 재웅 정의 3월 3일 작업 완료 댓글'},
    {file: 'pipeline.webp', title: '자동 배포 연결', width: 1330, alt: 'GitHub Actions와 S3, CodeDeploy 연결 단계 및 GitHub Secrets 등록 항목 안내'},
    {file: 'script-fix.webp', title: '배포 오류 수정', width: 1340, alt: '트러블슈팅 문서의 배포 스크립트 수정 기록: 파일명 대소문자, JAR 탐색 패턴, 프로세스 조회 옵션 변경'},
  ];
  const stage = dialog.querySelector('.evidence-dialog__stage');
  const image = dialog.querySelector('.evidence-dialog__image');
  const caption = dialog.querySelector('.evidence-dialog__caption');
  const rail = dialog.querySelector('.evidence-dialog__thumbnails');
  const zoom = dialog.querySelector('.evidence-dialog__zoom');
  const close = dialog.querySelector('.evidence-dialog__close');
  const error = dialog.querySelector('.evidence-dialog__error');
  let selected = 0;
  let opener = null;
  let thumbnails = [];

  function setZoom(expanded) {
    stage.classList.toggle('is-zoomed', expanded);
    zoom.setAttribute('aria-pressed', String(expanded));
    zoom.querySelector('span').textContent = expanded ? '화면에 맞춤' : '확대';
    stage.scrollTop = 0;
    stage.scrollLeft = 0;
  }

  function select(index, focus = false) {
    selected = index;
    const capture = captures[index];
    error.hidden = true;
    image.hidden = false;
    image.alt = capture.alt;
    image.src = captureUrl(capture.file);
    stage.style.setProperty('--capture-width', capture.width + 'px');
    caption.textContent = capture.title + ' · ' + (index + 1) + ' / ' + captures.length;
    setZoom(false);
    thumbnails.forEach((button, position) => button.setAttribute('aria-pressed', String(position === index)));
    if (focus) {
      thumbnails[index].focus({preventScroll: true});
      thumbnails[index].scrollIntoView({block: 'nearest', inline: 'nearest'});
    }
  }

  function createThumbnails() {
    if (thumbnails.length) return;
    thumbnails = captures.map((capture, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'evidence-dialog__thumbnail';
      button.setAttribute('aria-label', capture.title + ' 캡처 보기');
      button.setAttribute('aria-pressed', 'false');
      const preview = document.createElement('img');
      preview.src = captureUrl(capture.file);
      preview.alt = '';
      preview.width = 160;
      preview.height = 56;
      const label = document.createElement('span');
      label.textContent = capture.title;
      button.append(preview, label);
      button.addEventListener('click', () => select(index));
      rail.append(button);
      return button;
    });
  }

  triggers.forEach((trigger) => {
    trigger.addEventListener('click', () => {
      opener = trigger;
      createThumbnails();
      select(0);
      dialog.showModal();
      document.documentElement.classList.add('evidence-viewer-open');
      close.focus({preventScroll: true});
    });
    trigger.hidden = false;
  });
  zoom.addEventListener('click', () => setZoom(zoom.getAttribute('aria-pressed') !== 'true'));
  close.addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => {
    document.documentElement.classList.remove('evidence-viewer-open');
    setZoom(false);
    opener?.focus({preventScroll: true});
  });
  image.addEventListener('error', () => { image.hidden = true; error.hidden = false; });
  image.addEventListener('load', () => {
    stage.style.setProperty('--capture-height-ratio', image.naturalHeight / image.naturalWidth);
  });
  dialog.addEventListener('keydown', (event) => {
    // Arrow keys remain available for panning an enlarged capture.
    if (event.altKey || event.ctrlKey || event.metaKey || stage.classList.contains('is-zoomed')) return;
    const next = {ArrowRight: (selected + 1) % captures.length,
      ArrowLeft: (selected + captures.length - 1) % captures.length,
      Home: 0, End: captures.length - 1}[event.key];
    if (next === undefined) return;
    event.preventDefault();
    select(next, true);
  });
  const isOutside = (event) => {
    const r = dialog.getBoundingClientRect();
    return event.target === dialog && (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom);
  };
  let pointerStartedOutside = false;
  dialog.addEventListener('pointerdown', (event) => { pointerStartedOutside = isOutside(event); });
  dialog.addEventListener('click', (event) => {
    if (pointerStartedOutside && isOutside(event)) dialog.close();
    pointerStartedOutside = false;
  });
})();
