from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from unittest.mock import patch

from .models import Usuario


class CadastroUsuarioTests(TestCase):
    def dados_validos(self):
        return {
            "first_name": "Ana",
            "last_name": "Silva",
            "username": "anacoleciona",
            "email": "ana@example.com",
            "cpf": "529.982.247-25",
            "telefone_whatsapp": "(11) 99999-9999",
            "password1": "ForjaGeek!2026",
            "password2": "ForjaGeek!2026",
        }

    def test_cadastro_cria_usuario_e_inicia_sessao(self):
        resposta = self.client.post(reverse("core:cadastro_usuario"), self.dados_validos())

        self.assertRedirects(resposta, reverse("core:verificar_whatsapp"))
        usuario = Usuario.objects.get(username="anacoleciona")
        self.assertEqual(usuario.cpf, "52998224725")
        self.assertEqual(usuario.telefone_whatsapp, "+5511999999999")
        self.assertFalse(usuario.whatsapp_validado)
        self.assertEqual(int(self.client.session["_auth_user_id"]), usuario.pk)

    def test_cadastro_recusa_email_duplicado(self):
        dados = self.dados_validos()
        Usuario.objects.create_user(
            username="existente",
            email=dados["email"],
            cpf="16899535009",
            telefone_whatsapp="+5511988887777",
            password="Senha!2026",
        )

        resposta = self.client.post(reverse("core:cadastro_usuario"), dados)

        self.assertContains(resposta, "Já existe uma conta com este e-mail.")
        self.assertEqual(Usuario.objects.filter(email=dados["email"]).count(), 1)

    def test_cadastro_recusa_whatsapp_duplicado(self):
        dados = self.dados_validos()
        Usuario.objects.create_user(username="existente", email="outra@example.com", cpf="16899535009", telefone_whatsapp="+5511999999999", password="Senha!2026")
        resposta = self.client.post(reverse("core:cadastro_usuario"), dados)
        self.assertContains(resposta, "Já existe uma conta com este número de WhatsApp.")

    @patch("usuarios.views.conferir_codigo", return_value=True)
    def test_codigo_aprovado_confirma_whatsapp(self, conferir):
        usuario = Usuario.objects.create_user(username="pendente", email="pendente@example.com", cpf="16899535009", telefone_whatsapp="+5511988887777", password="Senha!2026")
        self.client.force_login(usuario)
        resposta = self.client.post(reverse("core:verificar_whatsapp"), {"acao": "confirmar", "codigo": "123456"})
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta.url, reverse("core:index"))
        usuario.refresh_from_db()
        self.assertTrue(usuario.whatsapp_validado)
        conferir.assert_called_once_with("+5511988887777", "123456")

    @override_settings(EMAIL_CONFIGURADO=True)
    @patch("usuarios.views.send_mail")
    def test_recuperacao_envia_link_para_email_cadastrado(self, enviar):
        Usuario.objects.create_user(
            username="colecionador", email="colecionador@example.com", cpf="16899535009",
            telefone_whatsapp="+5511988887777", password="SenhaAntiga!2026",
        )
        resposta = self.client.post(reverse("core:recuperar_conta"), {"email": "colecionador@example.com"})
        self.assertRedirects(resposta, reverse("core:recuperar_conta"))
        enviar.assert_called_once()
        self.assertEqual(enviar.call_args.args[3], ["colecionador@example.com"])
        self.assertIn("recuperar-conta", enviar.call_args.args[1])

    def test_recuperacao_redefine_senha_com_link_valido(self):
        usuario = Usuario.objects.create_user(
            username="colecionador", email="colecionador@example.com", cpf="16899535009",
            telefone_whatsapp="+5511988887777", password="SenhaAntiga!2026",
        )
        url = reverse("core:redefinir_senha_email", args=[
            urlsafe_base64_encode(force_bytes(usuario.pk)), default_token_generator.make_token(usuario),
        ])
        resposta = self.client.post(url, {
            "password1": "NovaSenha!2026", "password2": "NovaSenha!2026",
        })
        self.assertRedirects(resposta, reverse("core:login"))
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password("NovaSenha!2026"))
