(() => {
  const somenteDigitos = (valor, limite) => valor.replace(/\D/g, '').slice(0, limite);

  const formatarCpf = (valor) => {
    const digitos = somenteDigitos(valor, 11);
    return digitos
      .replace(/^(\d{3})(\d)/, '$1.$2')
      .replace(/^(\d{3})\.(\d{3})(\d)/, '$1.$2.$3')
      .replace(/\.(\d{3})(\d)/, '.$1-$2');
  };

  const formatarTelefone = (valor) => {
    let digitos = somenteDigitos(valor, 13);
    if (digitos.length > 11 && digitos.startsWith('55')) digitos = digitos.slice(2);
    digitos = digitos.slice(0, 11);
    if (digitos.length <= 2) return digitos ? `(${digitos}` : '';
    const ddd = digitos.slice(0, 2);
    const numero = digitos.slice(2);
    if (numero.length <= 4) return `(${ddd}) ${numero}`;
    const corte = numero.length > 8 ? 5 : 4;
    return `(${ddd}) ${numero.slice(0, corte)}-${numero.slice(corte)}`;
  };

  const numeroMonetario = (valor) => {
    const texto = String(valor || '').trim().replace(/\s/g, '').replace(/^R\$/, '');
    if (!texto) return null;
    let normalizado = texto;
    if (texto.includes(',')) normalizado = texto.replace(/\./g, '').replace(',', '.');
    normalizado = normalizado.replace(/[^\d.-]/g, '');
    const numero = Number(normalizado);
    return Number.isFinite(numero) ? numero : null;
  };

  document.querySelectorAll('[data-mascara="cpf"]').forEach((campo) => {
    campo.value = formatarCpf(campo.value);
    campo.addEventListener('input', () => { campo.value = formatarCpf(campo.value); });
  });

  document.querySelectorAll('[data-mascara="telefone"]').forEach((campo) => {
    campo.value = formatarTelefone(campo.value);
    campo.addEventListener('input', () => { campo.value = formatarTelefone(campo.value); });
  });

  document.querySelectorAll('[data-mascara="numeros"]').forEach((campo) => {
    campo.addEventListener('input', () => { campo.value = campo.value.replace(/\D/g, ''); });
  });

  document.querySelectorAll('[data-mascara="letras"]').forEach((campo) => {
    campo.addEventListener('input', () => {
      campo.value = campo.value.replace(/[0-9]/g, '');
    });
  });

  document.querySelectorAll('.campo-numero-decimal').forEach((campo) => {
    campo.addEventListener('input', () => {
      let valor = campo.value.replace(/[^\d,.]/g, '').replace(/\./g, ',');
      const partes = valor.split(',');
      if (partes.length > 1) valor = `${partes.shift()},${partes.join('').slice(0, 4)}`;
      campo.value = valor;
    });
  });

  document.querySelectorAll('.campo-moeda').forEach((campo) => {
    const formatar = () => {
      const numero = numeroMonetario(campo.value);
      campo.value = numero === null ? '' : numero.toFixed(2).replace('.', ',');
    };
    campo.addEventListener('input', () => {
      campo.value = campo.value.replace(/[^\d,.]/g, '').replace(/(,.*),/g, '$1');
    });
    campo.addEventListener('blur', formatar);
    formatar();
  });
})();
