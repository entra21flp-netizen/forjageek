from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Dados ForjaGeek", {"fields": ("cpf", "telefone_whatsapp", "whatsapp_validado")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Dados ForjaGeek", {"fields": ("cpf", "telefone_whatsapp", "whatsapp_validado")}),
    )
    list_display = ("username", "get_full_name", "email", "telefone_whatsapp", "whatsapp_validado", "is_staff")
    search_fields = ("username", "first_name", "last_name", "email", "cpf")
