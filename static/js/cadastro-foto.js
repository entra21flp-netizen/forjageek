(() => {
  const form = document.querySelector('form[data-analisar-url]');
  const input = document.getElementById('id_foto');
  const previews = document.getElementById('foto-previews');
  const placeholder = document.getElementById('foto-placeholder');
  const remove = document.getElementById('remover-foto');
  const analyze = document.getElementById('analisar-foto');
  const status = document.getElementById('foto-status');
  const result = document.getElementById('analise-resultado');
  if (!form || !input) return;

  const acceptedTypes = ['image/jpeg', 'image/png', 'image/webp'];
  let previewUrls = [];

  function showResult(message, kind = 'success') {
    result.hidden = false;
    result.className = `analise-resultado ${kind}`;
    result.textContent = message;
  }

  function clearPhoto() {
    previewUrls.forEach((url) => URL.revokeObjectURL(url));
    previewUrls = [];
    previews.querySelectorAll('.foto-miniatura').forEach((item) => item.remove());
    placeholder.hidden = false;
    remove.hidden = true;
    analyze.disabled = true;
    input.value = '';
    status.textContent = '';
    result.hidden = true;
  }

  input.addEventListener('change', () => {
    const files = [...input.files];
    result.hidden = true;
    if (!files.length) { clearPhoto(); return; }
    if (files.length > 6) {
      clearPhoto();
      status.textContent = 'Adicione no máximo 6 fotos por colecionável.';
      return;
    }
    if (files.some((file) => file.size > 10 * 1024 * 1024)) {
      clearPhoto();
      status.textContent = 'Cada imagem pode ter até 10 MB.';
      return;
    }
    if (files.some((file) => !acceptedTypes.includes(file.type))) {
      clearPhoto();
      status.textContent = 'Use apenas imagens JPG, PNG ou WebP.';
      return;
    }
    previewUrls.forEach((url) => URL.revokeObjectURL(url));
    previewUrls = files.map((file) => URL.createObjectURL(file));
    previews.querySelectorAll('.foto-miniatura').forEach((item) => item.remove());
    previewUrls.forEach((url, index) => {
      const figure = document.createElement('figure');
      figure.className = 'foto-quadro foto-miniatura';
      const image = document.createElement('img');
      image.src = url;
      image.alt = `Prévia da foto ${index + 1} do colecionável`;
      const badge = document.createElement('span');
      badge.textContent = index === 0 ? 'Referência da IA' : `Foto ${index + 1}`;
      figure.append(image, badge);
      previews.append(figure);
    });
    placeholder.hidden = true;
    remove.hidden = false;
    const aboveAnalysisLimit = files[0].size > 8 * 1024 * 1024;
    analyze.disabled = aboveAnalysisLimit;
    status.textContent = aboveAnalysisLimit
      ? `${files.length} fotos selecionadas · A primeira pode ser salva, mas precisa ter até 8 MB para ser analisada.`
      : `${files.length} ${files.length === 1 ? 'foto selecionada' : 'fotos selecionadas'} · A primeira será usada como referência pela IA.`;
  });
  remove.addEventListener('click', () => { clearPhoto(); input.focus(); });

  function useful(value) {
    return typeof value === 'string' && value.trim() && !/^não (informado|encontrado|é possível)/i.test(value.trim());
  }

  function fillIfEmpty(id, value, filled, label) {
    const field = document.getElementById(id);
    if (!field || !useful(String(value || '')) || field.value.trim()) return;
    field.value = String(value).trim();
    filled.push(label);
  }

  function firstNumber(value) {
    const found = String(value || '').replace(',', '.').match(/\d+(?:\.\d+)?/);
    return found ? found[0] : '';
  }

  function findCharacteristic(labelPart) {
    return [...document.querySelectorAll('[data-tipos]')].find((group) =>
      group.querySelector('label')?.textContent.toLocaleLowerCase('pt-BR').includes(labelPart)
    )?.querySelector('input,select');
  }

  function applySuggestions(data) {
    const filled = [];
    const hasExistingModel = Boolean(document.getElementById('id_modelo')?.value);

    if (!hasExistingModel) {
      const typeNames = {
        action_figure: 'action figure',
        estatua: 'estátua',
        busto: 'busto',
        funko_pop: 'funko pop',
        diorama: 'diorama',
        figura_de_vinil: 'vinil',
      };
      const wanted = typeNames[data.tipo_colecionavel];
      const type = document.getElementById('id_tipo');
      if (type && wanted && !type.value) {
        const option = [...type.options].find((item) => item.textContent.toLocaleLowerCase('pt-BR').includes(wanted));
        if (option) {
          type.value = option.value;
          type.dispatchEvent(new Event('change', { bubbles: true }));
          filled.push('categoria');
        }
      }
      fillIfEmpty('id_nome_modelo', data.identificacao, filled, 'nome do modelo');
      fillIfEmpty('id_nome_personagem', data.identificacao, filled, 'personagem');
      fillIfEmpty('id_fabricante', data.fabricante, filled, 'fabricante');
      fillIfEmpty('id_codigo_fabricante_sku', data.codigo_produto, filled, 'código do fabricante');

      const height = findCharacteristic('altura');
      const heightValue = firstNumber(data.altura_fabricante || data.altura_estimada);
      if (height && heightValue && !height.value) { height.value = heightValue; filled.push('altura'); }
      const weight = findCharacteristic('peso');
      const weightValue = firstNumber(data.peso_fabricante);
      if (weight && weightValue && !weight.value) { weight.value = weightValue; filled.push('peso'); }
    }

    const stateNames = {
      novo: 'Novo', excelente: 'Excelente', bom: 'Bom', regular: 'Regular',
      danificado: 'Danificado', indeterminado: 'Não informado',
    };
    fillIfEmpty('id_estado_peca', stateNames[data.estado_geral], filled, 'estado da peça');
    if (data.tem_caixa === 'sim') fillIfEmpty('id_condicao_caixa', 'Com caixa', filled, 'condição da caixa');
    if (data.tem_caixa === 'nao') fillIfEmpty('id_condicao_caixa', 'Sem caixa', filled, 'condição da caixa');

    const noteParts = [];
    if (Array.isArray(data.avarias_visiveis) && data.avarias_visiveis.length) noteParts.push(`Avarias visíveis: ${data.avarias_visiveis.join('; ')}.`);
    if (Array.isArray(data.pecas_faltando_visiveis) && data.pecas_faltando_visiveis.length) noteParts.push(`Possíveis peças faltando: ${data.pecas_faltando_visiveis.join('; ')}.`);
    if (useful(data.observacoes)) noteParts.push(data.observacoes.trim());
    fillIfEmpty('id_nota', noteParts.join('\n'), filled, 'notas');

    const confidence = Number.isFinite(Number(data.confianca)) ? ` Confiança da análise: ${data.confianca}%.` : '';
    const changed = filled.length ? `Sugestões aplicadas: ${filled.join(', ')}.` : 'Nenhum campo vazio pôde ser preenchido.';
    showResult(`Análise feita com a primeira foto como referência. ${changed}${confidence} Revise as sugestões e complete os dados antes de salvar.`);
  }

  analyze.addEventListener('click', async () => {
    const files = [...input.files];
    if (!files.length) return;
    const originalLabel = analyze.innerHTML;
    analyze.disabled = true;
    analyze.textContent = 'Analisando a primeira foto…';
    result.hidden = true;
    const payload = new FormData();
    payload.append('imagem', files[0]);
    payload.append('codigo_produto', document.getElementById('id_codigo_fabricante_sku')?.value || '');
    try {
      const response = await fetch(form.dataset.analisarUrl, {
        method: 'POST',
        headers: { 'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value },
        body: payload,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.erro || 'Não foi possível analisar a foto agora.');
      applySuggestions(data.analise);
    } catch (error) {
      showResult(error.message || 'Não foi possível analisar a foto agora.', 'error');
    } finally {
      analyze.innerHTML = originalLabel;
      analyze.disabled = false;
    }
  });
})();
