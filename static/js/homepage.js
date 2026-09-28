(() => {
  const header = document.querySelector('.site-header');
  const hero = document.querySelector('.homepage-hero');
  if (!header || !hero) return;
  const updateHeight = () => {
    hero.style.setProperty('--homepage-header-height', `${header.getBoundingClientRect().height}px`);
  };
  updateHeight();
  if ('ResizeObserver' in window) {
    new ResizeObserver(updateHeight).observe(header);
  } else {
    window.addEventListener('resize', updateHeight);
  }
})();
