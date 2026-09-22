(() => {
  const token = () => document.querySelector('[name="csrfmiddlewaretoken"]')?.value || '';

  document.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-wishlist-item]');
    if (!button || button.disabled) return;
    button.disabled = true;
    try {
      const body = new FormData();
      body.append('item_id', button.dataset.wishlistItem);
      const response = await fetch(button.dataset.url, {
        method: 'POST',
        headers: {'X-CSRFToken': token(), 'X-Requested-With': 'XMLHttpRequest'},
        body,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.erro || 'Não foi possível atualizar a Wishlist.');
      document.querySelectorAll(`[data-wishlist-item="${data.item_id}"]`).forEach((itemButton) => {
        itemButton.classList.toggle('adicionado', data.adicionado);
        itemButton.setAttribute('aria-pressed', String(data.adicionado));
        const icon = itemButton.querySelector('span[aria-hidden="true"]');
        if (icon) icon.textContent = data.adicionado ? '♥' : '♡';
        const text = itemButton.querySelector('[data-wishlist-texto]');
        if (text) text.textContent = data.adicionado ? 'Salvo na Wishlist' : 'Adicionar à Wishlist';
      });
      if (!data.adicionado && document.body.querySelector('.wishlist-pagina')) {
        button.closest('.product-card')?.remove();
        if (!document.querySelector('.wishlist-pagina .product-card')) location.reload();
      }
    } catch (error) {
      window.alert(error.message);
    } finally {
      button.disabled = false;
    }
  });
})();
