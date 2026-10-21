const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.attributes = {}; this.events = {}; this.dataset = {}; this.value = ''; this.textContent = ''; this.style = {}; this.hidden = true; this.offsetWidth = 320; this.offsetHeight = 280; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  addEventListener(key, fn) { this.events[key] = fn; }
  querySelector(selector) {
    return walk(this).find(node => selector.startsWith('.') ? node.className === selector.slice(1) : selector === '[aria-pressed="true"]' && node.attributes['aria-pressed'] === 'true');
  }
  querySelectorAll(selector) { return walk(this).filter(node => node.tag === selector); }
  getBoundingClientRect() { return {left: 20, top: 100, bottom: 140}; }
  focus() {}
  click() { this.events.click?.({}); }
}

const walk = node => [node, ...node.children.flatMap(walk)];
const text = node => walk(node).map(n => n.textContent).join(' ');
async function loadPage(query = '', failLabels = false, overrides = {}) {
  const ids = {};
  ['judgment-class','judgment-task','judgment-context','judgment-source','judgment-search','judgment-filter','sample-tooltip','judgment-samples','judgment-count','judgment-definition','judgment-source-note'].forEach(id => ids[id] = new Element('div'));
  ids['judgment-filter'].value = 'all';
  const events = {};
  const document = {currentScript: {src: 'http://local/assets/task-context.js'}, getElementById: id => ids[id], createElement: tag => new Element(tag), addEventListener: (key, fn) => events[key] = fn};
  const window = {location: {search: query, href: 'http://local/task-context/' + query}, innerWidth: 1024, innerHeight: 768, addEventListener: () => {}, history: {replaceState: (_, __, url) => { window.location.href = String(url); }}};
  const fetch = async url => {
    if (failLabels && String(url).includes('task_labels')) throw new Error('Unavailable');
    return {ok: true, json: async () => overrides[new URL(url).pathname] || JSON.parse(fs.readFileSync('docs' + new URL(url).pathname, 'utf8'))};
  };
  vm.runInNewContext(fs.readFileSync('docs/assets/task-context.js','utf8'), {document,window,URL,URLSearchParams,fetch,setTimeout,clearTimeout, Option: function(text,value) { const n = new Element('option'); n.textContent = text; n.value = value; return n; }});
  await new Promise(resolve => setImmediate(resolve));
  return {ids,events,window};
}
(async () => {
  const {ids, events, window} = await loadPage('?class=bird&task=fly&context=wet_20m');
  assert.equal(ids['judgment-task'].value, 'fly');
  assert.equal(ids['judgment-context'].value, 'wet_20m');
  assert.match(ids['judgment-count'].textContent, /100 samples/);
  assert.match(ids['judgment-count'].textContent, /100 NA/);
  assert.match(ids['judgment-source-note'].textContent, /Release v1/);
  let first = ids['judgment-samples'].children[0];
  first.events.mouseenter();
  assert.equal(ids['sample-tooltip'].hidden, false);
  assert.match(text(ids['sample-tooltip']), /House sparrow/);
  assert.equal(walk(ids['sample-tooltip']).filter(n=>n.tag==='dd').length, 7);
  events.keydown({key:'Escape'});
  assert.equal(ids['sample-tooltip'].hidden, true);
  assert.equal(new URL(first.href).searchParams.get('instance'), 'bird_0001');
  ids['judgment-filter'].value = 'NA'; ids['judgment-filter'].events.change();
  assert.match(ids['judgment-count'].textContent, /^100 samples/);
  ids['judgment-samples'].children[0].events.focus();
  assert.equal(walk(ids['sample-tooltip']).filter(n=>n.tag==='dd' && n.textContent==='NA').length, 7);
  ids['judgment-filter'].value='all';
  ids['judgment-class'].value='plant'; ids['judgment-class'].events.change();
  assert.equal(ids['judgment-task'].value, 'survive');
  assert(ids['judgment-context'].children.every(n=>n.value.startsWith('plant_')));
  assert.match(ids['judgment-count'].textContent, /^100 samples/);
  assert.equal(new URL(window.location.href).searchParams.get('class'),'plant');
  ids['judgment-search'].value='not-a-real-sample'; ids['judgment-search'].events.input();
  assert.match(text(ids['judgment-samples']), /No samples/);
  const releases = JSON.parse(fs.readFileSync('docs/assets/task_labels.json'));
  releases.sources.v2 = {available:true,classes:['bird'],instance_range:[1,2],feature_range:[1,1],contexts:{fly:['dry_20m']},tasks:{fly:{bird_0001:{dry_20m:'true'},bird_0002:{dry_20m:'false'}}}};
  const versioned = await loadPage('?release=v2', false, {'/assets/task_labels.json':releases});
  assert.match(versioned.ids['judgment-count'].textContent,/2 samples · 1 true · 1 false/);
  assert.equal(versioned.ids['judgment-context'].children.length,1);
  assert.equal(versioned.ids['judgment-class'].children.length,1);
  versioned.ids['judgment-source'].value='v1'; versioned.ids['judgment-source'].events.change();
  assert.match(versioned.ids['judgment-count'].textContent,/100 NA/);
  const noLabels = await loadPage('?class=human&release=');
  assert.match(noLabels.ids['judgment-count'].textContent, /100 NA/);
  const unavailable = await loadPage('?class=human', true);
  assert.match(unavailable.ids['judgment-source-note'].textContent, /could not be loaded/);
  console.log('Task-context UI checks passed: selections, class bindings, values, missing labels, hover/focus, filters, links, URL state and load failure.');
})().catch(error => {console.error(error); process.exitCode=1;});
