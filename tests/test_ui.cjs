const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.attributes = {}; this.events = {}; this.dataset = {}; this.value = ''; this.textContent = ''; this.classList = {add() {}, remove() {}}; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  addEventListener(key, fn) { this.events[key] = fn; }
}
const walk = n => [n, ...n.children.flatMap(walk)];
const text = n => walk(n).map(n => n.textContent).join(' ');
const catalog = JSON.parse(fs.readFileSync('docs/assets/catalog.json'));
const sources = {v2: {available: true, classes: ['bird'], sample_provenance: {method:'constructed'},
  samples: {bird: {sample_1: {bird_f_001: 0, bird_f_002: true}, sample_2: {bird_f_001: 2.7}}},
  tasks: {fly: {sample_1: {dry_20m:{yes:0.7,no:0.2,unknown:0.1}}}}}};
sources.v2.definitions = {
  classes: catalog.classes.map(c=>({...c, features:Object.entries(c.features).map(([id,f])=>({id,...f}))})),
  tasks: catalog.tasks,
  contexts: catalog.tasks.flatMap(t=>Object.entries(t.contexts).map(([id,c])=>({task_id:t.id,id,...c})))
};
async function loadPage(file, query='', failed=false, homeOnly=false) {
  const ids = {};
  const names = homeOnly ? ['catalog-combinations'] : ['catalog-panel','catalog-version','instance-label-source','instance-class-buttons','class-search','instance-detail-content'];
  for (const id of names) ids[id] = new Element('div');
  const document = {currentScript:{src:`http://local/assets/${file}`},getElementById:id=>ids[id],createElement:tag=>new Element(tag),createElementNS:(_,tag)=>new Element(tag)};
  const fetch = async url => ({ok:!failed,json:async()=>new URL(url).pathname.endsWith('release_samples.json') ? {sources} : catalog});
  vm.runInNewContext(fs.readFileSync(`docs/assets/${file}`,'utf8'), {
    document,fetch,URL,URLSearchParams,window:{location:{search:query}},
    Option:function(label,value) { const n = new Element('option'); n.textContent=label; n.value=value; return n; }
  });
  await new Promise(resolve=>setImmediate(resolve));
  return ids;
}
(async()=>{
  const home = await loadPage('catalog-explorer.js', '', false, true);
  const stream = home['catalog-combinations'];
  assert.equal(walk(stream).filter(n=>n.className==='instance-stream-row').length,2);
  assert.equal(walk(stream).filter(n=>n.className==='instance-stream-group').length,4);
  assert.equal(walk(stream).filter(n=>n.tag==='svg').length,20);
  assert.equal(walk(stream).filter(n=>n.attributes['aria-hidden']==='true' && n.tag==='ul').length,2);
  const symbols = fs.readFileSync('docs/assets/project-overview/icons.svg','utf8');
  for (const use of walk(stream).filter(n=>n.tag==='use')) {
    const id = new URL(use.attributes.href).hash.slice(1);
    assert.ok(symbols.includes(`id="${id}"`), `Missing icon ${id}`);
  }
  assert.match(text(stream),/Cars/);
  assert.doesNotMatch(text(stream),/\d+ features/);
  let ids = await loadPage('catalog-explorer.js','?class=bird');
  assert.equal(ids['catalog-version'].value, 'v1');
  assert.equal(ids['catalog-version'].children[0].textContent, 'v1');
  assert.match(text(ids['instance-detail-content']), /is_large/);
  assert.doesNotMatch(text(ids['instance-detail-content']), /no sample selected/);
  const tab = name => walk(ids['instance-detail-content']).find(n=>n.attributes.role==='tab' && n.textContent===name);
  tab('Task-Context').events.click();
  assert.match(text(ids['instance-detail-content']), /wet_20m/);
  assert.doesNotMatch(text(ids['instance-detail-content']), /is_large/);
  let description = walk(ids['instance-detail-content']).find(n=>n.className==='context-description');
  assert.match(text(description), /dry_20m/);
  assert.doesNotMatch(text(description), /wet_20m/);
  walk(ids['instance-detail-content']).find(n=>n.className==='context-choice' && n.textContent==='wet_20m').events.click();
  description = walk(ids['instance-detail-content']).find(n=>n.className==='context-description');
  assert.match(text(description), /wet_20m/);
  assert.match(text(description), /immediately after heavy rain/);
  assert.doesNotMatch(text(description), /dry_500m/);

  assert.match(text(ids['instance-detail-content']), /Can this bird fly/);
  assert.equal(tab('Task-Context').attributes['aria-selected'],'true');
  tab('Features').events.click();
  assert.match(text(ids['instance-detail-content']), /is_large/);

  ids = await loadPage('catalog-explorer.js','?class=bird&release=v2&sample=sample_1');
  assert.match(text(ids['instance-detail-content']), /Bird/);
  assert.match(text(ids['instance-detail-content']), / 0 /);
  assert.doesNotMatch(text(ids['instance-detail-content']), /grounding|sparrow/i);
  assert.match(text(ids['instance-detail-content']), /T\+F\+U=1/);
  assert.ok(!fs.readFileSync('docs/catalog/index.html','utf8').includes('catalog-search'));
  assert.ok(fs.readFileSync('docs/catalog/index.html','utf8').includes('class-sidebar'));
  assert.equal(walk(ids['instance-class-buttons']).filter(n=>n.tag==='button').length,10);
  ids['class-search'].value='SMART'; ids['class-search'].events.input();
  assert.equal(walk(ids['instance-class-buttons']).filter(n=>n.tag==='button').length,1);
  assert.match(text(ids['instance-class-buttons']),/Smartphones/);
  ids['class-search'].value='no-such-class'; ids['class-search'].events.input();
  assert.match(text(ids['instance-class-buttons']),/No matching classes/);

  ids = await loadPage('catalog-explorer.js','?class=cars&tab=tasks');
  assert.doesNotMatch(text(ids['instance-detail-content']), /Task-Context|No tasks or contexts/);
  assert.match(text(ids['instance-detail-content']), /has_long_range/);
  ids = await loadPage('catalog-explorer.js','',true);
  assert.match(text(ids['instance-detail-content']), /could not be loaded/);
  assert.ok(fs.readFileSync('docs/index.html','utf8').includes('href="catalog/"'));
  assert.ok(fs.readFileSync('docs/catalog/index.html','utf8').includes('id="catalog-version"'));
  assert.ok(!fs.existsSync('docs/task-context/index.html'));
  assert.ok(!fs.readFileSync('docs/index.html','utf8').includes('task-context/'));
  console.log('Class browser checks passed: icons, search, feature/context/task tabs, releases, zero values, empty states and load failure.');
})().catch(error=>{console.error(error);process.exitCode=1;});
