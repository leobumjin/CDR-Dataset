/* Reference-backed contexts for the additional domain conversation panels. */
const datasetExampleAssets = new URL('.', document.currentScript.src);
(async () => {
  const response = await fetch(new URL('examples.json', datasetExampleAssets));
  if (!response.ok) throw new Error(`Example configuration: ${response.status}`);
  const domains = await response.json();
  document.querySelectorAll('[data-demo-context]').forEach(button => {
    button.addEventListener('click', () => {
      const domain = button.dataset.demoDomain;
      const context = button.dataset.demoContext;
      const state = domains[domain].contexts[context];
      const card = document.getElementById(`${domain}-example`);
      card.querySelectorAll('[data-field]').forEach(field => {
        field.textContent = state[field.dataset.field];
      });
      card.classList.toggle('changed', state.code === '0');
      card.querySelectorAll('[data-demo-context]').forEach(item => {
        item.setAttribute('aria-pressed', String(item.dataset.demoContext === context));
      });
    });
  });
})().catch(error => console.error('Additional dataset examples could not load:', error));
