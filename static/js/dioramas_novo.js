document.addEventListener('DOMContentLoaded',()=>{
  const form=document.querySelector('#dn-generation-form');
  if(!form)return;
  const type=document.querySelector('#id_tipo');
  const activate=(mode)=>{
    type.value=mode;
    document.querySelectorAll('.dn-mode').forEach(el=>el.classList.toggle('active',el.dataset.mode===mode));
    document.querySelectorAll('.dn-panel').forEach(el=>el.classList.toggle('active',el.dataset.panel===mode));
  };
  document.querySelectorAll('.dn-mode').forEach(el=>el.addEventListener('click',()=>activate(el.dataset.mode)));
  document.querySelectorAll('.dn-preset').forEach(card=>card.addEventListener('click',()=>{
    document.querySelectorAll('.dn-preset').forEach(el=>el.classList.remove('selected'));
    card.classList.add('selected');
  }));
  const ideas=form.querySelector('.dn-ideas');
  if(ideas)ideas.addEventListener('click',event=>{
    const button=event.target.closest('.dn-idea');
    if(!button||!ideas.contains(button))return;
    const description=form.elements.namedItem('descricao');
    if(!description)return;
    const idea=button.dataset.idea;
    const current=description.value.trim();
    const punctuation=current.match(/[.!?]$/u)?.[0]||'';
    const base=punctuation ? current.slice(0,-1).trimEnd() : current;
    const separator=base ? (/[,:;]$/u.test(base) ? ' ' : ', ') : '';
    const addition=base ? idea : idea.charAt(0).toLocaleUpperCase('pt-BR')+idea.slice(1);
    const updated=base+separator+addition+punctuation;
    if(description.maxLength>0&&updated.length>description.maxLength)return;
    description.value=updated;
    description.dispatchEvent(new Event('input',{bubbles:true}));
    description.focus();
    description.setSelectionRange(updated.length,updated.length);
  });
  activate(type.value||'predefinido');
  form.addEventListener('submit',()=>{
    const mode=type.value;
    const button=document.querySelector(mode==='predefinido'?'#dn-save-preset':'#dn-generate');
    if(button){button.disabled=true;button.classList.add('is-loading');}
  });
});
