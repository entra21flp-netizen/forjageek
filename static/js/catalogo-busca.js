document.addEventListener('DOMContentLoaded', () => {
  const campoBusca = document.querySelector('#busca-figuras');
  const campoFranquia = document.querySelector('#franquia-figuras');
  const grupos = [...document.querySelectorAll('[data-catalogo-grupo]')];
  const vazio = document.querySelector('.catalogo-vazio-dinamico');

  if (!campoBusca || !campoFranquia || !grupos.length) return;

  const normalizar = (valor) => String(valor || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('pt-BR')
    .trim();

  const filtrar = () => {
    const busca = normalizar(campoBusca.value);
    const franquia = normalizar(campoFranquia.value);
    let totalVisivel = 0;

    grupos.forEach((grupo) => {
      const cards = [...grupo.querySelectorAll('.figura-card')];
      let visiveisNoGrupo = 0;

      cards.forEach((card) => {
        const correspondeBusca = !busca || normalizar(card.dataset.textoBusca).includes(busca);
        const correspondeFranquia = !franquia || normalizar(card.dataset.franquia) === franquia;
        const visivel = correspondeBusca && correspondeFranquia;
        card.hidden = !visivel;
        if (visivel) visiveisNoGrupo += 1;
      });

      grupo.hidden = visiveisNoGrupo === 0;
      const contador = grupo.querySelector('[data-contador]');
      if (contador) contador.textContent = `${visiveisNoGrupo} ${visiveisNoGrupo === 1 ? 'modelo' : 'modelos'}`;
      totalVisivel += visiveisNoGrupo;
    });

    if (vazio) vazio.hidden = totalVisivel !== 0;
  };

  campoBusca.addEventListener('input', filtrar);
  campoFranquia.addEventListener('change', filtrar);
});
