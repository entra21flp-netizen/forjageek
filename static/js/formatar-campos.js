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

  const formatarCentavos = (valor) => {
    const digitos = valor.replace(/\D/g, '').replace(/^0+(?=\d)/, '');
    if (!digitos) return '';
    const preenchido = digitos.padStart(3, '0');
    return `${preenchido.slice(0, -2)},${preenchido.slice(-2)}`;
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
    // Valores vindos do servidor já representam reais, não centavos digitados.
    const inicial = campo.value.trim();
    if (inicial) {
      const normalizado = inicial.includes(',')
        ? inicial.replace(/\./g, '').replace(',', '.')
        : inicial;
      if (/^\d+(?:\.\d{1,2})?$/.test(normalizado)) {
        const [reais, centavos = ''] = normalizado.split('.');
        campo.value = formatarCentavos(reais + centavos.padEnd(2, '0'));
      }
    }
    campo.inputMode = 'numeric';
    campo.addEventListener('input', () => {
      campo.value = formatarCentavos(campo.value);
    });
  });
})();
