from django.contrib import admin

from .models import DioramaGeradoNovo, DioramaPresetNovo


@admin.register(DioramaPresetNovo)
class DioramaPresetNovoAdmin(admin.ModelAdmin):
    list_display = ("nome", "slug", "ativo", "data_criacao")
    list_filter = ("ativo",)
    prepopulated_fields = {"slug": ("nome",)}


@admin.register(DioramaGeradoNovo)
class DioramaGeradoNovoAdmin(admin.ModelAdmin):
    list_display = ("colecionavel", "usuario", "tipo", "preset", "data_criacao")
    list_filter = ("tipo", "data_criacao")
    search_fields = ("usuario__username", "colecionavel__modelo__nome_personagem")
    readonly_fields = ("prompt_utilizado", "data_criacao", "atualizado_em")
