// Dependency-free interaction checks: node --test tests/check_gallery.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');
const source = fs.readFileSync(path.join(__dirname, '../src/project-gallery.js'), 'utf8');
const INTERVAL = 3000;

function setup({reduceMotion = false, withObserver = true, visible = true} = {}) {
  const events = () => ({
    listeners: {},
    addEventListener(type, handler) { (this.listeners[type] ??= []).push(handler); },
    emit(type, details = {}) {
      const event = {prevented: false, preventDefault() { this.prevented = true; }, ...details};
      for (const handler of this.listeners[type] ?? []) handler(event);
      return event;
    },
  });
  const document = Object.assign(events(), {activeElement: null, hidden: false});
  const motion = Object.assign(events(), {matches: reduceMotion});
  const timers = new Map();
  let now = 0, nextTimer = 0;
  const observers = [];
  const window = {
    matchMedia(query) { assert.equal(query, '(prefers-reduced-motion: reduce)'); return motion; },
    setInterval(callback, delay) {
      const id = ++nextTimer;
      timers.set(id, {callback, delay, next: now + delay});
      return id;
    },
    clearInterval(id) { timers.delete(id); },
  };
  if (withObserver) window.IntersectionObserver = class {
    constructor(callback) { this.callback = callback; observers.push(this); }
    observe(target) { this.target = target; }
  };
  function advance(ms) {
    const end = now + ms;
    while (true) {
      const next = [...timers.values()].sort((a, b) => a.next - b.next)[0];
      if (!next || next.next > end) break;
      now = next.next;
      next.next += next.delay;
      next.callback();
    }
    now = end;
  }
  const element = () => Object.assign(events(), {
    hidden: false, dataset: {}, attributes: {},
    classList: {values: new Set(), add(value) { this.values.add(value); }},
    setAttribute(name, value) { this.attributes[name] = value; },
    matches() { return false; },
    contains(node) { return node === this || this.slides?.includes(node) || false; },
    focus() { document.activeElement = this; },
  });
  const makeGallery = (labels) => {
    const gallery = element();
    gallery.slides = labels.map((imageLabel) => {
      const slide = Object.assign(element(), {dataset: {imageLabel}, img: {loading: 'lazy'}});
      slide.querySelector = (selector) => selector === 'img' ? slide.img : null;
      return slide;
    });
    gallery.viewport = element();
    gallery.querySelectorAll = () => gallery.slides;
    gallery.querySelector = () => gallery.viewport;
    gallery.key = (key, modifiers = {}) => gallery.emit('keydown', {key, ...modifiers});
    gallery.index = () => gallery.slides.findIndex((slide) => !slide.hidden);
    gallery.setVisible = (isIntersecting) => {
      observers.find((observer) => observer.target === gallery)?.callback([{isIntersecting}]);
    };
    gallery.swipe = (dx, dy = 0) => {
      gallery.emit('touchstart', {touches: [{clientX: 200, clientY: 100}]});
      gallery.emit('touchend', {touches: [], changedTouches: [{clientX: 200 + dx, clientY: 100 + dy}]});
    };
    return gallery;
  };
  const dekk = makeGallery(['카드 탐색', '덱 목록', '링크 공유']);
  const learnflow = makeGallery(['메인', 'AI 요약', '리뷰']);
  const vench = makeGallery(['생성 중', '생성 결과', '지난 기록']);
  const single = makeGallery(['한 장']);
  const incomplete = makeGallery(['하나', '둘']);
  incomplete.viewport = null;
  document.querySelectorAll = () => [dekk, learnflow, vench, single, incomplete];
  vm.runInNewContext(source, {document, window});
  for (const observer of observers) observer.callback([{isIntersecting: visible}]);
  return {document, motion, timers, advance, dekk, learnflow, vench, single, incomplete};
}

test('one slide per gallery; automatic 3000 ms steps wrap after three', () => {
  const {dekk, learnflow, vench, timers, advance} = setup();
  assert.equal(timers.size, 3);
  for (const timer of timers.values()) assert.equal(timer.delay, INTERVAL);
  for (const gallery of [dekk, learnflow, vench]) {
    assert.equal(gallery.index(), 0);
    assert.equal(gallery.slides.filter((slide) => !slide.hidden).length, 1);
    assert.ok(gallery.slides.every((slide) => slide.img.loading === 'eager'));
  }
  advance(INTERVAL - 1);
  assert.equal(dekk.index(), 0);
  advance(1);
  assert.equal(dekk.index(), 1);
  assert.equal(learnflow.index(), 1);
  assert.equal(vench.index(), 1);
  advance(INTERVAL);
  assert.equal(vench.index(), 2);
  advance(INTERVAL);
  assert.equal(vench.index(), 0);
});

test('hover pauses only that gallery; resume starts a fresh three-second delay', () => {
  const {dekk, learnflow, timers, advance} = setup();
  advance(INTERVAL / 2);
  dekk.emit('pointerenter');
  assert.equal(timers.size, 2);
  advance(INTERVAL / 2);
  assert.equal(dekk.index(), 0);
  assert.equal(learnflow.index(), 1);
  dekk.emit('pointerleave');
  advance(INTERVAL - 1);
  assert.equal(dekk.index(), 0);
  advance(1);
  assert.equal(dekk.index(), 1);
});

test('keyboard focus pauses playback and manual navigation retains image focus', () => {
  const {document, dekk, advance} = setup();
  document.activeElement = dekk.slides[0];
  dekk.emit('focusin');
  advance(INTERVAL * 2);
  assert.equal(dekk.index(), 0);
  assert.equal(dekk.key('ArrowRight').prevented, true);
  assert.equal(document.activeElement, dekk.slides[1]);
  dekk.emit('focusout', {relatedTarget: dekk.slides[1]});
  advance(INTERVAL);
  assert.equal(dekk.index(), 1);
  document.activeElement = null;
  dekk.emit('focusout', {relatedTarget: null});
  advance(INTERVAL);
  assert.equal(dekk.index(), 2);
});

test('hidden documents stop timers and resume without catch-up or duplication', () => {
  const {document, dekk, timers, advance} = setup();
  document.hidden = true;
  document.emit('visibilitychange');
  assert.equal(timers.size, 0);
  advance(INTERVAL * 8);
  assert.equal(dekk.index(), 0);
  document.hidden = false;
  document.emit('visibilitychange');
  document.emit('visibilitychange');
  assert.equal(timers.size, 3);
  advance(INTERVAL);
  assert.equal(dekk.index(), 1);
});

test('offscreen or filtered galleries pause and visible images load ahead', () => {
  const {dekk, learnflow, timers, advance} = setup({visible: false});
  assert.equal(timers.size, 0);
  assert.ok(dekk.slides.every((slide) => slide.img.loading === 'lazy'));
  dekk.setVisible(true);
  advance(INTERVAL);
  assert.equal(dekk.index(), 1);
  assert.equal(learnflow.index(), 0);
  assert.ok(dekk.slides.every((slide) => slide.img.loading === 'eager'));
  dekk.setVisible(false);
  advance(INTERVAL * 2);
  assert.equal(dekk.index(), 1);
});

test('reduced motion disables autoplay but not manual navigation', () => {
  const {dekk, motion, timers, advance} = setup({reduceMotion: true});
  assert.equal(timers.size, 0);
  advance(INTERVAL);
  assert.equal(dekk.index(), 0);
  dekk.key('End');
  assert.equal(dekk.index(), 2);
  dekk.key('Home');
  assert.equal(dekk.index(), 0);
  motion.matches = false;
  motion.emit('change');
  advance(INTERVAL);
  assert.equal(dekk.index(), 1);
  motion.matches = true;
  motion.emit('change');
  assert.equal(timers.size, 0);
});

test('space toggles persistent pause without visible controls', () => {
  const {dekk, advance} = setup();
  assert.equal(dekk.key(' ').prevented, true);
  dekk.emit('pointerenter');
  dekk.emit('pointerleave');
  advance(INTERVAL * 2);
  assert.equal(dekk.index(), 0);
  dekk.key(' ');
  advance(INTERVAL);
  assert.equal(dekk.index(), 1);
});

test('horizontal swipe navigates, pauses and prevents accidental image opening', () => {
  const {vench, advance} = setup();
  vench.swipe(-100);
  assert.equal(vench.index(), 1);
  assert.equal(vench.emit('click').prevented, true);
  assert.equal(vench.emit('click').prevented, false);
  advance(INTERVAL * 2);
  assert.equal(vench.index(), 1);
  vench.swipe(100);
  assert.equal(vench.index(), 0);
});

test('vertical touch scrolling and ordinary taps keep native behavior', () => {
  const {vench} = setup();
  vench.swipe(5, 100);
  assert.equal(vench.index(), 0);
  assert.equal(vench.emit('click').prevented, false);
  vench.swipe(0);
  assert.equal(vench.emit('click').prevented, false);
});

test('tab, enter and browser navigation shortcuts are not intercepted', () => {
  const {dekk} = setup();
  for (const key of ['Tab', 'Enter', 'Escape']) assert.equal(dekk.key(key).prevented, false);
  for (const modifier of ['altKey', 'ctrlKey', 'metaKey']) {
    assert.equal(dekk.key('ArrowLeft', {[modifier]: true}).prevented, false);
  }
});

test('single or incomplete galleries retain native fallback', () => {
  const {single, incomplete} = setup();
  for (const gallery of [single, incomplete]) {
    assert.equal(gallery.classList.values.has('project__gallery--enhanced'), false);
    assert.ok(gallery.slides.every((slide) => !slide.hidden));
  }
});

test('autoplay also works without IntersectionObserver', () => {
  const {dekk, advance} = setup({withObserver: false});
  advance(INTERVAL);
  assert.equal(dekk.index(), 1);
});
