(() => {
  const input = document.getElementById('id_foto');
  const preview = document.getElementById('foto-edicao-preview');
  const nome = document.getElementById('nome-arquivo-edicao');
  if (!input || !preview || !nome) return;
  let urlTemporaria = null;

  input.addEventListener('change', () => {
    const arquivos = [...input.files];
    if (urlTemporaria) URL.revokeObjectURL(urlTemporaria);
    if (!arquivos.length) {
      nome.textContent = 'Nenhuma nova imagem escolhida';
      return;
    }
    nome.textContent = arquivos.length === 1 ? arquivos[0].name : `${arquivos.length} novas imagens escolhidas`;
    urlTemporaria = URL.createObjectURL(arquivos[0]);
    preview.replaceChildren();
    const imagem = document.createElement('img');
    imagem.src = urlTemporaria;
    imagem.alt = 'Prévia da nova foto principal';
    preview.append(imagem);
  });
})();
