(() => {
  const form = document.querySelector('form[data-consultar-codigo-url]');
  const input = document.getElementById('id_codigo_barras_ean_jan');
  const button = document.getElementById('buscar-codigo-barras');
  const result = document.getElementById('codigo-barras-resultado');
  const model = document.getElementById('id_modelo');
  if (!form || !input || !button || !result || !model) return;

  function show(message, kind = '') {
    result.hidden = false;
    result.className = `codigo-barras-resultado ${kind}`.trim();
    result.textContent = message;
  }

  function fillIfEmpty(id, value, filled, label) {
    const field = document.getElementById(id);
    const cleanValue = typeof value === 'string' ? value.trim() : '';
    if (!field || !cleanValue || field.value.trim()) return;
    field.value = cleanValue;
    filled.push(label);
  }

  function applyExternalProduct(product) {
    const filled = [];
    fillIfEmpty('id_nome_modelo', product.nome_modelo, filled, 'nome do modelo');
    fillIfEmpty('id_fabricante', product.fabricante, filled, 'fabricante');
    fillIfEmpty('id_imagem_modelo', product.imagem_modelo, filled, 'imagem do modelo');
    const extra = product.categoria_origem ? ` Categoria informada pela fonte: ${product.categoria_origem}.` : '';
    const changes = filled.length ? ` Preenchemos: ${filled.join(', ')}.` : '';
    show(`Referência encontrada na UPCitemdb.${changes}${extra} Revise todos os campos antes de salvar.`, 'success');
  }

  button.addEventListener('click', async () => {
    const code = input.value.replace(/\D/g, '');
    input.value = code;
    if (code.length < 8 || code.length > 13) {
      show('Digite um código EAN, JAN ou UPC com 8 a 13 números.', 'error');
      input.focus();
      return;
    }

    const originalLabel = button.textContent;
    button.disabled = true;
    button.textContent = 'Buscando…';
    result.hidden = true;
    const payload = new FormData();
    payload.append('codigo', code);
    try {
      const response = await fetch(form.dataset.consultarCodigoUrl, {
        method: 'POST',
        headers: { 'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value },
        body: payload,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.erro || 'Não foi possível consultar o código agora.');
      if (!data.encontrado) {
        show(data.mensagem, 'notice');
      } else if (data.origem === 'catalogo_forjageek') {
        model.value = String(data.modelo_id);
        model.dispatchEvent(new Event('change', { bubbles: true }));
        show(`${data.mensagem} O modelo “${data.produto.nome_modelo || data.produto.nome_personagem}” foi selecionado.`, 'success');
      } else {
        applyExternalProduct(data.produto || {});
      }
    } catch (error) {
      show(error.message || 'Não foi possível consultar o código agora.', 'error');
    } finally {
      button.disabled = false;
      button.textContent = originalLabel;
    }
  });

  input.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' || event.isComposing) return;
    event.preventDefault();
    button.click();
  });
})();
