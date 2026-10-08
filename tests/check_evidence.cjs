const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'src/evidence-viewer.js'), 'utf8');

test('deployment code comes before captures, with an underline spanning the document icon', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  const deployment = html.split('id="dekk-deployment-collaboration"')[1].split('</article>')[0];
  assert.ok(deployment.indexOf('팀 배포 구성 코드 ↗') < deployment.indexOf('class="evidence-trigger"'));
  const css = fs.readFileSync(path.join(root, 'css/evidence-viewer.css'), 'utf8');
  const underline = css.split('.evidence-trigger::after {')[1].split('}')[0];
  assert.match(underline, /left: 0;/);
  assert.match(underline, /right: 0;/);
  assert.doesNotMatch(css, /\.evidence-trigger span\s*\{[^}]*text-decoration: underline/);
});

function setup({supported = true} = {}) {
  const document = {activeElement: null};
  function element() {
    const values = new Set();
    return {
      hidden: false, attrs: {}, listeners: {}, children: [], style: {setProperty() {}},
      classList: {add: name => values.add(name), remove: name => values.delete(name),
        contains: name => values.has(name), toggle(name, on) { on ? values.add(name) : values.delete(name); }},
      setAttribute(name, value) { this.attrs[name] = value; },
      getAttribute(name) { return this.attrs[name]; },
      addEventListener(name, handler) { (this.listeners[name] ??= []).push(handler); },
      emit(name, extra = {}) {
        const event = {target: this, preventDefault() { this.prevented = true; }, ...extra};
        (this.listeners[name] ?? []).forEach(handler => handler(event));
        return event;
      },
      append(...children) { this.children.push(...children); },
      focus() { document.activeElement = this; }, scrollIntoView() {},
    };
  }
  const nodes = Object.fromEntries(['stage', 'image', 'caption', 'thumbnails', 'zoom', 'close', 'error']
    .map(name => ['.evidence-dialog__' + name, element()]));
  const zoomLabel = element();
  nodes['.evidence-dialog__zoom'].querySelector = () => zoomLabel;
  const dialog = element();
  dialog.open = false;
  dialog.querySelector = selector => nodes[selector];
  if (supported) dialog.showModal = () => { dialog.open = true; };
  dialog.close = () => { dialog.open = false; dialog.emit('close'); };
  dialog.getBoundingClientRect = () => ({left: 20, top: 20, right: 900, bottom: 700});
  const trigger = element();
  trigger.hidden = true;
  document.documentElement = element();
  document.querySelector = () => dialog;
  document.querySelectorAll = () => [trigger];
  document.createElement = element;
  vm.runInNewContext(source, {document});
  return {document, dialog, trigger, zoomLabel,
    ...Object.fromEntries(Object.entries(nodes).map(([key, value]) => [key.replace('.evidence-dialog__', ''), value]))};
}

test('capture viewer enhances only when modal dialogs are supported', () => {
  assert.equal(setup({supported: false}).trigger.hidden, true);
  assert.equal(setup().trigger.hidden, false);
});

test('opens six original assets with one selected capture and meaningful alt text', () => {
  const view = setup();
  view.trigger.emit('click');
  assert.equal(view.dialog.open, true);
  assert.equal(view.thumbnails.children.length, 6);
  assert.equal(view.document.activeElement, view.close);
  for (const button of view.thumbnails.children) {
    button.emit('click');
    assert.ok(fs.existsSync(path.join(root, view.image.src.split('?')[0])), view.image.src);
    assert.match(view.image.src, /\?v=20261008-clean$/);
    assert.ok(view.image.alt.length > 20);
    assert.equal(view.thumbnails.children.filter(el => el.attrs['aria-pressed'] === 'true').length, 1);
  }
});

test('zoom resets on capture changes and leaves arrow keys available for panning', () => {
  const view = setup();
  view.trigger.emit('click');
  view.zoom.emit('click');
  assert.equal(view.zoom.attrs['aria-pressed'], 'true');
  assert.equal(view.zoomLabel.textContent, '화면에 맞춤');
  assert.equal(view.dialog.emit('keydown', {key: 'ArrowRight'}).prevented, undefined);
  view.thumbnails.children[1].emit('click');
  assert.equal(view.zoom.attrs['aria-pressed'], 'false');
  assert.equal(view.stage.classList.contains('is-zoomed'), false);
});

test('keyboard navigation wraps and browser navigation shortcuts are preserved', () => {
  const view = setup();
  view.trigger.emit('click');
  view.dialog.emit('keydown', {key: 'ArrowLeft'});
  assert.equal(view.document.activeElement, view.thumbnails.children[5]);
  assert.ok(view.caption.textContent.endsWith('6 / 6'));
  view.dialog.emit('keydown', {key: 'ArrowRight'});
  assert.ok(view.caption.textContent.endsWith('1 / 6'));
  assert.equal(view.dialog.emit('keydown', {key: 'ArrowLeft', altKey: true}).prevented, undefined);
});

test('close returns focus without altering the parent case or creating duplicate thumbnails', () => {
  const view = setup();
  view.trigger.emit('click');
  view.close.emit('click');
  assert.equal(view.dialog.open, false);
  assert.equal(view.document.activeElement, view.trigger);
  assert.equal(view.document.documentElement.classList.contains('evidence-viewer-open'), false);
  view.trigger.emit('click');
  assert.equal(view.thumbnails.children.length, 6);
  assert.ok(view.caption.textContent.endsWith('1 / 6'));
});

test('image load errors are visible and clear when selecting another capture', () => {
  const view = setup();
  view.trigger.emit('click');
  view.image.emit('error');
  assert.equal(view.image.hidden, true);
  assert.equal(view.error.hidden, false);
  view.thumbnails.children[1].emit('click');
  assert.equal(view.error.hidden, true);
  assert.equal(view.image.hidden, false);
});

test('only a click that starts and ends on the backdrop closes the viewer', () => {
  const view = setup();
  view.trigger.emit('click');
  view.dialog.emit('pointerdown', {clientX: 100, clientY: 100});
  view.dialog.emit('click', {clientX: 0, clientY: 0});
  assert.equal(view.dialog.open, true);
  view.dialog.emit('pointerdown', {clientX: 0, clientY: 0});
  view.dialog.emit('click', {clientX: 0, clientY: 0});
  assert.equal(view.dialog.open, false);
});
