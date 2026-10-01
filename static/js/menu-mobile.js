document.addEventListener('DOMContentLoaded', () => {
  const header = document.querySelector('.site-header');
  const trigger = document.querySelector('.menu-mobile-gatilho');
  const navigation = document.getElementById('nav-principal');
  if (!header || !trigger || !navigation) return;

  const close = () => {
    header.classList.remove('menu-aberto');
    trigger.setAttribute('aria-expanded', 'false');
    trigger.querySelector('[aria-hidden="true"]').textContent = '☰';
    trigger.querySelector('.sr-only').textContent = 'Abrir menu principal';
  };

  trigger.addEventListener('click', () => {
    const open = !header.classList.contains('menu-aberto');
    header.classList.toggle('menu-aberto', open);
    trigger.setAttribute('aria-expanded', String(open));
    trigger.querySelector('[aria-hidden="true"]').textContent = open ? '×' : '☰';
    trigger.querySelector('.sr-only').textContent = open ? 'Fechar menu principal' : 'Abrir menu principal';
  });
  navigation.addEventListener('click', (event) => {
    if (event.target.closest('a')) close();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') close();
  });
  window.matchMedia('(min-width: 721px)').addEventListener('change', (event) => {
    if (event.matches) close();
  });
});
