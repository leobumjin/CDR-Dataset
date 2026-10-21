/* Public catalog definitions and successful generation scopes. */
(() => {
  const assets = new URL('.', document.currentScript.src);
  const panel = document.getElementById('catalog-panel');
  const classSelect = document.getElementById('catalog-class');
  const search = document.getElementById('catalog-search');
  const classButtons = document.getElementById('instance-class-buttons');
  let selectedClass = '';
  const labelSelect = document.getElementById('instance-label-source');
  let labelSources = {};
  let labelsReady = false;
  let labelsFailed = false;
  let selectedInstance = null;
  const taskSelect = document.getElementById('catalog-task');
  const params = new URLSearchParams(window.location.search);
  let data;
  const view = document.body.dataset.catalogView || 'tasks';
  let page = 0;
  const pageSize = 24;
  const el = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  const className = id => data.classes.find(item => item.id === id)?.name || id;
  const matches = text => text.toLowerCase().includes((search?.value || '').trim().toLowerCase());
  const collection = (item, id) => {
    const number = Number(id.slice(id.lastIndexOf('_') + 1));
    return item.collections.find(source => number >= source.indices[0] && number <= source.indices[1])?.source || 'Unspecified';
  };
  function render() {
    if (!panel) return;
    const cid = classSelect ? classSelect.value : selectedClass;
    const tid = taskSelect?.value || '';
    const scope = labelSources[labelSelect?.value];
    const selected = data.classes.filter(item => (!cid || item.id === cid) && (!scope?.classes?.length || scope.classes.includes(item.id)));
    const fragment = document.createDocumentFragment();
    panel.setAttribute('aria-labelledby', 'catalog-title');
    let records;
    if (view === 'instances') {
      records = selected.flatMap(item => Object.entries(item.instances).map(([id, instance]) => ({id, ...instance, class: item, source: collection(item, id)})))
        .filter(item => (!scope?.instance_range || (Number(item.id.split('_').at(-1)) >= scope.instance_range[0] && Number(item.id.split('_').at(-1)) <= scope.instance_range[1])) && matches(`${item.id} ${item.name} ${item.class.name} ${item.source}`));
    } else {
      records = data.tasks.filter(task => (!cid || task.bindings.some(binding => binding.class_id === cid)) && matches(`${task.id} ${task.name} ${task.bindings.map(binding => `${binding.class_id} ${binding.query_template}`).join(' ')}`));
    }
    const maxPage = Math.max(0, Math.ceil(records.length / pageSize) - 1);
    page = Math.min(page, maxPage);
    fragment.append(el('p', `${records.length.toLocaleString()} ${view}${(search?.value || '').trim() ? ' matching your search' : ''}`, 'catalog-result-count'));
    if (view === 'instances') {
      renderInstances(records);
      return;
    }
    if (!records.length) fragment.append(el('p', 'No results. Try another class or search term.', 'catalog-empty'));
    const grid = el('div', undefined, view === 'instances' ? 'catalog-instance-grid' : 'catalog-entry-grid');
    for (const record of records.slice(page * pageSize, (page + 1) * pageSize)) {
      const card = el('article', undefined, 'catalog-entry');
        card.append(el('p', record.id, 'catalog-entry-id'), el('h3', record.name));
        for (const binding of record.bindings.filter(binding => !cid || binding.class_id === cid)) {
          card.append(el('p', `${className(binding.class_id)} · ${binding.query_template}`, 'catalog-task-binding'));
          card.append(el('p', binding.target_definition));
        }
        const button = el('a', 'View task–context labels', 'catalog-text-button');
        const contextUrl = new URL('../task-context/', assets);
        contextUrl.searchParams.set('task', record.id);
        contextUrl.searchParams.set('class', cid || record.bindings[0].class_id);
        button.href = contextUrl;
        card.append(button);
      grid.append(card);
    }
    fragment.append(grid);
    if (records.length > pageSize) {
      const pagination = el('nav', undefined, 'catalog-pagination');
      pagination.setAttribute('aria-label', 'Catalog pages');
      const previous = el('button', 'Previous');
      const next = el('button', 'Next');
      previous.type = next.type = 'button';
      previous.disabled = page === 0;
      next.disabled = page === maxPage;
      previous.addEventListener('click', () => { page--; render(); panel.focus(); });
      next.addEventListener('click', () => { page++; render(); panel.focus(); });
      pagination.append(previous, el('span', `Page ${page + 1} of ${maxPage + 1}`), next);
      fragment.append(pagination);
    }
    panel.replaceChildren(fragment);
  }
  function renderInstances(records) {
    const listHost = document.getElementById('instance-list-content');
    const detail = document.getElementById('instance-detail-content');
    const title = document.getElementById('instance-list-title');
    title.textContent = `${records.length.toLocaleString()} instances`;
    if (!records.length) {
      listHost.replaceChildren(el('p', 'No results. Try another class or search term.', 'catalog-empty'));
      detail.replaceChildren(el('p', 'Select an instance to view its features.', 'catalog-empty'));
      return;
    }
    if (!records.some(record => record.id === selectedInstance)) selectedInstance = records[0].id;
    const selected = records.find(record => record.id === selectedInstance);
    const list = el('ul', undefined, 'instance-list');
    for (const record of records) {
      const item = el('li');
      const button = el('button', undefined, 'instance-list-button');
      button.type = 'button';
      button.setAttribute('aria-pressed', String(record.id === selectedInstance));
      button.append(el('span', record.name), el('span', record.id, 'catalog-entry-id'));
      button.addEventListener('click', () => {
        const scrollTop = list.scrollTop;
        selectedInstance = record.id;
        render();
        const nextList = listHost.querySelector('.instance-list');
        if (nextList) {
          nextList.scrollTop = scrollTop;
          nextList.querySelector('[aria-pressed="true"]')?.focus({preventScroll: true});
        }
      });
      item.append(button);
      list.append(item);
    }
    listHost.replaceChildren(list);
    detail.replaceChildren();
    const heading = el('div', undefined, 'instance-detail-heading');
    heading.append(el('h2', selected.name, 'instance-detail-title'), el('span', selected.id, 'catalog-entry-id'));
    detail.append(heading);
    const source = labelSources[labelSelect?.value];
    const note = !labelsReady ? 'Loading label values…' : labelsFailed ? 'Label data could not be loaded. Values are unavailable.' : source ? (source.available === false ? `Release ${labelSelect.value} · labels unavailable` : `Release ${labelSelect.value}`) : 'No release selected.';
    detail.append(el('p', note, 'catalog-entry-meta'));
    const table = el('table', undefined, 'instance-feature-table');
    const caption = el('caption', `Features and label values for ${selected.name}`, 'sr-only');
    const head = el('thead');
    const headers = el('tr');
    for (const title of ['Feature', 'Value']) {
      const cell = el('th', title); cell.setAttribute('scope', 'col'); headers.append(cell);
    }
    head.append(headers);
    const body = el('tbody');
    Object.entries(selected.class.features).filter(([fid]) => !source?.feature_range || (Number(fid.split('_').at(-1)) >= source.feature_range[0] && Number(fid.split('_').at(-1)) <= source.feature_range[1])).forEach(([fid, feature]) => {
      const row = el('tr');
      const name = el('th'); name.setAttribute('scope', 'row');
      const info = el('span', undefined, 'instance-feature-info');
      const trigger = el('span', feature.name, 'instance-feature-trigger');
      trigger.tabIndex = 0;
      const tooltip = el('span', undefined, 'instance-feature-tooltip');
      tooltip.id = `feature-tooltip-${fid}`;
      tooltip.setAttribute('role', 'tooltip');
      trigger.setAttribute('aria-describedby', tooltip.id);
      tooltip.append(el('span', fid, 'catalog-entry-id'), el('span', feature.description, 'instance-feature-description'));
      trigger.addEventListener('keydown', event => {
        if (event.key === 'Escape') info.classList.add('tooltip-dismissed');
      });
      for (const event of ['mouseenter', 'focusin']) info.addEventListener(event, () => info.classList.remove('tooltip-dismissed'));
      info.append(trigger, tooltip);
      name.append(info);
      const stored = source?.features?.[selected.class.id]?.[selected.id];
      const value = stored && Object.prototype.hasOwnProperty.call(stored, fid) ? stored[fid] : null;
      const display = value === null || value === undefined ? 'NA' : typeof value === 'object' ? JSON.stringify(value) : String(value);
      row.append(name, el('td', labelsReady ? display : '…', display === 'NA' ? 'instance-label-na' : 'instance-label-value'));
      body.append(row);
    });
    table.append(caption, head, body);
    detail.append(table);
  }
  labelSelect?.addEventListener('change', () => { if (data) render(); });
  [classSelect, search, taskSelect].filter(Boolean).forEach(control => control.addEventListener(control === search ? 'input' : 'change', () => { page = 0; if (data) render(); }));
  async function get(name) {
    const response = await fetch(new URL(name, assets));
    if (!response.ok) throw new Error(`${name}: ${response.status}`);
    return response.json();
  }
  if (view === 'instances') get('instance_labels.json').then(payload => {
    labelSources = payload.sources;
    Object.keys(labelSources).forEach(id => labelSelect?.append(new Option(`Release ${id}`, id)));
    if (labelSelect) {
      const requested = params.get('release');
      labelSelect.value = Object.hasOwn(labelSources, requested) ? requested : (Object.keys(labelSources).at(-1) || '');
    }
    labelsReady = true;
    if (data) render();
  }).catch(() => { labelsReady = true; labelsFailed = true; if (data) render(); });
  get('catalog.json').then(catalog => {
    data = catalog;
    let instances = 0;
    let features = 0;
    data.classes.forEach(item => {
      classSelect?.append(new Option(item.name, item.id));
      instances += Object.keys(item.instances).length;
      features += Object.keys(item.features).length;
    });
    if (data.classes.some(item => item.id === params.get('class'))) selectedClass = params.get('class');
    if (classSelect) classSelect.value = selectedClass;
    if (classButtons) {
      const options = [{id: '', name: 'All'}, ...data.classes];
      for (const item of options) {
        const button = el('button', undefined, 'instance-class-button');
        button.type = 'button';
        button.dataset.classId = item.id;
        button.setAttribute('aria-pressed', String(item.id === selectedClass));
        const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        icon.setAttribute('viewBox', '0 0 48 48');
        icon.setAttribute('aria-hidden', 'true');
        if (item.id) {
          const iconId = {bird:'bird',human:'human',legal_case:'legal',mammal:'mammal',plant:'plant'}[item.id];
          const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
          use.setAttribute('href', new URL(`project-overview/icons.svg#${iconId}`, assets));
          icon.append(use);
        } else {
          for (const [x, y] of [[8,8],[28,8],[8,28],[28,28]]) {
            const square = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            for (const [key, value] of Object.entries({x,y,width:12,height:12,rx:2})) square.setAttribute(key, value);
            icon.append(square);
          }
        }
        button.append(icon, el('span', item.name));
        button.addEventListener('click', () => {
          selectedClass = item.id;
          selectedInstance = null;
          classButtons.querySelectorAll('button').forEach(control => control.setAttribute('aria-pressed', String(control === button)));
          render();
        });
        classButtons.append(button);
      }
    }
    if (search) search.value = params.get('q') || '';
    selectedInstance = params.get('instance');
    if (taskSelect) {
      data.tasks.forEach(task => taskSelect.append(new Option(task.name, task.id)));
      if (data.tasks.some(task => task.id === params.get('task'))) taskSelect.value = params.get('task');
    }
    const counts = document.getElementById('catalog-stats');
    [[data.tasks.length, 'Tasks'], [instances, 'Instances'], [data.tasks.reduce((sum, task) => sum + Object.keys(task.contexts).length, 0), 'Contexts'], [features, 'Features']].forEach(([count, label]) => {
      const item = el('div');
      item.append(el('strong', count.toLocaleString()), el('span', label));
      counts?.append(item);
    });
    const combinations = document.getElementById('catalog-combinations');
    data.classes.forEach(item => data.tasks.filter(task => task.bindings.some(binding => binding.class_id === item.id)).forEach(task => {
      const li = el('li', undefined, 'category-card');
      const link = el('a');
      const instanceUrl = new URL('../instances/', assets);
      instanceUrl.searchParams.set('class', item.id);
      link.href = instanceUrl;
      const iconId = {bird: 'bird', human: 'human', legal_case: 'legal', mammal: 'mammal', plant: 'plant'}[item.id];
      const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      icon.setAttribute('class', 'category-icon');
      icon.setAttribute('viewBox', '0 0 48 48');
      icon.setAttribute('aria-hidden', 'true');
      const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
      use.setAttribute('href', new URL(`project-overview/icons.svg#${iconId}`, assets));
      icon.append(use);
      link.append(icon, el('strong', `${item.name} – ${task.name}`), el('span', `${Object.keys(item.instances).length} instances`));
      li.append(link);
      combinations?.append(li);
    }));
    render();
  }).catch(() => {
    if (!panel) {
      document.getElementById('catalog-combinations')?.replaceChildren(el('li', 'Catalog preview is unavailable. Use the Instances or Task–Context page above.'));
      return;
    }
    panel.replaceChildren(el('p', 'The catalog could not be loaded. Please refresh or download the definitions below.'));
    const link = el('a', 'Catalog JSON'); link.href = new URL('catalog.json', assets); panel.append(link);
  });
})();
