from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.utils import timezone

from catalogo.models import TipoColecionavel
from inventario.models import AvaliacaoEstante, ColecionavelUsuario, EstanteVirtual, ItemEstante, Diorama, ItemWishlist
from transacoes.models import AvaliacaoVenda
from .carrinho import CHAVE_SESSAO_CARRINHO, contexto_carrinho, ids_do_carrinho
from .models import Conversa, Mensagem

Usuario = get_user_model()

TIPOS_IMAGEM_ANALISE = {"image/jpeg", "image/png", "image/webp"}


def _estante_principal(usuario):
    """Usa a primeira estante já criada pelo usuário ou cria uma padrão."""
    estante = EstanteVirtual.objects.filter(usuario=usuario).order_by("ordem_exibicao", "id").first()
    if estante:
        return estante
    return EstanteVirtual.objects.create(usuario=usuario, nome_estante="Minha estante", ordem_exibicao=1)


def _estante_selecionada(usuario, estante_id=None):
    if estante_id:
        return get_object_or_404(EstanteVirtual, id=estante_id, usuario=usuario)
    return _estante_principal(usuario)


def index(request):
    """
    Home do site = catálogo completo: sidebar de filtros (categoria,
    franquia, personagem, fabricante, escala, estado) + destaques +
    resultados. Antes isso era dividido entre index e busca — agora é
    uma coisa só.
    """
    tipos = TipoColecionavel.objects.all()
    tipo_selecionado = request.GET.get("tipo", "")
    franquia = request.GET.get("franquia", "").strip()
    personagem = request.GET.get("personagem", "").strip()
    fabricante = request.GET.get("fabricante", "").strip()
    escala = request.GET.get("escala", "").strip()
    estado = request.GET.get("estado", "").strip()

    itens = (
        ColecionavelUsuario.objects
        .filter(status_privacidade=ColecionavelUsuario.PRIVACIDADE_PUBLICO)
        .select_related("modelo", "modelo__tipo", "usuario")
        .order_by("-data_inclusao")
    )

    if tipo_selecionado:
        itens = itens.filter(modelo__tipo__nome_tipo=tipo_selecionado)
    if franquia:
        itens = itens.filter(modelo__franquia__icontains=franquia)
    if personagem:
        itens = itens.filter(modelo__nome_personagem__icontains=personagem)
    if fabricante:
        itens = itens.filter(modelo__fabricante__icontains=fabricante)
    if escala:
        itens = itens.filter(
            modelo__valores_caracteristicas__caracteristica__nome_caracteristica="Escala",
            modelo__valores_caracteristicas__valor__icontains=escala,
        )
    if estado:
        itens = itens.filter(condicao_caixa__icontains=estado)

    itens = itens.distinct()

    # "Em destaque": itens à venda (ou venda/troca) com preço definido.
    # OBS: o banco não tem um campo de "preço original" pra calcular
    # desconto de verdade — então isso é "em destaque", não "promoção com
    # % off". Dá pra evoluir pra desconto real se um dia existir esse campo.
    destaques = (
        ColecionavelUsuario.objects
        .filter(
            status_privacidade=ColecionavelUsuario.PRIVACIDADE_PUBLICO,
            status_negociacao__in=[
                ColecionavelUsuario.NEGOCIACAO_VENDA,
                ColecionavelUsuario.NEGOCIACAO_VENDA_OU_TROCA,
            ],
        )
        .exclude(preco_anunciado__isnull=True)
        .select_related("modelo", "modelo__tipo")
        .order_by("-data_inclusao")[:6]
    )

    wishlist_ids = set()
    if request.user.is_authenticated:
        wishlist_ids = set(ItemWishlist.objects.filter(usuario=request.user).values_list("colecionavel_usuario_id", flat=True))
    contexto = {
        "tipos": tipos,
        "destaques": destaques,
        "filtros": {
            "tipo": tipo_selecionado,
            "franquia": franquia,
            "personagem": personagem,
            "fabricante": fabricante,
            "escala": escala,
            "estado": estado,
        },
        "itens": itens,
        "wishlist_ids": wishlist_ids,
        "mostrar_negociacao": True,
        "mensagem_vazio": "Nenhum item encontrado com esses filtros.",
    }
    return render(request, "core/index.html", contexto)


def produto(request, item_id):
    """Ficha da unidade anunciada e outras ofertas públicas do mesmo modelo."""
    visiveis = Q(status_privacidade=ColecionavelUsuario.PRIVACIDADE_PUBLICO)
    if request.user.is_authenticated:
        visiveis |= Q(usuario=request.user)

    produto = get_object_or_404(
        ColecionavelUsuario.objects
        .filter(visiveis)
        .select_related("modelo", "modelo__tipo", "usuario")
        .prefetch_related("imagens", "modelo__imagens", "modelo__valores_caracteristicas__caracteristica"),
        id=item_id,
    )

    ofertas_iguais = (
        ColecionavelUsuario.objects
        .filter(
            modelo=produto.modelo,
            status_privacidade=ColecionavelUsuario.PRIVACIDADE_PUBLICO,
            status_negociacao__in=[
                ColecionavelUsuario.NEGOCIACAO_VENDA,
                ColecionavelUsuario.NEGOCIACAO_TROCA,
                ColecionavelUsuario.NEGOCIACAO_VENDA_OU_TROCA,
            ],
        )
        .exclude(id=produto.id)
        .select_related("modelo", "usuario")
        .prefetch_related("imagens")
        .order_by("preco_anunciado", "-data_inclusao")
    )

    caracteristicas = []
    for registro in produto.modelo.valores_caracteristicas.all():
        valor = registro.valor
        if registro.caracteristica.tipo_dado == "boolean":
            valor = "Sim" if valor.lower() == "true" else "Não" if valor.lower() == "false" else valor
        caracteristicas.append((registro.caracteristica.nome_caracteristica, valor))

    reputacao_vendedor = AvaliacaoVenda.objects.filter(avaliado=produto.usuario).aggregate(
        media=Avg("nota"), total=Count("id")
    )

    return render(request, "core/produto.html", {
        "produto": produto,
        "caracteristicas": caracteristicas,
        "ofertas_iguais": ofertas_iguais,
        "eh_dono": request.user.is_authenticated and produto.usuario_id == request.user.id,
        "na_wishlist": request.user.is_authenticated and ItemWishlist.objects.filter(usuario=request.user, colecionavel_usuario=produto).exists(),
        "reputacao_vendedor_media": reputacao_vendedor["media"],
        "reputacao_vendedor_total": reputacao_vendedor["total"],
    })


def _resposta_carrinho(request):
    contexto = contexto_carrinho(request)
    return JsonResponse({
        "html": render_to_string("core/_carrinho_conteudo.html", contexto, request=request),
        "ids": contexto["carrinho_ids"],
        "quantidade": contexto["carrinho_quantidade"],
        "total": str(contexto["carrinho_total"]),
    })


@require_POST
def adicionar_ao_carrinho(request):
    item_id = request.POST.get("item_id", "")
    if not item_id.isdigit():
        return JsonResponse({"erro": "Item inválido."}, status=400)
    item = get_object_or_404(
        ColecionavelUsuario,
        pk=int(item_id),
        status_privacidade=ColecionavelUsuario.PRIVACIDADE_PUBLICO,
        status_negociacao__in=[
            ColecionavelUsuario.NEGOCIACAO_VENDA,
            ColecionavelUsuario.NEGOCIACAO_VENDA_OU_TROCA,
        ],
        preco_anunciado__isnull=False,
    )
    if request.user.is_authenticated and item.usuario_id == request.user.id:
        return JsonResponse({"erro": "Seu próprio anúncio não pode ser adicionado ao carrinho."}, status=400)
    ids = ids_do_carrinho(request)
    if item.id not in ids:
        ids.append(item.id)
        request.session[CHAVE_SESSAO_CARRINHO] = ids
        request.session.modified = True
    return _resposta_carrinho(request)


@require_POST
def remover_do_carrinho(request):
    item_id = request.POST.get("item_id", "")
    if not item_id.isdigit():
        return JsonResponse({"erro": "Item inválido."}, status=400)
    ids = [pk for pk in ids_do_carrinho(request) if pk != int(item_id)]
    request.session[CHAVE_SESSAO_CARRINHO] = ids
    request.session.modified = True
    return _resposta_carrinho(request)


@login_required
@require_POST
def analisar_foto_cadastro(request):
    fotos = request.FILES.getlist("imagem") or request.FILES.getlist("imagens")
    codigo = request.POST.get("codigo_produto", "").strip()
    if not fotos:
        return JsonResponse({"erro": "Escolha pelo menos uma foto para analisar."}, status=400)
    foto_referencia = fotos[0]
    if foto_referencia.content_type not in TIPOS_IMAGEM_ANALISE:
        return JsonResponse({"erro": "A primeira foto deve ser JPG, PNG ou WebP."}, status=400)
    if foto_referencia.size > 8 * 1024 * 1024:
        return JsonResponse({"erro": "A primeira foto pode ter no máximo 8 MB para análise."}, status=400)
    if len(codigo) > 80:
        return JsonResponse({"erro": "O código do produto pode ter no máximo 80 caracteres."}, status=400)
    try:
        from .analisador_gemini import analisar_imagens
        resultado = analisar_imagens([foto_referencia], codigo_produto=codigo)
        return JsonResponse({
            "analise": resultado,
            "referencia": "primeira_foto",
            "limite": "Sugestão baseada na primeira foto; revise os campos antes de salvar. A análise não comprova autenticidade.",
        })
    except ValueError as exc:
        return JsonResponse({"erro": str(exc)}, status=503)
    except Exception:
        return JsonResponse({"erro": "Não foi possível analisar a foto agora. Tente novamente."}, status=502)


@login_required
def prateleira(request):
    """A prateleira do PRÓPRIO usuário logado — vê tudo, público ou privado."""
    itens = list(
        ColecionavelUsuario.objects
        .filter(usuario=request.user)
        .select_related("modelo", "modelo__tipo")
        .prefetch_related("imagens", "modelo__imagens")
        .order_by("-data_inclusao")
    )

    estante = _estante_selecionada(request.user, request.GET.get("estante"))
    for ordem in range(1, 4):
        Diorama.objects.get_or_create(
            estante=estante,
            ordem=ordem,
            defaults={"titulo": f"Diorama da prateleira {ordem}"},
        )
    dioramas = list(estante.dioramas.all())
    dioramas_por_ordem = {diorama.ordem: diorama for diorama in dioramas}
    posicionamentos = list(
        ItemEstante.objects.filter(estante=estante)
        .select_related("colecionavel_usuario", "colecionavel_usuario__modelo")
        .prefetch_related("colecionavel_usuario__imagens", "colecionavel_usuario__modelo__imagens")
        .order_by("posicao_slot")
    )
    itens_por_posicao = {
        posicao.posicao_slot: posicao.colecionavel_usuario
        for posicao in posicionamentos
        if posicao.posicao_slot in range(1, 13)
    }
    slots = [{"numero": numero, "item": itens_por_posicao.get(numero)} for numero in range(1, 13)]
    prateleiras = []
    for numero in range(1, 4):
        inicio = (numero - 1) * 4
        slots_da_prateleira = slots[inicio:inicio + 4]
        pecas = [slot["item"] for slot in slots_da_prateleira if slot["item"]]
        prateleiras.append({
            "numero": numero,
            "slots": slots_da_prateleira,
            "diorama": dioramas_por_ordem[numero],
            "pecas": pecas,
            "nomes_pecas": [peca.modelo.nome_personagem for peca in pecas],
        })
    ids_posicionados = {item.id for item in itens_por_posicao.values()}
    ids_na_estante = {posicao.colecionavel_usuario_id for posicao in posicionamentos}
    itens_sem_posicao = [item for item in itens if item.id in ids_na_estante and item.id not in ids_posicionados]
    colecionaveis_disponiveis = [item for item in itens if item.id not in ids_na_estante]

    # "valor estimado" = soma do que o usuário pagou em cada item.
    # Poderia usar preco_anunciado quando existir, mas nem todo item está
    # anunciado — preco_pago é o único valor que TODO item sempre tem.
    valor_total = sum((item.preco_pago for item in itens), Decimal("0"))

    contexto = {
        "itens": itens,
        "slots": slots,
        "prateleiras": prateleiras,
        "diorama_destaque": prateleiras[min(max(estante.diorama_destaque, 1), 3) - 1],
        "itens_sem_posicao": itens_sem_posicao,
        "colecionaveis_disponiveis": colecionaveis_disponiveis,
        "estante": estante,
        "estantes": EstanteVirtual.objects.filter(usuario=request.user).order_by("ordem_exibicao", "id"),
        "valor_total": valor_total,
        "mostrar_negociacao": True,
        "mostrar_preco_pago": True,
        "mensagem_vazio": "Sua prateleira está vazia. Que tal cadastrar seu primeiro item?",
    }
    return render(request, "core/prateleira.html", contexto)


@login_required
def meus_colecionaveis(request):
    """Catálogo particular do usuário, conectado à sua estante principal."""
    estante = _estante_principal(request.user)
    itens = list(
        ColecionavelUsuario.objects.filter(usuario=request.user)
        .select_related("modelo", "modelo__tipo")
        .order_by("modelo__franquia", "modelo__nome_personagem")
    )
    posicionamentos = ItemEstante.objects.filter(estante=estante).only(
        "colecionavel_usuario_id", "posicao_slot"
    )
    posicoes = {posicao.colecionavel_usuario_id: posicao.posicao_slot for posicao in posicionamentos}
    colecionaveis = [
        {"item": item, "posicao": posicoes.get(item.id), "na_estante": item.id in posicoes}
        for item in itens
    ]
    return render(request, "core/meus_colecionaveis.html", {"colecionaveis": colecionaveis})


@login_required
@require_POST
def mover_item_estante(request):
    """Move um colecionável para um dos doze espaços da estante principal."""
    try:
        item_id = int(request.POST.get("item_id", ""))
        destino = int(request.POST.get("destino", ""))
    except (TypeError, ValueError):
        return JsonResponse({"erro": "Dados de posição inválidos."}, status=400)
    if destino not in range(1, 13):
        return JsonResponse({"erro": "Escolha uma posição entre 1 e 12."}, status=400)

    with transaction.atomic():
        estante = _estante_selecionada(request.user, request.POST.get("estante_id"))
        colecionavel = get_object_or_404(ColecionavelUsuario, id=item_id, usuario=request.user)
        item_estante, _ = ItemEstante.objects.select_for_update().get_or_create(
            colecionavel_usuario=colecionavel, defaults={"estante": estante}
        )
        if item_estante.estante_id != estante.id:
            item_estante.estante = estante
        posicao_origem = item_estante.posicao_slot
        ocupante = (ItemEstante.objects.select_for_update().filter(estante=estante, posicao_slot=destino)
                   .exclude(pk=item_estante.pk).first())
        if ocupante:
            ocupante.posicao_slot = posicao_origem
            ocupante.save(update_fields=["posicao_slot"])
        item_estante.posicao_slot = destino
        item_estante.save(update_fields=["estante", "posicao_slot"])
    return JsonResponse({"ok": True})


@login_required
@require_POST
def adicionar_item_estante(request):
    """Inclui um colecionável cadastrado na estante, ainda sem posição."""
    try:
        item_id = int(request.POST.get("item_id", ""))
    except (TypeError, ValueError):
        return JsonResponse({"erro": "Colecionável inválido."}, status=400)

    with transaction.atomic():
        estante = _estante_selecionada(request.user, request.POST.get("estante_id"))
        colecionavel = get_object_or_404(ColecionavelUsuario, id=item_id, usuario=request.user)
        item_estante, criado = ItemEstante.objects.select_for_update().get_or_create(
            colecionavel_usuario=colecionavel,
            defaults={"estante": estante, "posicao_slot": None},
        )
        if not criado and item_estante.estante_id != estante.id:
            item_estante.estante = estante
            item_estante.posicao_slot = None
            item_estante.save(update_fields=["estante", "posicao_slot"])

    return JsonResponse({"ok": True})


@login_required
@require_POST
def remover_item_estante(request):
    """Remove somente o vínculo com a estante; o cadastro do item permanece."""
    try:
        item_id = int(request.POST.get("item_id", ""))
    except (TypeError, ValueError):
        return JsonResponse({"erro": "Colecionável inválido."}, status=400)

    estante = _estante_selecionada(request.user, request.POST.get("estante_id"))
    ItemEstante.objects.filter(
        estante=estante,
        colecionavel_usuario_id=item_id,
        colecionavel_usuario__usuario=request.user,
    ).delete()
    return JsonResponse({"ok": True})


@login_required
@require_POST
def salvar_dioramas(request):
    """Cria ou edita o cenário da fileira indicada da estante."""
    try:
        ordem = int(request.POST.get("ordem", "0"))
    except ValueError:
        ordem = 0
    if ordem not in range(1, 4):
        return JsonResponse({"erro": "Prateleira inválida."}, status=400)
    estante = _estante_selecionada(request.user, request.POST.get("estante_id"))
    diorama, _ = Diorama.objects.get_or_create(estante=estante, ordem=ordem)
    diorama.titulo = request.POST.get("titulo", "").strip()[:100] or f"Diorama da prateleira {ordem}"
    diorama.descricao = request.POST.get("descricao", "").strip()[:180]
    diorama.configurado = True
    diorama.save(update_fields=["titulo", "descricao", "configurado"])
    return JsonResponse({"ok": True, "ordem": ordem})


@login_required
@require_POST
def selecionar_diorama_destaque(request):
    """Define qual das três prateleiras terá seu diorama exibido no topo."""
    try:
        ordem = int(request.POST.get("ordem", "0"))
    except ValueError:
        ordem = 0
    if ordem not in range(1, 4):
        return JsonResponse({"erro": "Prateleira inválida."}, status=400)
    estante = _estante_selecionada(request.user, request.POST.get("estante_id"))
    estante.diorama_destaque = ordem
    estante.save(update_fields=["diorama_destaque"])
    return JsonResponse({"ok": True, "ordem": ordem})


@login_required
@require_POST
def criar_estante(request):
    nome = request.POST.get("nome", "").strip()
    if not nome:
        return JsonResponse({"erro": "Informe um nome para a estante."}, status=400)
    ultima_ordem = EstanteVirtual.objects.filter(usuario=request.user).order_by("-ordem_exibicao").values_list("ordem_exibicao", flat=True).first() or 0
    estante = EstanteVirtual.objects.create(usuario=request.user, nome_estante=nome[:255], ordem_exibicao=ultima_ordem + 1)
    return JsonResponse({"ok": True, "url": f"/prateleira/?estante={estante.id}"})


@login_required
@require_POST
def alterar_privacidade_estante(request):
    estante = _estante_selecionada(request.user, request.POST.get("estante_id"))
    publica = request.POST.get("publica") == "true"
    estante.status_privacidade = "publico" if publica else "privado"
    estante.save(update_fields=["status_privacidade"])
    return JsonResponse({"ok": True, "publica": publica})


def prateleira_publica(request, username):
    """Versão compartilhável de uma estante que o dono tornou pública."""
    dono = get_object_or_404(Usuario, username=username)
    estantes_publicas = EstanteVirtual.objects.filter(usuario=dono, status_privacidade="publico")
    estante_id = request.GET.get("estante")
    estante = get_object_or_404(estantes_publicas, id=estante_id) if estante_id else get_object_or_404(estantes_publicas.order_by("ordem_exibicao", "id"))
    posicionamentos = list(ItemEstante.objects.filter(
        estante=estante,
        colecionavel_usuario__status_privacidade=ColecionavelUsuario.PRIVACIDADE_PUBLICO,
    ).select_related("colecionavel_usuario__modelo", "colecionavel_usuario__modelo__tipo").prefetch_related(
        "colecionavel_usuario__imagens", "colecionavel_usuario__modelo__imagens"
    ).order_by("posicao_slot", "id"))
    dioramas_por_ordem = {diorama.ordem: diorama for diorama in estante.dioramas.all()}
    itens_por_posicao = {
        posicao.posicao_slot: posicao.colecionavel_usuario
        for posicao in posicionamentos if posicao.posicao_slot in range(1, 13)
    }
    slots = [{"numero": numero, "item": itens_por_posicao.get(numero)} for numero in range(1, 13)]
    prateleiras = []
    for numero in range(1, 4):
        slots_da_prateleira = slots[(numero - 1) * 4:numero * 4]
        pecas = [slot["item"] for slot in slots_da_prateleira if slot["item"]]
        prateleiras.append({
            "numero": numero,
            "slots": slots_da_prateleira,
            "diorama": dioramas_por_ordem.get(numero),
            "pecas": pecas,
        })
    indice_destaque = min(max(estante.diorama_destaque, 1), 3) - 1

    reputacao = estante.avaliacoes.aggregate(media=Avg("nota"), total=Count("id"))
    minha_avaliacao = None
    if request.user.is_authenticated and request.user.id != dono.id:
        minha_avaliacao = AvaliacaoEstante.objects.filter(estante=estante, avaliador=request.user).first()

    contexto = {
        "dono": dono,
        "estante": estante,
        "prateleiras": prateleiras,
        "diorama_destaque": prateleiras[indice_destaque],
        "reputacao_media": reputacao["media"],
        "reputacao_total": reputacao["total"],
        "minha_avaliacao": minha_avaliacao,
        "pode_avaliar": request.user.is_authenticated and request.user.id != dono.id,
    }
    return render(request, "core/prateleira_publica.html", contexto)


def buscar_colecionadores(request):
    termo = request.GET.get("q", "").strip()
    colecionadores = Usuario.objects.filter(estantes__status_privacidade="publico").distinct()
    if termo:
        colecionadores = colecionadores.filter(
            Q(username__icontains=termo)
            | Q(first_name__icontains=termo)
            | Q(last_name__icontains=termo)
        )
    colecionadores = colecionadores.order_by("username")[:40]
    return render(request, "core/buscar_colecionadores.html", {
        "colecionadores": colecionadores,
        "termo": termo,
    })


def perfil_colecionador(request, username):
    colecionador = get_object_or_404(Usuario, username=username)
    estantes = EstanteVirtual.objects.filter(
        usuario=colecionador,
        status_privacidade="publico",
    ).annotate(
        reputacao_media=Avg("avaliacoes__nota"),
        reputacao_total=Count("avaliacoes"),
    ).order_by("ordem_exibicao", "id")
    reputacao_vendedor = AvaliacaoVenda.objects.filter(avaliado=colecionador).aggregate(
        media=Avg("nota"), total=Count("id"),
    )
    return render(request, "core/perfil_colecionador.html", {
        "colecionador": colecionador,
        "estantes": estantes,
        "reputacao_vendedor_media": reputacao_vendedor["media"],
        "reputacao_vendedor_total": reputacao_vendedor["total"],
    })


@login_required
@require_POST
def avaliar_estante(request, estante_id):
    estante = get_object_or_404(EstanteVirtual, id=estante_id, status_privacidade="publico")
    if estante.usuario_id == request.user.id:
        messages.error(request, "Você não pode avaliar a própria estante.")
        return redirect("core:prateleira_publica", username=estante.usuario.username)
    try:
        nota = int(request.POST.get("nota", ""))
    except (TypeError, ValueError):
        nota = 0
    comentario = request.POST.get("comentario", "").strip()
    if nota not in range(1, 6):
        messages.error(request, "Escolha uma nota entre 1 e 5 estrelas.")
    elif len(comentario) > 500:
        messages.error(request, "O comentário pode ter no máximo 500 caracteres.")
    elif AvaliacaoEstante.objects.filter(estante=estante, avaliador=request.user).exists():
        messages.info(request, "Você já avaliou esta estante.")
    else:
        avaliacao = AvaliacaoEstante(estante=estante, avaliador=request.user, nota=nota, comentario=comentario)
        try:
            avaliacao.full_clean()
            avaliacao.save()
        except (IntegrityError, ValidationError):
            messages.info(request, "Você já avaliou esta estante.")
        else:
            messages.success(request, "Avaliação enviada. Ela já conta para o ranking!")
    return redirect("core:prateleira_publica", username=estante.usuario.username)


def ranking_estantes(request):
    estantes = (
        EstanteVirtual.objects.filter(status_privacidade="publico")
        .annotate(reputacao_media=Avg("avaliacoes__nota"), reputacao_total=Count("avaliacoes"))
        .filter(reputacao_total__gt=0)
        .select_related("usuario")
        .order_by("-reputacao_media", "-reputacao_total", "nome_estante")
    )
    return render(request, "core/ranking_estantes.html", {"estantes": estantes})


@login_required
def wishlist(request):
    registros = ItemWishlist.objects.filter(usuario=request.user).select_related(
        "colecionavel_usuario__modelo",
        "colecionavel_usuario__modelo__tipo",
        "colecionavel_usuario__usuario",
    ).prefetch_related("colecionavel_usuario__imagens")
    itens = [registro.colecionavel_usuario for registro in registros]
    return render(request, "core/wishlist.html", {
        "itens": itens,
        "wishlist_ids": {item.id for item in itens},
        "mostrar_negociacao": True,
        "mensagem_vazio": "Sua Wishlist ainda está vazia.",
    })


@login_required
@require_POST
def alternar_wishlist(request):
    item_id = request.POST.get("item_id", "")
    if not item_id.isdigit():
        return JsonResponse({"erro": "Item inválido."}, status=400)
    item = get_object_or_404(
        ColecionavelUsuario,
        id=int(item_id),
        status_privacidade=ColecionavelUsuario.PRIVACIDADE_PUBLICO,
    )
    if item.usuario_id == request.user.id:
        return JsonResponse({"erro": "Você não precisa salvar um item que já pertence a você."}, status=400)
    registro, adicionado = ItemWishlist.objects.get_or_create(usuario=request.user, colecionavel_usuario=item)
    if not adicionado:
        registro.delete()
    quantidade = ItemWishlist.objects.filter(usuario=request.user).count()
    return JsonResponse({"adicionado": adicionado, "quantidade": quantidade, "item_id": item.id})


def _conversas_do_usuario(usuario):
    return Conversa.objects.filter(Q(iniciado_por=usuario) | Q(destinatario=usuario)).select_related(
        "iniciado_por", "destinatario", "colecionavel__modelo"
    ).prefetch_related("mensagens")


@login_required
def chat(request, conversa_id=None):
    conversas = list(_conversas_do_usuario(request.user))
    ativa = None
    if conversa_id is not None:
        ativa = get_object_or_404(_conversas_do_usuario(request.user), id=conversa_id)
    elif conversas:
        ativa = conversas[0]
    itens = []
    for conversa in conversas:
        outro = conversa.destinatario if conversa.iniciado_por_id == request.user.id else conversa.iniciado_por
        ultima = conversa.mensagens.last()
        itens.append({"conversa": conversa, "outro": outro, "ultima": ultima})
    mensagens = []
    outro_ativo = None
    if ativa:
        outro_ativo = ativa.destinatario if ativa.iniciado_por_id == request.user.id else ativa.iniciado_por
        Mensagem.objects.filter(conversa=ativa, lida_em__isnull=True).exclude(autor=request.user).update(lida_em=timezone.now())
        mensagens = list(ativa.mensagens.select_related("autor"))
    return render(request, "core/chat.html", {"conversas": itens, "conversa_ativa": ativa, "outro_ativo": outro_ativo, "mensagens": mensagens})


@login_required
@require_POST
def iniciar_chat(request, item_id):
    item = get_object_or_404(ColecionavelUsuario.objects.select_related("usuario"), id=item_id, status_privacidade=ColecionavelUsuario.PRIVACIDADE_PUBLICO)
    if item.usuario_id == request.user.id:
        return redirect("core:produto", item_id=item.id)
    conversa, _ = Conversa.objects.get_or_create(iniciado_por=request.user, destinatario=item.usuario, colecionavel=item)
    return redirect("core:chat_conversa", conversa_id=conversa.id)


@login_required
@require_POST
def enviar_mensagem(request, conversa_id):
    conversa = get_object_or_404(_conversas_do_usuario(request.user), id=conversa_id)
    texto = request.POST.get("texto", "").strip()
    if not texto:
        return JsonResponse({"erro": "Digite uma mensagem."}, status=400)
    if len(texto) > 2000:
        return JsonResponse({"erro": "A mensagem pode ter no máximo 2.000 caracteres."}, status=400)
    mensagem = Mensagem.objects.create(conversa=conversa, autor=request.user, texto=texto)
    Conversa.objects.filter(id=conversa.id).update(atualizada_em=timezone.now())
    return JsonResponse({"id": mensagem.id, "texto": mensagem.texto, "hora": mensagem.enviada_em.astimezone().strftime("%H:%M"), "autor": request.user.username})


@login_required
def cadastrar_colecionavel(request):
    from .forms import CadastroColecionavelForm
    form = CadastroColecionavelForm(request.POST if request.method == 'POST' else None, request.FILES if request.method == 'POST' else None, initial={'status_privacidade': 'privado', 'modelo': request.GET.get('modelo')})
    if request.method == 'POST' and form.is_valid():
        form.save_for_user(request.user)
        return redirect('core:meus_colecionaveis')
    return render(request, 'core/cadastrar_colecionavel.html', {'form': form})


@login_required
def editar_colecionavel(request, item_id):
    from .forms import EditarColecionavelForm

    item = get_object_or_404(
        ColecionavelUsuario.objects.select_related('modelo', 'modelo__tipo'),
        id=item_id,
        usuario=request.user,
    )
    form = EditarColecionavelForm(request.POST if request.method == 'POST' else None, instance=item)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('core:meus_colecionaveis')
    return render(request, 'core/editar_colecionavel.html', {'form': form, 'item': item})


def catalogo_figuras(request):
    from catalogo.models import ModeloColecionavel
    modelos = ModeloColecionavel.objects.filter(tipo__nome_tipo='Action Figure').select_related('tipo').prefetch_related('imagens', 'unidades__imagens', 'valores_caracteristicas__caracteristica').order_by('franquia', 'pk')
    franquias = list(modelos.order_by('franquia').values_list('franquia', flat=True).distinct())
    busca = request.GET.get('q', '').strip()
    franquia = request.GET.get('franquia', '')
    figuras = []
    for modelo in modelos:
        dados = {x.caracteristica.nome_caracteristica: x.valor for x in modelo.valores_caracteristicas.all()}
        imagem = modelo.imagens.first()
        if not imagem:
            for unidade in modelo.unidades.all():
                imagem = unidade.imagens.first()
                if imagem:
                    break
        figuras.append({'modelo': modelo, 'imagem': imagem, 'nome': dados.get('Nome', modelo.nome_modelo or modelo.nome_personagem), 'serie': dados.get('Série', ''), 'ano': dados.get('Ano de lançamento', ''), 'altura': dados.get('Altura (cm)', '').replace('.', ','), 'material': dados.get('Material', ''), 'ficha': [(k, 'Sim' if val == 'true' else 'Não' if val == 'false' else val.replace('.', ',') if k == 'Altura (cm)' else val) for k, val in dados.items() if k != 'Origem dos dados']})
    franquias = sorted({f['modelo'].franquia for f in figuras})
    total = len(figuras)
    figuras = [f for f in figuras if (not franquia or f['modelo'].franquia == franquia) and (not busca or busca.casefold() in (f['nome'] + ' ' + f['modelo'].nome_personagem).casefold())]
    return render(request, 'core/catalogo_figuras.html', {'figuras': figuras, 'total': total, 'busca': busca, 'franquia': franquia, 'franquias': franquias})
