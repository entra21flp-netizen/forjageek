(() => {
  const form = document.getElementById('chat-form');
  const messages = document.getElementById('chat-mensagens');
  if (!form || !messages) return;
  messages.scrollTop = messages.scrollHeight;
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const field = form.querySelector('[name="texto"]');
    const button = form.querySelector('button');
    if (!field.value.trim()) return;
    button.disabled = true;
    try {
      const response = await fetch(form.dataset.url, {method:'POST', headers:{'X-CSRFToken':form.querySelector('[name="csrfmiddlewaretoken"]').value,'X-Requested-With':'XMLHttpRequest'}, body:new FormData(form)});
      const data = await response.json();
      if (!response.ok) throw new Error(data.erro || 'Não foi possível enviar a mensagem.');
      document.getElementById('chat-inicio')?.remove();
      const article = document.createElement('article'); article.className='chat-balao minha';
      const p = document.createElement('p'); p.textContent=data.texto;
      const small = document.createElement('small'); small.textContent=data.hora;
      article.append(p,small); messages.append(article); field.value=''; messages.scrollTop=messages.scrollHeight; field.focus();
    } catch(error) { window.alert(error.message); } finally { button.disabled=false; }
  });
})();
