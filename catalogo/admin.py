from django.contrib import admin

from .models import Caracteristica, ModeloCaracteristica, ModeloColecionavel, TipoColecionavel


class ModeloCaracteristicaInline(admin.TabularInline):
    model = ModeloCaracteristica
    extra = 1


@admin.register(TipoColecionavel)
class TipoColecionavelAdmin(admin.ModelAdmin):
    list_display = ("nome_tipo",)
    search_fields = ("nome_tipo",)


@admin.register(ModeloColecionavel)
class ModeloColecionavelAdmin(admin.ModelAdmin):
    list_display = ("nome_personagem", "franquia", "fabricante", "tipo", "codigo_barras_ean_jan")
    list_filter = ("tipo", "fabricante")
    search_fields = ("nome_personagem", "franquia", "fabricante", "codigo_barras_ean_jan", "codigo_fabricante_sku")
    inlines = [ModeloCaracteristicaInline]


@admin.register(Caracteristica)
class CaracteristicaAdmin(admin.ModelAdmin):
    list_display = ("nome_caracteristica", "tipo_dado")
    search_fields = ("nome_caracteristica",)
