from django.contrib import admin

from .models import AvaliacaoVenda, TransacaoVenda


@admin.register(TransacaoVenda)
class TransacaoVendaAdmin(admin.ModelAdmin):
    list_display = (
        "id", "colecionavel_usuario", "comprador", "vendedor",
        "valor_item", "taxa_plataforma", "valor_liquido_vendedor",
        "status_transacao", "stripe_checkout_session_id", "criado_em",
    )
    list_filter = ("status_transacao",)
    search_fields = ("comprador__username", "vendedor__username", "colecionavel_usuario__modelo__nome_personagem")
    autocomplete_fields = ["comprador", "vendedor", "colecionavel_usuario"]
    readonly_fields = ("criado_em", "stripe_checkout_session_id", "stripe_payment_intent_id")


@admin.register(AvaliacaoVenda)
class AvaliacaoVendaAdmin(admin.ModelAdmin):
    list_display = ("transacao", "avaliado", "avaliador", "nota", "criado_em")
    list_filter = ("nota",)
    search_fields = ("avaliado__username", "avaliador__username", "comentario")
    autocomplete_fields = ("transacao", "avaliador", "avaliado")
    readonly_fields = ("criado_em",)
