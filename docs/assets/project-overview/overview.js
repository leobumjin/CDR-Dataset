/* Update config.json to change the latest version and its category cards. */
const projectOverviewAssets = new URL('.', document.currentScript.src);
(async () => {
  const response = await fetch(new URL('config.json', projectOverviewAssets));
  if (!response.ok) throw new Error(`Project config: ${response.status}`);
  const config = await response.json();
  const version = config.latestVersion;
  const release = config.versions[version];
  if (!/^v[1-9][0-9]*$/.test(version) || !release || !Array.isArray(release.categories)) throw new Error('Invalid latest-version config');
  const link = document.getElementById('latest-version-link');
  const list = document.getElementById('latest-categories');
  if (!link || !list) return;
  const fragment = document.createDocumentFragment();
  for (const category of release.categories) {
    const item = document.createElement('li');
    item.className = 'category-card';
    const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    icon.setAttribute('class', 'category-icon');
    icon.setAttribute('viewBox', '0 0 48 48');
    icon.setAttribute('aria-hidden', 'true');
    const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
    use.setAttribute('href', `${new URL('icons.svg', projectOverviewAssets)}#${category.icon}`);
    icon.appendChild(use);
    const name = document.createElement('strong');
    name.textContent = category.name;
    const query = document.createElement('span');
    query.textContent = category.query;
    item.append(icon, name, query);
    fragment.appendChild(item);
  }
  link.textContent = version;
  link.href = `${config.datasetUrl.replace(/\/$/, '')}/tree/main/${version}`;
  list.replaceChildren(fragment);
})().catch(error => console.error('Latest-version overview could not update:', error));
