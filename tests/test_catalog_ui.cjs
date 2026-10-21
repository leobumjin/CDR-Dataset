const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.attributes = {}; this.events = {}; this.dataset = {}; this.value = ''; this.textContent = ''; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  addEventListener(key, fn) { this.events[key] = fn; }
  querySelector(selector) {
    return walk(this).find(node => selector.startsWith('.') ? node.className === selector.slice(1) : selector === '[aria-pressed="true"]' && node.attributes['aria-pressed'] === 'true');
  }
  querySelectorAll(selector) { return walk(this).filter(node => node.tag === selector); }
  focus() {}
  click() { this.events.click?.({}); }
}
const walk = node => [node, ...node.children.flatMap(walk)];
const text = node => walk(node).map(item => item.textContent).join(' ');
async function loadPage(view, query = '', overrides = {}) {
  const ids = {};
  const names = view === 'tasks'
    ? ['catalog-combinations']
    : ['catalog-panel', 'catalog-search', ...(view === 'instances' ? ['instance-label-source', 'instance-class-buttons', 'instance-list-content', 'instance-list-title', 'instance-detail-content'] : ['catalog-class', 'catalog-task'])];
  names.forEach(id => { ids[id] = new Element('div'); });
  if (view === 'instances') {
    ids['instance-detail-content'].className = 'instance-detail';
    ids['catalog-panel'].append(ids['instance-list-title'], ids['instance-list-content'], ids['instance-detail-content']);
  }
  const document = {
    body: {dataset: {catalogView: view}},
    currentScript: {src: 'http://local/assets/catalog-explorer.js'},
    getElementById: id => ids[id] || null,
    createElement: tag => new Element(tag),
    createElementNS: (_,tag) => new Element(tag),
    createDocumentFragment: () => new Element('fragment')
  };
  const fetch = async url => ({ok: true, json: async () => overrides[new URL(url).pathname] || JSON.parse(fs.readFileSync('docs' + new URL(url).pathname, 'utf8'))});
  vm.runInNewContext(fs.readFileSync('docs/assets/catalog-explorer.js', 'utf8'), {
    document, fetch, URL, URLSearchParams, window: {location: {search: query}},
    Option: function(text, value) {this.textContent = text; this.value = value;}
  });
  await new Promise(resolve => setImmediate(resolve));
  return ids;
}
(async () => {
  const home = await loadPage('tasks');
  assert.equal(home['catalog-combinations'].children.length, 5);
  const birdLink = walk(home['catalog-combinations']).find(n => String(n.href).includes('class=bird'));
  assert.equal(new URL(birdLink.href).pathname, '/instances/');
  const instances = await loadPage('instances', '?class=bird');
  assert.match(text(instances['catalog-panel']), /100 instances/);
  assert.match(text(instances['catalog-panel']), /House sparrow/);
  assert.match(text(instances['catalog-panel']), /Release v1/);
  const classFilters = walk(instances['instance-class-buttons']).filter(n => n.tag === 'button');
  assert.equal(classFilters.length, 6);
  assert.equal(classFilters.find(n => n.dataset.classId === 'bird').attributes['aria-pressed'], 'true');
  const listButtons = walk(instances['catalog-panel']).filter(n => n.className === 'instance-list-button');
  assert.equal(listButtons.length, 100);
  listButtons[0].click();
  const manualDetail = walk(instances['catalog-panel']).find(n => n.className === 'instance-detail');
  assert.deepEqual(walk(manualDetail).filter(n => n.tag === 'td').map(n => n.textContent), Array(7).fill('NA'));
  instances['instance-label-source'].value = ''; instances['instance-label-source'].events.change();
  assert.equal(walk(instances['catalog-panel']).filter(n => n.tag === 'td' && n.textContent === 'NA').length, 7);
  instances['catalog-search'].value = 'penguin'; instances['catalog-search'].events.input();
  assert.match(text(instances['catalog-panel']), /4 instances/);
  assert.match(text(instances['catalog-panel']), /Emperor penguin/);
  instances['catalog-search'].value = 'missing-instance'; instances['catalog-search'].events.input();
  assert.match(text(instances['catalog-panel']), /No results/);

  classFilters.find(n => n.dataset.classId === 'plant').click();
  instances['catalog-search'].value = ''; instances['catalog-search'].events.input();
  assert.match(text(instances['catalog-panel']), /100 instances/);
  assert.equal(classFilters.find(n => n.dataset.classId === 'plant').attributes['aria-pressed'], 'true');
  const releases = JSON.parse(fs.readFileSync('docs/assets/instance_labels.json'));
  releases.sources.v2 = {available:true,classes:['bird'],instance_range:[1,2],feature_range:[1,1],contexts:{fly:['dry_20m']},features:{bird:{bird_0001:{bird_f_001:0}}}};
  const versioned = await loadPage('instances','?class=bird&release=v2',{'/assets/instance_labels.json':releases});
  assert.match(text(versioned['catalog-panel']),/2 instances/);
  assert.deepEqual(walk(versioned['catalog-panel']).filter(n=>n.tag==='td').map(n=>n.textContent), ['0']);
  versioned['instance-label-source'].value='v1'; versioned['instance-label-source'].events.change();
  assert.match(text(versioned['catalog-panel']),/100 instances/);
  assert.equal(walk(versioned['catalog-panel']).filter(n=>n.tag==='td' && n.textContent==='NA').length,7);
  const invalid = await loadPage('instances', '?class=unknown');
  assert.match(text(invalid['catalog-panel']), /500 instances/);
  console.log('Page UI checks passed: overview links, dedicated pages, URL filters, class/task filters, search, instance selection, feature values, missing values and empty states.');
})().catch(error => { console.error(error); process.exitCode = 1; });
