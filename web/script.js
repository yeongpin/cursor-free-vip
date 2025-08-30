const navToggle = document.querySelector('.nav-toggle');
const siteNav = document.querySelector('.site-nav');
navToggle?.addEventListener('click', () => {
  const isOpen = siteNav?.classList.toggle('open');
  navToggle.setAttribute('aria-expanded', String(!!isOpen));
});

// Tabs
const tabs = Array.from(document.querySelectorAll('.tab'));
const panels = {
  linux: document.querySelector('#panel-linux'),
  arch: document.querySelector('#panel-arch'),
  windows: document.querySelector('#panel-windows')
};

tabs.forEach(t => t.addEventListener('click', () => {
  tabs.forEach(x => x.classList.remove('active'));
  t.classList.add('active');
  const key = t.dataset.tab;
  Object.values(panels).forEach(p => p?.classList.remove('active'));
  panels[key]?.classList.add('active');
}));

// Year
const y = document.querySelector('#year');
if (y) y.textContent = String(new Date().getFullYear());

// Respect prefers-reduced-motion for potential future animations
if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  document.documentElement.classList.add('reduced-motion');
}