/* Four independent dry/wet reference contexts arranged as a continuous path. */
const birdAnimationAssets = new URL('.', document.currentScript.src);
(async () => {
  const mount = document.querySelector('[data-bird-demo]');
  if (!mount) return;
  const load = async name => {
    const response = await fetch(new URL(name, birdAnimationAssets), { cache: 'no-cache' });
    if (!response.ok) throw new Error(`${name}: ${response.status}`);
    return response.text();
  };
  const [markup, svg, json] = await Promise.all(['component.html', 'scene.svg', 'scenes.json'].map(load));
  const regions = JSON.parse(json);
  if (regions.length !== 4) throw new Error('The path needs exactly four regions');
  mount.innerHTML = markup;
  const get = id => mount.querySelector(`#${id}`);
  const section = mount.querySelector('.bird-demo-section');
  const traveller = get('birdTraveller');
  get('birdSprite').innerHTML = svg;
  const zones = [...mount.querySelectorAll('[data-zone]')];
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const cycleMs = 24000;
  const feedingMs = 650;
  let elapsed = 0;
  let previous = null;
  let frame = null;
  let playing = !motion.matches;
  let current = -1;
  let captionIndex = -1;
  const caption = get('birdStoryCaption');

  function render() {
    const time = elapsed % cycleMs;
    const width = get('birdLandscape').clientWidth || 700;
    // Align the beak, rather than the bird's center, with the fish at 30% (20% into the puddle quarter).
    const feedingX = Math.max(25.2, Math.min(28, 30 - 29 / width * 100));
    const travelMs = cycleMs - feedingMs;
    const arrival = (feedingX - 6) / 88 * travelMs;
    const feeding = time >= arrival && time < arrival + feedingMs;
    const touchingWater = time >= arrival + 180;
    const travelTime = time < arrival ? time : time < arrival + feedingMs ? arrival : time - feedingMs;
    const x = 6 + 88 * travelTime / travelMs;
    const index = Math.min(3, Math.floor(x / 25));
    traveller.style.left = `${x.toFixed(3)}%`;
    const region = regions[index];
    const walking = region.answerValue === 'false';
    if (index !== current) {
      current = index;
      traveller.classList.toggle('walking', walking);
      traveller.classList.toggle('flying', !walking);

      zones.forEach((zone, i) => zone.setAttribute('data-active', String(i === index)));
    }
    // Describe wet wings only after Alice actually reaches the water.
    const storyIndex = index === 1 && !touchingWater ? 0 : index;
    if (storyIndex !== captionIndex) {
      captionIndex = storyIndex;
      caption.textContent = regions[storyIndex].caption;
      if (!motion.matches && caption.animate) {
        caption.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 280 });
      }
    }
    section.classList.toggle('is-wet', index === 3 || (index === 1 && touchingWater));
    section.classList.toggle('is-feeding', feeding);
    section.classList.toggle('fish-eaten', time >= arrival + 180);
    section.classList.toggle('is-splashing', feeding && touchingWater && time < arrival + 550);
    section.classList.toggle('is-paused', !playing || document.hidden);
  }

  function tick(now) {
    frame = null;
    if (!playing || document.hidden) return;
    if (previous !== null) elapsed += Math.min(now - previous, 100);
    previous = now;
    render();
    frame = requestAnimationFrame(tick);
  }

  function sync() {
    if (frame !== null) cancelAnimationFrame(frame);
    frame = null;
    previous = null;
    render();
    if (playing && !document.hidden) frame = requestAnimationFrame(tick);
  }

  motion.addEventListener('change', () => { playing = !motion.matches; sync(); });
  document.addEventListener('visibilitychange', sync);
  sync();
})().catch(error => {
  console.error('Bird path could not start:', error);
  const mount = document.querySelector('[data-bird-demo]');
  if (mount) mount.textContent = 'Animation unavailable. See the interactive dataset examples below.';
});
