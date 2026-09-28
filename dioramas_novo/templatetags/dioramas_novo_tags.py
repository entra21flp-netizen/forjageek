from django import template

from dioramas_novo.models import DioramaGeradoNovo
from inventario.models import ItemEstante

register = template.Library()


@register.inclusion_tag("dioramas_novo/_secao_prateleira.html", takes_context=True)
def secao_dioramas_novos(context, usuario, estante=None):
    if not usuario.is_authenticated:
        return {"dioramas_novos": []}
    dioramas = list(DioramaGeradoNovo.objects.filter(usuario=usuario).select_related("colecionavel__modelo", "preset"))
    posicoes = {
        item.diorama_novo_id: item
        for item in ItemEstante.objects.filter(diorama_novo_id__in=[d.pk for d in dioramas]).select_related("estante")
    }
    for diorama in dioramas:
        diorama.posicionamento_atual = posicoes.get(diorama.pk)
        diorama.linha_atual = (
            ((diorama.posicionamento_atual.posicao_slot - 1) // 4) + 1
            if diorama.posicionamento_atual
            else None
        )
    return {"dioramas_novos": dioramas, "estante": estante, "csrf_token": context.get("csrf_token")}
