/* Inspect source-specific sample judgments for one class/task/context. */
(() => {
  const assets = new URL('.', document.currentScript.src);
  const node = id => document.getElementById(id);
  const controls = {class: node('judgment-class'), task: node('judgment-task'), context: node('judgment-context'), source: node('judgment-source')};
  const search = node('judgment-search');
  const filter = node('judgment-filter');
  const tooltip = node('sample-tooltip');
  const samples = node('judgment-samples');
  const count = node('judgment-count');
  const params = new URLSearchParams(window.location.search);
  let catalog;
  let taskSources = {};
  let featureSources = {};
  let labelsFailed = false;
  let featuresFailed = false;
  let hideTimer;
  const el = (tag, text, className) => {
    const item = document.createElement(tag);
    if (text !== undefined) item.textContent = text;
    if (className) item.className = className;
    return item;
  };
  const display = value => value === null || value === undefined ? 'NA' : String(value);
  async function get(file) {
    const response = await fetch(new URL(file, assets));
    if (!response.ok) throw new Error(`Cannot load ${file}`);
    return response.json();
  }
  function options(select, entries, requested) {
    select.replaceChildren(...entries.map(([id, label]) => new Option(label, id)));
    select.value = entries.some(([id]) => id === requested) ? requested : (entries[0]?.[0] || '');
    select.disabled = !entries.length;
  }
  function setClasses(requested) {
    const scope = taskSources[controls.source.value];
    const classes = catalog.classes.filter(item => !scope?.classes?.length || scope.classes.includes(item.id));
    options(controls.class, classes.map(item => [item.id, item.name]), requested);
  }
  const selectedClass = () => catalog.classes.find(item => item.id === controls.class.value);
  const selectedTask = () => catalog.tasks.find(item => item.id === controls.task.value);
  function setContexts(requested) {
    const task = selectedTask();
    const binding = task?.bindings.find(item => item.class_id === controls.class.value);
    const scope = taskSources[controls.source.value];
    const ids = task ? (binding.contexts || Object.keys(task.contexts)).filter(id => !scope || (scope.contexts[task.id] || []).includes(id)) : [];
    options(controls.context, ids.map(id => [id, id]), requested);
  }
  function setTasks(requested, context) {
    options(controls.task, catalog.tasks.filter(task => task.bindings.some(binding => binding.class_id === controls.class.value) && (!taskSources[controls.source.value] || Object.hasOwn(taskSources[controls.source.value].contexts, task.id))).map(task => [task.id, task.name]), requested);
    setContexts(context);
  }
  function hideTooltip() { tooltip.hidden = true; clearTimeout(hideTimer); }
  function scheduleHide() { clearTimeout(hideTimer); hideTimer = setTimeout(hideTooltip, 150); }
  tooltip.addEventListener('mouseenter', () => clearTimeout(hideTimer));
  tooltip.addEventListener('mouseleave', scheduleHide);
  document.addEventListener('keydown', event => { if (event.key === 'Escape') hideTooltip(); });
  function showTooltip(anchor, instanceClass, iid, instance) {
    clearTimeout(hideTimer);
    tooltip.replaceChildren(el('strong', instance.name), el('p', iid, 'catalog-entry-id'));
    const source = featureSources[controls.source.value];
    if (featuresFailed) tooltip.append(el('p', 'Feature labels are unavailable.', 'catalog-entry-meta'));
    const list = el('dl', undefined, 'sample-tooltip-features');
    Object.entries(instanceClass.features).filter(([fid]) => !source?.feature_range || (Number(fid.split('_').at(-1)) >= source.feature_range[0] && Number(fid.split('_').at(-1)) <= source.feature_range[1])).forEach(([fid, feature]) => {
      list.append(el('dt', feature.name), el('dd', display(source?.features?.[instanceClass.id]?.[iid]?.[fid])));
    });
    tooltip.append(list);
    const label = taskSources[controls.source.value];
    if (label?.synthetic || source?.synthetic) tooltip.append(el('p', 'Synthetic template values', 'catalog-entry-meta'));
    tooltip.hidden = false;
    const rect = anchor.getBoundingClientRect();
    const width = tooltip.offsetWidth;
    const height = tooltip.offsetHeight;
    const left = Math.max(8, Math.min(rect.left, window.innerWidth - width - 8));
    const below = rect.bottom + 8;
    const top = below + height < window.innerHeight ? below : Math.max(8, rect.top - height - 8);
    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
  }
  function render() {
    hideTooltip();
    const instanceClass = selectedClass();
    const task = selectedTask();
    const contextId = controls.context.value;
    const sourceId = controls.source.value;
    const source = taskSources[sourceId];
    const context = task?.contexts[contextId];
    const definition = node('judgment-definition');
    definition.replaceChildren();
    if (context) definition.append(el('h2', `${task.name} · ${contextId}`), el('p', context.description));
    node('judgment-source-note').textContent = labelsFailed ? 'Task label data could not be loaded. Values are unavailable.' : source ? (source.available === false ? `Release ${sourceId} · label values are unavailable; showing NA.` : `Release ${sourceId}`) : 'No release selected. Missing values are shown as NA.';
    const query = search.value.trim().toLowerCase();
    const totals = {true: 0, false: 0, ambiguous: 0, NA: 0};
    const cards = [];
    for (const [iid, instance] of Object.entries(instanceClass?.instances || {})) {
      const index = Number(iid.split('_').at(-1));
      if (source?.instance_range && (index < source.instance_range[0] || index > source.instance_range[1])) continue;
      if (source?.classes?.length && !source.classes.includes(instanceClass.id)) continue;
      if (!`${iid} ${instance.name}`.toLowerCase().includes(query)) continue;
      const value = display(source?.tasks?.[task?.id]?.[iid]?.[contextId]);
      const verdict = Object.hasOwn(totals, value) ? value : 'NA';
      totals[verdict]++;
      if (filter.value !== 'all' && filter.value !== verdict) continue;
      const card = el('a', undefined, `judgment-sample judgment-${verdict}`);
      const url = new URL('../instances/', assets);
      url.searchParams.set('class', instanceClass.id);
      url.searchParams.set('instance', iid);
      if (sourceId) url.searchParams.set('release', sourceId);
      card.href = url;
      card.setAttribute('aria-describedby', 'sample-tooltip');
      card.append(el('span', iid, 'catalog-entry-id'), el('span', instance.name, 'judgment-sample-name'), el('span', verdict, 'judgment-value'));
      card.addEventListener('mouseenter', () => showTooltip(card, instanceClass, iid, instance));
      card.addEventListener('focus', () => showTooltip(card, instanceClass, iid, instance));
      card.addEventListener('mouseleave', scheduleHide);
      card.addEventListener('blur', scheduleHide);
      cards.push(card);
    }
    count.textContent = `${cards.length} samples · ${totals.true} true · ${totals.false} false · ${totals.ambiguous} ambiguous · ${totals.NA} NA`;
    samples.replaceChildren(...(cards.length ? cards : [el('p', 'No samples match the current filters.', 'catalog-empty')]));
    const url = new URL(window.location.href);
    for (const [controlKey, select] of Object.entries(controls)) {
      const key = controlKey === 'source' ? 'release' : controlKey;
      if (select.value) url.searchParams.set(key, select.value); else url.searchParams.delete(key);
    }
    window.history.replaceState(null, '', url);
  }
  controls.class.addEventListener('change', () => { setTasks(controls.task.value); render(); });
  controls.task.addEventListener('change', () => { setContexts(); render(); });
  controls.context.addEventListener('change', render);
  controls.source.addEventListener('change', () => { setClasses(controls.class.value); setTasks(controls.task.value, controls.context.value); render(); });
  search.addEventListener('input', render);
  filter.addEventListener('change', render);
  window.addEventListener('resize', hideTooltip);
  window.addEventListener('scroll', hideTooltip, true);
  Promise.all([
    get('catalog.json'),
    get('task_labels.json').catch(() => { labelsFailed = true; return {sources: {}}; }),
    get('instance_labels.json').catch(() => { featuresFailed = true; return {sources: {}}; })
  ]).then(([data, labels, features]) => {
    catalog = data;
    taskSources = labels.sources;
    featureSources = features.sources;
    const sourceOptions = [['', 'No release selected'], ...Object.keys(taskSources).map(id => [id, `Release ${id}`])];
    const requestedSource = params.has('release') ? params.get('release') : (Object.keys(taskSources).at(-1) || '');
    options(controls.source, sourceOptions, requestedSource);
    setClasses(params.get('class'));
    setTasks(params.get('task'), params.get('context'));
    render();
  }).catch(() => {
    count.textContent = 'The catalog could not be loaded. Please refresh the page.';
    Object.values(controls).forEach(control => { control.disabled = true; });
  });
})();
