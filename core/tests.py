from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from catalogo.models import ModeloColecionavel, TipoColecionavel
from inventario.models import ColecionavelUsuario
from inventario.models import Diorama, EstanteVirtual


Usuario = get_user_model()


class DioramaPorPrateleiraTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username="colecionador",
            email="colecionador@example.com",
            cpf="52998224725",
            telefone_whatsapp="+5511999999999",
            password="ForjaGeek!2026",
        )
        self.estante = EstanteVirtual.objects.create(
            usuario=self.usuario,
            nome_estante="Estante principal",
            ordem_exibicao=1,
        )
        self.client.force_login(self.usuario)

    def test_pagina_organiza_tres_dioramas_por_fileira(self):
        resposta = self.client.get(reverse("core:prateleira"))

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.context["prateleiras"]), 3)
        self.assertEqual(Diorama.objects.filter(estante=self.estante).count(), 3)
        self.assertContains(resposta, "+ Criar diorama", count=3)

    def test_salva_apenas_o_diorama_da_prateleira_escolhida(self):
        resposta = self.client.post(
            reverse("core:salvar_dioramas"),
            {
                "estante_id": self.estante.id,
                "ordem": 2,
                "titulo": "Batalha em Namekusei",
                "descricao": "Guerreiros reunidos na segunda prateleira.",
            },
        )

        self.assertEqual(resposta.status_code, 200)
        diorama = Diorama.objects.get(estante=self.estante, ordem=2)
        self.assertTrue(diorama.configurado)
        self.assertEqual(diorama.titulo, "Batalha em Namekusei")
        self.assertFalse(Diorama.objects.filter(estante=self.estante).exclude(ordem=2).exists())

    def test_seleciona_diorama_visivel_no_topo(self):
        resposta = self.client.post(
            reverse("core:selecionar_diorama_destaque"),
            {"estante_id": self.estante.id, "ordem": 3},
        )

        self.assertEqual(resposta.status_code, 200)
        self.estante.refresh_from_db()
        self.assertEqual(self.estante.diorama_destaque, 3)


class AnalisadorFotoCadastroTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username="analista",
            email="analista@example.com",
            cpf="15350946056",
            telefone_whatsapp="+5511988888888",
            password="ForjaGeek!2026",
        )
        self.client.force_login(self.usuario)

    @patch("core.analisador_gemini.analisar_imagens")
    def test_usa_somente_a_primeira_foto_como_referencia(self, analisar_imagens):
        analisar_imagens.return_value = {"identificacao": "Item reconhecido"}
        primeira = SimpleUploadedFile("frente.jpg", b"foto-frente", content_type="image/jpeg")
        segunda = SimpleUploadedFile("verso.png", b"foto-verso", content_type="image/png")

        resposta = self.client.post(
            reverse("core:analisar_foto_cadastro"),
            {"imagens": [primeira, segunda]},
        )

        self.assertEqual(resposta.status_code, 200)
        fotos_enviadas = analisar_imagens.call_args.args[0]
        self.assertEqual(len(fotos_enviadas), 1)
        self.assertEqual(fotos_enviadas[0].name, "frente.jpg")
        self.assertEqual(resposta.json()["referencia"], "primeira_foto")


class CarrinhoTests(TestCase):
    def setUp(self):
        self.vendedor = Usuario.objects.create_user(
            username="vendedor",
            email="vendedor@example.com",
            cpf="39053344705",
            telefone_whatsapp="+5511977777777",
            password="ForjaGeek!2026",
        )
        self.comprador = Usuario.objects.create_user(
            username="comprador",
            email="comprador@example.com",
            cpf="11144477735",
            telefone_whatsapp="+5511966666666",
            password="ForjaGeek!2026",
        )
        tipo = TipoColecionavel.objects.create(nome_tipo="Action Figure")
        modelo = ModeloColecionavel.objects.create(
            nome_modelo="Figura de teste",
            tipo=tipo,
            nome_personagem="Herói",
            franquia="Franquia",
            fabricante="Fabricante",
        )
        self.item = ColecionavelUsuario.objects.create(
            usuario=self.vendedor,
            modelo=modelo,
            estado_peca="Excelente",
            condicao_caixa="Com caixa",
            preco_pago="100.00",
            preco_anunciado="149.90",
            status_privacidade=ColecionavelUsuario.PRIVACIDADE_PUBLICO,
            status_negociacao=ColecionavelUsuario.NEGOCIACAO_VENDA,
        )
        self.client.force_login(self.comprador)

    def test_adiciona_item_e_mantem_carrinho_entre_paginas(self):
        resposta = self.client.post(reverse("core:adicionar_ao_carrinho"), {"item_id": self.item.id})

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["ids"], [self.item.id])
        self.assertEqual(resposta.json()["quantidade"], 1)
        pagina = self.client.get(reverse("core:index"))
        self.assertContains(pagina, "Figura de teste")
        self.assertContains(pagina, 'id="carrinho-contagem"')
        self.assertContains(pagina, f'data-carrinho-adicionar="{self.item.id}"')

    def test_remove_item_do_carrinho(self):
        session = self.client.session
        session["carrinho_itens"] = [self.item.id]
        session.save()

        resposta = self.client.post(reverse("core:remover_do_carrinho"), {"item_id": self.item.id})

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["quantidade"], 0)
        self.assertEqual(resposta.json()["ids"], [])
