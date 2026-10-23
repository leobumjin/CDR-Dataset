/* Follow native document scrolling without intercepting wheel or touch events. */
(() => {
  const sections = [...document.querySelectorAll('.landing-section')];
  const links = [...document.querySelectorAll('.landing-nav a[href^="#"]')];
  if (!sections.length) return;
  let scheduled = false;
  function update() {
    scheduled = false;
    const boundary = Math.min(window.innerHeight * 0.35, 240);
    let current = sections[0];
    for (const section of sections) {
      if (section.getBoundingClientRect().top <= boundary) current = section;
    }
    for (const link of links) {
      if (link.hash === `#${current.id}`) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    }
  }
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(update);
  }
  window.addEventListener('scroll', schedule, {passive: true});
  window.addEventListener('resize', schedule);
  window.addEventListener('hashchange', schedule);
  update();
})();
