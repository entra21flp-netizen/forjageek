from .carrinho import contexto_carrinho


def carrinho(request):
    return contexto_carrinho(request)
