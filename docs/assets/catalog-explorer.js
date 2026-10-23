/* Definitions contain feature groups; samples exist only in explicit releases. */
(() => {
  const node = id => document.getElementById(id);
  const home = node('catalog-combinations');
  const detail = node('instance-detail-content');
  if (!home && !detail) return;
  const base = new URL('.', document.currentScript.src);
  const el = (tag, text, className) => {
    const item = document.createElement(tag);
    if (text !== undefined) item.textContent = text;
    if (className) item.className = className;
    return item;
  };
  async function read(name) {
    const response = await fetch(new URL(name, base));
    if (!response.ok) throw new Error(name);
    return response.json();
  }
  const iconIds = {bird: 'bird', human: 'human', legal_case: 'legal', mammal: 'mammal', plant: 'plant',
    cars: 'car', foods: 'food', garments: 'garment', smartphones: 'smartphone', kitchenware: 'kitchenware'};
  function iconFor(id) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'category-icon');
    svg.setAttribute('viewBox', '0 0 48 48');
    svg.setAttribute('aria-hidden', 'true');
    if (id) {
      const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
      use.setAttribute('href', new URL(`project-overview/icons.svg#${iconIds[id] || id}`, base));
      svg.append(use);
    } else {
      for (const [x, y] of [[8, 8], [28, 8], [8, 28], [28, 28]]) {
        const square = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        for (const [key, value] of Object.entries({x, y, width: 12, height: 12, rx: 2})) square.setAttribute(key, value);
        svg.append(square);
      }
    }
    return svg;
  }
  const display = value => value === undefined || value === null ? '-' : typeof value === 'object' ? JSON.stringify(value) : String(value);
  Promise.all([read('catalog.json'), home ? Promise.resolve({sources: {}}) : read('release_samples.json')]).then(([catalog, releases]) => {
    if (home) {
      home.replaceChildren();
      const midpoint = Math.ceil(catalog.classes.length / 2);
      for (const groups of [catalog.classes.slice(0, midpoint), catalog.classes.slice(midpoint)]) {
        if (!groups.length) continue;
        const row = el('div', undefined, 'instance-stream-row');
        const track = el('div', undefined, 'instance-stream-track');
        for (const duplicate of [false, true]) {
          const items = el('ul', undefined, 'instance-stream-group');
          if (duplicate) items.setAttribute('aria-hidden', 'true');
          for (const group of groups) {
            const chip = el('li', undefined, 'instance-stream-chip');
            const label = el('span', undefined, 'instance-stream-label');
            label.append(el('strong', group.name));
            chip.append(iconFor(group.id), label);
            items.append(chip);
          }
          track.append(items);
        }
        row.append(track);
        home.append(row);
      }
      return;
    }
    const params = new URLSearchParams(window.location.search);
    const version = node('catalog-version');
    version.replaceChildren(new Option(catalog.catalog_version, catalog.catalog_version));
    version.value = catalog.catalog_version;
    const source = node('instance-label-source');
    const buttons = node('instance-class-buttons');
    const classSearch = node('class-search');
    let cid = params.get('class') || '';
    let selectedId = params.get('sample') || '';
    const tabNames = ['Features', 'Task-Context'];
    let selectedContext = '';
    let activeTab = ['tasks', 'contexts', 'task-context'].includes(params.get('tab')) ? 'Task-Context' : 'Features';
    source.replaceChildren(new Option('Catalog definitions', ''));
    for (const id of Object.keys(releases.sources)) source.append(new Option(`Release ${id}`, id));
    source.value = Object.hasOwn(releases.sources, params.get('release')) ? params.get('release') : '';
    function groupsFor(release) {
      if (!release?.definitions) return catalog.classes;
      return release.definitions.classes.map(c => ({...c, features: Object.fromEntries(c.features.map(f => [f.id, f]))}));
    }
    function render() {
      const release = releases.sources[source.value];
      const groups = groupsFor(release);
      if (!groups.some(c => c.id === cid)) cid = groups[0]?.id || '';
      const available = groups.filter(c => c.id === cid);
      buttons.replaceChildren();
      const classQuery = (classSearch?.value || '').trim().toLowerCase();
      const matchingGroups = groups.filter(c => `${c.id} ${c.name}`.toLowerCase().includes(classQuery));
      for (const [id, name] of matchingGroups.map(c => [c.id, c.name])) {
        const button = el('button', undefined, 'instance-class-button');
        button.append(iconFor(id), el('span', name));
        button.setAttribute('aria-pressed', String(cid === id));
        button.addEventListener('click', () => { cid = id; selectedId = ''; render(); });
        buttons.append(button);
      }
      if (!matchingGroups.length) buttons.append(el('p', 'No matching classes.', 'catalog-empty'));
      const records = available.flatMap(c => Object.entries(release?.samples?.[c.id] || {}).map(([id, features]) => ({id, features, group: c})));
      const selected = records.find(s => s.id === selectedId) || records[0];
      selectedId = selected?.id || '';
      detail.replaceChildren();
      const group = selected?.group || available[0];
      if (!group) { detail.append(el('p', 'No matching feature group.')); return; }
      const taskDefinitions = release?.definitions?.tasks || catalog.tasks;
      const boundTasks = taskDefinitions.filter(t => t.bindings.some(b => b.class_id === group.id));
      const availableTabs = boundTasks.length ? tabNames : ['Features'];
      if (!availableTabs.includes(activeTab)) activeTab = 'Features';
      detail.append(el('h2', group.name));
      const tabs = el('div', undefined, 'class-detail-tabs');
      tabs.setAttribute('role', 'tablist');
      tabs.setAttribute('aria-label', 'Class information');
      for (const name of availableTabs) {
        const tab = el('button', name, 'class-detail-tab');
        tab.id = `class-tab-${name.toLowerCase()}`;
        tab.type = 'button';
        tab.setAttribute('role', 'tab');
        tab.setAttribute('aria-selected', String(activeTab === name));
        tab.setAttribute('aria-controls', 'class-detail-panel');
        tab.tabIndex = activeTab === name ? 0 : -1;
        tab.addEventListener('click', () => { activeTab = name; render(); });
        tab.addEventListener('keydown', event => {
          let index = availableTabs.indexOf(name);
          if (event.key === 'ArrowRight') index = (index + 1) % availableTabs.length;
          else if (event.key === 'ArrowLeft') index = (index + availableTabs.length - 1) % availableTabs.length;
          else if (event.key === 'Home') index = 0;
          else if (event.key === 'End') index = availableTabs.length - 1;
          else return;
          event.preventDefault();
          activeTab = availableTabs[index];
          render();
          node(`class-tab-${activeTab.toLowerCase()}`)?.focus();
        });
        tabs.append(tab);
      }
      const content = el('div', undefined, 'class-detail-panel');
      content.id = 'class-detail-panel';
      content.setAttribute('role', 'tabpanel');
      content.setAttribute('aria-labelledby', `class-tab-${activeTab.toLowerCase()}`);
      detail.append(tabs, content);
      if (activeTab === 'Task-Context') {
        const entries = boundTasks.flatMap(task => {
          const binding = task.bindings.find(b => b.class_id === group.id);
          const definitions = task.contexts || Object.fromEntries((release?.definitions?.contexts || [])
            .filter(c => c.task_id === task.id && (!c.class_id || c.class_id === group.id))
            .map(c => [c.id, c]));
          return (binding.contexts || Object.keys(definitions)).filter(id => definitions[id])
            .map(id => ({key: `${task.id}:${id}`, id, task: task.name, question: binding.query_template, description: definitions[id].description}));
        });
        if (!entries.length) { content.append(el('p', 'No tasks or contexts are defined for this class.', 'catalog-empty')); return; }
        const current = entries.find(c => c.key === selectedContext) || entries[0];
        selectedContext = current.key;
        content.append(el('h3', `Task: ${current.question}`, 'context-task-question'));
        const workspace = el('div', undefined, 'context-workspace');
        const choices = el('nav', undefined, 'context-choices');
        choices.setAttribute('aria-label', 'Contexts');
        const description = el('article', undefined, 'context-description');
        description.id = 'selected-context-description';
        description.append(el('h4', current.id), el('p', current.description));
        for (const entry of entries) {
          const button = el('button', entry.id, 'context-choice');
          button.type = 'button';
          button.setAttribute('aria-pressed', String(entry.key === selectedContext));
          button.setAttribute('aria-controls', description.id);
          button.title = entry.task;
          button.addEventListener('click', () => { selectedContext = entry.key; render(); });
          choices.append(button);
        }
        workspace.append(choices, description);
        content.append(workspace);
        return;
      }
      const table = el('table', undefined, 'instance-feature-table');
      const thead = el('thead');
      const tbody = el('tbody');
      const head = el('tr');
      head.append(el('th', 'Feature'), el('th', 'T+F+U=1'));
      thead.append(head);
      table.append(thead, tbody);
      for (const [fid, f] of Object.entries(group.features)) {
        const row = el('tr');
        const cell = el('th');
        cell.setAttribute('scope', 'row');
        const info = el('span', undefined, 'instance-feature-info');
        const trigger = el('button', f.name, 'instance-feature-trigger');
        trigger.setAttribute('aria-describedby', `feature-tip-${fid}`);
        const tooltip = el('span', `${fid} · ${f.description}`, 'instance-feature-tooltip');
        tooltip.id = `feature-tip-${fid}`;
        tooltip.setAttribute('role', 'tooltip');
        trigger.addEventListener('keydown', event => { if (event.key === 'Escape') info.classList.add('tooltip-dismissed'); });
        for (const event of ['mouseenter', 'focusin']) info.addEventListener(event, () => info.classList.remove('tooltip-dismissed'));
        info.append(trigger, tooltip);
        cell.append(info);
        row.append(cell, el('td', display(selected?.features[fid])));
        tbody.append(row);
      }
      content.append(table);
    }
    classSearch?.addEventListener('input', render);
    source.addEventListener('change', () => { selectedId = ''; render(); });
    render();
  }).catch(() => {
    const target = detail || home;
    target.replaceChildren(el('p', 'Data could not be loaded. Sample values are unavailable.', 'catalog-empty'));
  });
})();
