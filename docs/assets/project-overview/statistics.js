/* A few v1 examples, rather than exhaustive inventories. */
(() => {
  const examples = {
    domains: {title: 'Example domains', text: 'Birds · Humans · Mammals · Plants · Legal Cases'},
    queries: {title: 'One query per domain · examples', text: 'Birds: Can this bird fly?\nHumans: Can this person run?\nLegal Cases: Is this person guilty?'},
    contexts: {title: 'Example contexts', text: 'Birds: dry feathers / 20 m; wet feathers / 20 m\nPlants: hot drought / 30 days; watered / 7 days\nLegal Cases: ordinary situation; emergency'},
    entities: {title: 'Example entities', text: 'bird_010 · mammal_038 · plant_014 · human_018 · case_007\n100 entities in each domain.'},
    features: {title: 'Example experimental features · Birds', text: 'has_intact_wings: 1 · is_rested: 1 · is_large: 0\nSeven experimental judgments per entity; values are 0, 0.5, or 1.'},
    total: {title: 'Total = 2,500 samples', text: '5 domains × 1 query × 5 contexts × 100 entities = 2,500\nExample: can_fly + dry_20m + bird_010 → true'}
  };
  const panel = document.getElementById('statistic-examples');
  if (!panel) return;
  const title = document.getElementById('statistic-example-title');
  const text = document.getElementById('statistic-example-text');
  const buttons = [...document.querySelectorAll('[data-statistic]')];
  let active = null;
  let hideTimer = null;

  function hide() {
    clearTimeout(hideTimer);
    panel.hidden = true;
    buttons.forEach(button => button.classList.remove('active'));
    active = null;
  }

  function scheduleHide() {
    clearTimeout(hideTimer);
    hideTimer = setTimeout(hide, 120);
  }

  function place() {
    if (!active || panel.hidden) return;
    const anchor = active.getBoundingClientRect();
    const box = panel.getBoundingClientRect();
    const gap = 10;
    const left = Math.max(12, Math.min(anchor.left + anchor.width / 2 - box.width / 2, window.innerWidth - box.width - 12));
    let top = anchor.top - box.height - gap;
    if (top < 12) top = anchor.bottom + gap;
    top = Math.max(12, Math.min(top, window.innerHeight - box.height - 12));
    panel.style.left = `${left}px`;
    panel.style.top = `${top}px`;
  }

  buttons.forEach(button => {
    const show = () => {
      clearTimeout(hideTimer);
      active = button;
      const example = examples[button.dataset.statistic];
      title.textContent = example.title;
      text.textContent = example.text;
      panel.hidden = false;
      buttons.forEach(item => item.classList.toggle('active', item === button));
      place();
    };
    button.addEventListener('mouseenter', show);
    button.addEventListener('mouseleave', scheduleHide);
    button.addEventListener('focus', show);
    button.addEventListener('blur', scheduleHide);
    button.addEventListener('click', show);
  });
  panel.addEventListener('mouseenter', () => clearTimeout(hideTimer));
  panel.addEventListener('mouseleave', scheduleHide);
  window.addEventListener('resize', hide);
  window.addEventListener('scroll', hide, true);
  document.addEventListener('pointerdown', event => {
    if (!panel.contains(event.target) && !buttons.some(button => button.contains(event.target))) hide();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') hide();
  });
})();
