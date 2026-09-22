import re

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Usuario


def _cpf_valido(cpf):
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(cpf[indice]) * (tamanho + 1 - indice) for indice in range(tamanho))
        digito = (soma * 10) % 11
        if digito == 10:
            digito = 0
        if digito != int(cpf[tamanho]):
            return False
    return True


class CadastroUsuarioForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, label="Nome")
    last_name = forms.CharField(max_length=150, label="Sobrenome")
    email = forms.EmailField(label="E-mail")
    cpf = forms.CharField(max_length=15, label="CPF")
    telefone_whatsapp = forms.CharField(max_length=20, label="WhatsApp")

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = (
            "first_name",
            "last_name",
            "username",
            "email",
            "cpf",
            "telefone_whatsapp",
            "password1",
            "password2",
        )
        labels = {"username": "Nome de usuário"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        atributos = {
            "first_name": {"autocomplete": "given-name", "placeholder": "Seu nome"},
            "last_name": {"autocomplete": "family-name", "placeholder": "Seu sobrenome"},
            "username": {"autocomplete": "username", "placeholder": "Como aparecerá na ForjaGeek"},
            "email": {"autocomplete": "email", "placeholder": "voce@exemplo.com"},
            "cpf": {"inputmode": "numeric", "autocomplete": "off", "placeholder": "000.000.000-00"},
            "telefone_whatsapp": {"inputmode": "tel", "autocomplete": "tel", "placeholder": "(11) 99999-9999"},
            "password1": {"autocomplete": "new-password", "placeholder": "Crie uma senha segura"},
            "password2": {"autocomplete": "new-password", "placeholder": "Repita a senha"},
        }
        for nome, attrs in atributos.items():
            self.fields[nome].widget.attrs.update(attrs)
        self.fields["username"].help_text = "Use letras, números e os caracteres @ . + - _."
        self.fields["cpf"].help_text = "O CPF será usado para identificar sua conta."
        self.fields["telefone_whatsapp"].help_text = "A validação do número poderá ser feita depois."

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe uma conta com este e-mail.")
        return email

    def clean_cpf(self):
        cpf = re.sub(r"\D", "", self.cleaned_data["cpf"])
        if not _cpf_valido(cpf):
            raise forms.ValidationError("Informe um CPF válido.")
        if Usuario.objects.filter(cpf=cpf).exists():
            raise forms.ValidationError("Já existe uma conta com este CPF.")
        return cpf

    def clean_telefone_whatsapp(self):
        valor = self.cleaned_data["telefone_whatsapp"].strip()
        digitos = re.sub(r"\D", "", valor)
        if len(digitos) in (10, 11):
            digitos = "55" + digitos
        if not 12 <= len(digitos) <= 15:
            raise forms.ValidationError("Informe um número de WhatsApp válido, com DDD.")
        telefone = "+" + digitos
        if Usuario.objects.filter(telefone_whatsapp=telefone).exists():
            raise forms.ValidationError("Já existe uma conta com este número de WhatsApp.")
        return telefone
