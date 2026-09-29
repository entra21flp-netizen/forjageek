document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('form[data-confirmar-campo-com-enter]').forEach((formulario) => {
    formulario.addEventListener('submit', (evento) => {
      if (!evento.submitter) evento.preventDefault();
    });

    formulario.addEventListener('keydown', (evento) => {
      if (evento.key !== 'Enter' || evento.isComposing) return;

      const campo = evento.target;
      if (!(campo instanceof HTMLInputElement)) return;

      const tiposQueNaoConfirmam = new Set([
        'button',
        'checkbox',
        'file',
        'hidden',
        'image',
        'radio',
        'reset',
        'submit',
      ]);
      if (tiposQueNaoConfirmam.has(campo.type)) return;

      evento.preventDefault();
      campo.blur();
    });
  });
});
