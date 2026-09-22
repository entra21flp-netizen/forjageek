(() => {
  const drawer = document.getElementById('carrinho-lateral');
  const overlay = document.getElementById('carrinho-overlay');
  const content = document.getElementById('carrinho-conteudo');
  const opener = document.getElementById('abrir-carrinho');
  const count = document.getElementById('carrinho-contagem');
  const live = document.getElementById('carrinho-status');
  const csrf = document.querySelector('#carrinho-csrf [name=csrfmiddlewaretoken]')?.value;
  if (!drawer || !overlay || !content || !opener) return;

  function openCart() {
    drawer.hidden = false;
    overlay.hidden = false;
    document.body.classList.add('carrinho-aberto');
    opener.setAttribute('aria-expanded', 'true');
    requestAnimationFrame(() => drawer.classList.add('aberto'));
    drawer.querySelector('.carrinho-fechar')?.focus();
  }

  function closeCart() {
    drawer.classList.remove('aberto');
    document.body.classList.remove('carrinho-aberto');
    opener.setAttribute('aria-expanded', 'false');
    window.setTimeout(() => { drawer.hidden = true; overlay.hidden = true; }, 220);
    opener.focus();
  }

  function updateButtons(ids) {
    document.querySelectorAll('[data-carrinho-adicionar]').forEach((button) => {
      const added = ids.includes(Number(button.dataset.carrinhoAdicionar));
      button.classList.toggle('adicionado', added);
      if (button.dataset.carrinhoFormato === 'icone') {
        button.innerHTML = `<span aria-hidden="true">${added ? '✓' : '🛒'}</span>`;
        button.setAttribute('aria-label', added ? 'Ver item no carrinho' : 'Adicionar item ao carrinho');
      } else {
        button.textContent = added ? '✓ Ver no carrinho' : 'Adicionar ao carrinho';
      }
      button.dataset.carrinhoNoCarrinho = added ? 'true' : 'false';
    });
  }

  async function changeCart(url, itemId, message) {
    const response = await fetch(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': csrf},
      body: new URLSearchParams({item_id: itemId}),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.erro || 'Não foi possível atualizar o carrinho.');
    content.innerHTML = data.html;
    count.textContent = data.quantidade;
    count.hidden = data.quantidade === 0;
    live.textContent = message;
    updateButtons(data.ids);
    return data;
  }

  opener.addEventListener('click', openCart);
  overlay.addEventListener('click', closeCart);
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape' && !drawer.hidden) closeCart(); });
  document.addEventListener('click', async (event) => {
    const closer = event.target.closest('[data-carrinho-fechar]');
    if (closer) { closeCart(); return; }

    const add = event.target.closest('[data-carrinho-adicionar]');
    if (add) {
      if (add.dataset.carrinhoNoCarrinho === 'true') { openCart(); return; }
      add.disabled = true;
      try {
        await changeCart(add.dataset.url, add.dataset.carrinhoAdicionar, 'Item adicionado ao carrinho.');
        openCart();
      } catch (error) { live.textContent = error.message; }
      finally { add.disabled = false; }
      return;
    }

    const remove = event.target.closest('[data-carrinho-remover]');
    if (remove) {
      remove.disabled = true;
      try { await changeCart(drawer.dataset.removerUrl, remove.dataset.carrinhoRemover, 'Item removido do carrinho.'); }
      catch (error) { live.textContent = error.message; remove.disabled = false; }
    }
  });
})();
