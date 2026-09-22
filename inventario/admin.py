from django.contrib import admin

from .models import AvaliacaoEstante, ColecionavelUsuario, EstanteVirtual, ItemEstante


class ItemEstanteInline(admin.TabularInline):
    model = ItemEstante
    extra = 0


@admin.register(ColecionavelUsuario)
class ColecionavelUsuarioAdmin(admin.ModelAdmin):
    list_display = (
        "modelo", "usuario", "condicao_caixa", "status_negociacao",
        "preco_pago", "preco_anunciado", "status_privacidade", "data_inclusao",
    )
    list_filter = ("status_negociacao", "status_privacidade", "condicao_caixa")
    search_fields = ("modelo__nome_personagem", "usuario__username", "usuario__first_name")
    autocomplete_fields = ["modelo"]


@admin.register(EstanteVirtual)
class EstanteVirtualAdmin(admin.ModelAdmin):
    list_display = ("nome_estante", "usuario", "status_privacidade", "ordem_exibicao", "tema_visual")
    list_filter = ("status_privacidade", "tema_visual")
    search_fields = ("nome_estante", "usuario__username")
    inlines = [ItemEstanteInline]


@admin.register(ItemEstante)
class ItemEstanteAdmin(admin.ModelAdmin):
    list_display = ("estante", "colecionavel_usuario", "posicao_slot", "data_posicionamento")
    list_filter = ("estante",)


@admin.register(AvaliacaoEstante)
class AvaliacaoEstanteAdmin(admin.ModelAdmin):
    list_display = ("estante", "avaliador", "nota", "criado_em")
    list_filter = ("nota",)
    search_fields = ("estante__nome_estante", "avaliador__username", "comentario")
    autocomplete_fields = ("estante", "avaliador")
    readonly_fields = ("criado_em",)
