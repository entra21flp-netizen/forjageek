import logging
from decimal import Decimal, ROUND_HALF_UP

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.carrinho import CHAVE_SESSAO_CARRINHO, contexto_carrinho
from inventario.models import ColecionavelUsuario
from .models import AvaliacaoVenda, TransacaoVenda

logger = logging.getLogger(__name__)
TAXA_PLATAFORMA = Decimal("0.10")


def _venda_avaliavel(venda):
    return venda.status_transacao in {
        TransacaoVenda.STATUS_PAGO,
        TransacaoVenda.STATUS_CONCLUIDO,
    }


def _centavos(valor):
    return int((Decimal(valor) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _confirmar_pagamento(sessao):
    """Confirma uma sessão já validada pelo Stripe de forma idempotente."""
    if sessao.get("payment_status") != "paid":
        return False
    with transaction.atomic():
        vendas = TransacaoVenda.objects.select_for_update().filter(stripe_checkout_session_id=sessao["id"])
        for venda in vendas:
            if venda.status_transacao != TransacaoVenda.STATUS_PENDENTE:
                continue
            item = ColecionavelUsuario.objects.select_for_update().get(pk=venda.colecionavel_usuario_id)
            venda.status_transacao = TransacaoVenda.STATUS_PAGO
            venda.stripe_payment_intent_id = sessao.get("payment_intent") or ""
            venda.concluido_em = timezone.now()
            venda.save(update_fields=["status_transacao", "stripe_payment_intent_id", "concluido_em"])
            item.status_negociacao = ColecionavelUsuario.NEGOCIACAO_EXIBICAO
            item.preco_anunciado = None
            item.status_privacidade = ColecionavelUsuario.PRIVACIDADE_PRIVADO
            item.save(update_fields=["status_negociacao", "preco_anunciado", "status_privacidade"])
    return True


@login_required
@require_POST
def iniciar_checkout_carrinho(request):
    if not settings.STRIPE_SECRET_KEY:
        messages.error(request, "O pagamento ainda não foi configurado pelo administrador.")
        return redirect("core:index")
    itens = [item for item in contexto_carrinho(request)["carrinho_itens"] if item.usuario_id != request.user.id]
    if not itens:
        messages.info(request, "Seu carrinho não possui itens disponíveis para compra.")
        return redirect("core:index")
    ids = [item.id for item in itens]
    if TransacaoVenda.objects.filter(colecionavel_usuario_id__in=ids, status_transacao__in=[
        TransacaoVenda.STATUS_PENDENTE, TransacaoVenda.STATUS_PAGO, TransacaoVenda.STATUS_CONCLUIDO,
    ]).exists():
        messages.error(request, "Um dos itens já está reservado ou foi vendido. Atualize o carrinho e tente novamente.")
        return redirect("core:index")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        with transaction.atomic():
            itens = list(ColecionavelUsuario.objects.select_for_update().filter(pk__in=ids).select_related("modelo", "usuario"))
            if len(itens) != len(ids):
                raise ValueError("Há itens indisponíveis no carrinho.")
            vendas = []
            for item in itens:
                if item.usuario_id == request.user.id or item.preco_anunciado is None or item.status_negociacao not in {item.NEGOCIACAO_VENDA, item.NEGOCIACAO_VENDA_OU_TROCA}:
                    raise ValueError("Há itens indisponíveis no carrinho.")
                valor = item.preco_anunciado
                taxa = (valor * TAXA_PLATAFORMA).quantize(Decimal("0.01"))
                vendas.append(TransacaoVenda.objects.create(
                    comprador=request.user, vendedor=item.usuario, colecionavel_usuario=item,
                    valor_item=valor, taxa_plataforma=taxa, valor_liquido_vendedor=valor - taxa,
                    whatsapp_comprador=request.user.telefone_whatsapp or "Não informado",
                    whatsapp_vendedor=item.usuario.telefone_whatsapp or "Não informado",
                ))
            sessao = stripe.checkout.Session.create(
                mode="payment", payment_method_types=["card"],
                line_items=[{"price_data": {"currency": "brl", "unit_amount": _centavos(v.valor_item), "product_data": {"name": v.colecionavel_usuario.nome_personalizado or v.colecionavel_usuario.modelo.nome_modelo or v.colecionavel_usuario.modelo.nome_personagem}}, "quantity": 1} for v in vendas],
                customer_email=request.user.email or None,
                success_url=request.build_absolute_uri(reverse("transacoes:checkout_sucesso")) + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=request.build_absolute_uri(reverse("transacoes:checkout_cancelado")) + "?session_id={CHECKOUT_SESSION_ID}",
                metadata={"comprador_id": str(request.user.id)},
            )
            TransacaoVenda.objects.filter(pk__in=[v.pk for v in vendas]).update(stripe_checkout_session_id=sessao.id)
        return redirect(sessao.url)
    except (stripe.StripeError, ValueError) as exc:
        logger.warning("Falha ao iniciar checkout Stripe: %s", exc)
        messages.error(request, "Não foi possível abrir o pagamento. Tente novamente em instantes.")
        return redirect("core:index")


@login_required
def checkout_sucesso(request):
    session_id = request.GET.get("session_id", "")
    vendas = TransacaoVenda.objects.filter(stripe_checkout_session_id=session_id, comprador=request.user)
    confirmado = False
    if session_id and vendas.exists() and settings.STRIPE_SECRET_KEY:
        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            confirmado = _confirmar_pagamento(stripe.checkout.Session.retrieve(session_id))
        except stripe.StripeError as exc:
            logger.warning("Falha ao consultar sessão Stripe %s: %s", session_id, exc)
    if confirmado:
        request.session[CHAVE_SESSAO_CARRINHO] = []
        request.session.modified = True
        messages.success(request, "Pagamento confirmado. O item foi retirado da venda.")
    else:
        messages.info(request, "Pagamento recebido. A confirmação ainda está sendo processada.")
    return redirect("core:index")


@login_required
def checkout_cancelado(request):
    session_id = request.GET.get("session_id", "")
    if session_id:
        TransacaoVenda.objects.filter(
            stripe_checkout_session_id=session_id,
            comprador=request.user,
            status_transacao=TransacaoVenda.STATUS_PENDENTE,
        ).update(status_transacao=TransacaoVenda.STATUS_CANCELADO)
    messages.info(request, "Pagamento cancelado. Seus itens continuam no carrinho.")
    return redirect("core:index")


@login_required
def historico_vendas(request):
    """Mostra compras e vendas do usuário, com reputação baseada em vendas avaliadas."""
    vendas = (
        TransacaoVenda.objects.filter(vendedor=request.user)
        .select_related("comprador", "colecionavel_usuario", "colecionavel_usuario__modelo")
        .select_related("avaliacao")
    )
    compras = (
        TransacaoVenda.objects.filter(comprador=request.user)
        .select_related("vendedor", "colecionavel_usuario", "colecionavel_usuario__modelo")
        .select_related("avaliacao")
    )
    reputacao = AvaliacaoVenda.objects.filter(avaliado=request.user).aggregate(
        media=Avg("nota"), total=Count("id")
    )
    return render(request, "transacoes/historico_vendas.html", {
        "vendas": vendas,
        "compras": compras,
        "reputacao_media": reputacao["media"],
        "reputacao_total": reputacao["total"],
    })


@login_required
def avaliar_venda(request, venda_id):
    venda = get_object_or_404(
        TransacaoVenda.objects.select_related("vendedor", "comprador", "colecionavel_usuario", "colecionavel_usuario__modelo"),
        pk=venda_id,
        comprador=request.user,
    )
    if not _venda_avaliavel(venda):
        messages.info(request, "A avaliação fica disponível após a confirmação do pagamento.")
        return redirect("transacoes:historico_vendas")
    if hasattr(venda, "avaliacao"):
        messages.info(request, "Esta compra já foi avaliada.")
        return redirect("transacoes:historico_vendas")

    if request.method == "POST":
        try:
            nota = int(request.POST.get("nota", ""))
        except (TypeError, ValueError):
            nota = 0
        comentario = request.POST.get("comentario", "").strip()
        if nota not in range(1, 6):
            messages.error(request, "Escolha uma nota entre 1 e 5 estrelas.")
        elif len(comentario) > 700:
            messages.error(request, "O comentário pode ter no máximo 700 caracteres.")
        else:
            avaliacao = AvaliacaoVenda(
                transacao=venda,
                avaliador=request.user,
                avaliado=venda.vendedor,
                nota=nota,
                comentario=comentario,
            )
            avaliacao.full_clean()
            try:
                avaliacao.save()
            except IntegrityError:
                messages.error(request, "Esta venda já foi avaliada. Atualize o histórico.")
            else:
                messages.success(request, "Avaliação enviada. Obrigado por fortalecer a comunidade!")
                return redirect("transacoes:historico_vendas")

    return render(request, "transacoes/avaliar_venda.html", {"venda": venda})


@csrf_exempt
@require_POST
def webhook_stripe(request):
    if not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponse(status=503)
    try:
        evento = stripe.Webhook.construct_event(request.body, request.headers.get("Stripe-Signature", ""), settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.SignatureVerificationError):
        return HttpResponse(status=400)
    if evento["type"] == "checkout.session.expired":
        sessao = evento["data"]["object"]
        TransacaoVenda.objects.filter(
            stripe_checkout_session_id=sessao["id"], status_transacao=TransacaoVenda.STATUS_PENDENTE
        ).update(status_transacao=TransacaoVenda.STATUS_CANCELADO)
    elif evento["type"] in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
        sessao = evento["data"]["object"]
        _confirmar_pagamento(sessao)
    return HttpResponse(status=200)
