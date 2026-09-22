from decimal import Decimal

from django.db.models import Case, IntegerField, When

from inventario.models import ColecionavelUsuario


CHAVE_SESSAO_CARRINHO = "carrinho_itens"


def ids_do_carrinho(request):
    ids = request.session.get(CHAVE_SESSAO_CARRINHO, [])
    return [int(item_id) for item_id in ids if str(item_id).isdigit()]


def contexto_carrinho(request):
    ids = ids_do_carrinho(request)
    if not ids:
        return {"carrinho_itens": [], "carrinho_ids": [], "carrinho_total": Decimal("0"), "carrinho_quantidade": 0}

    ordem = Case(
        *[When(pk=item_id, then=posicao) for posicao, item_id in enumerate(ids)],
        output_field=IntegerField(),
    )
    itens = list(
        ColecionavelUsuario.objects.filter(
            pk__in=ids,
            status_privacidade=ColecionavelUsuario.PRIVACIDADE_PUBLICO,
            status_negociacao__in=[
                ColecionavelUsuario.NEGOCIACAO_VENDA,
                ColecionavelUsuario.NEGOCIACAO_VENDA_OU_TROCA,
            ],
            preco_anunciado__isnull=False,
        )
        .select_related("modelo", "usuario")
        .prefetch_related("imagens", "modelo__imagens")
        .order_by(ordem)
    )
    ids_validos = [item.id for item in itens]
    if ids_validos != ids:
        request.session[CHAVE_SESSAO_CARRINHO] = ids_validos
        request.session.modified = True

    return {
        "carrinho_itens": itens,
        "carrinho_ids": ids_validos,
        "carrinho_total": sum((item.preco_anunciado for item in itens), Decimal("0")),
        "carrinho_quantidade": len(itens),
    }
