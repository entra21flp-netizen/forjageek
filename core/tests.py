from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from catalogo.models import ModeloColecionavel, TipoColecionavel
from inventario.models import ColecionavelUsuario, ImagemColecionavel
from inventario.models import EstanteVirtual


Usuario = get_user_model()


class PrateleiraSemDioramaLegadoTests(TestCase):
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

    def test_pagina_nao_cria_placeholders_de_diorama(self):
        resposta = self.client.get(reverse("core:prateleira"))

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.context["prateleiras"]), 3)
        self.assertContains(resposta, "+ Criar Diorama", count=1)
        self.assertNotContains(resposta, 'id="modal-dioramas"')


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


class ConsultaCodigoBarrasTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username="consulta-codigo",
            email="codigo@example.com",
            cpf="16899535009",
            telefone_whatsapp="+5511955555555",
            password="ForjaGeek!2026",
        )
        self.client.force_login(self.usuario)
        self.tipo = TipoColecionavel.objects.create(nome_tipo="Action Figure")

    def test_encontra_primeiro_no_catalogo_forjageek(self):
        modelo = ModeloColecionavel.objects.create(
            nome_modelo="Herói edição especial",
            tipo=self.tipo,
            nome_personagem="Herói",
            franquia="Saga",
            fabricante="Fabricante",
            codigo_barras_ean_jan="7891234560017",
        )

        with patch("core.consulta_codigo_barras.consultar_upcitemdb") as consulta_externa:
            resposta = self.client.post(
                reverse("core:consultar_codigo_barras"),
                {"codigo": "7891234560017"},
            )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["origem"], "catalogo_forjageek")
        self.assertEqual(resposta.json()["modelo_id"], modelo.id)
        consulta_externa.assert_not_called()

    @patch("core.consulta_codigo_barras.consultar_upcitemdb")
    def test_retorna_referencia_externa_sem_gravar_modelo(self, consultar):
        consultar.return_value = {
            "nome_modelo": "Figura encontrada",
            "fabricante": "Marca",
            "categoria_origem": "Toys",
            "imagem_modelo": "https://example.com/figura.jpg",
            "codigo_barras_ean_jan": "012345678905",
        }

        resposta = self.client.post(
            reverse("core:consultar_codigo_barras"),
            {"codigo": "012345678905"},
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["origem"], "upcitemdb")
        self.assertEqual(resposta.json()["produto"]["fabricante"], "Marca")
        self.assertEqual(ModeloColecionavel.objects.count(), 0)

    def test_rejeita_codigo_invalido(self):
        resposta = self.client.post(
            reverse("core:consultar_codigo_barras"),
            {"codigo": "ABC123"},
        )

        self.assertEqual(resposta.status_code, 400)
        self.assertIn("8 a 13", resposta.json()["erro"])

    def test_formulario_exibe_busca_por_codigo(self):
        resposta = self.client.get(reverse("core:cadastrar_colecionavel"))

        self.assertContains(resposta, "Buscar produto")
        self.assertContains(resposta, reverse("core:consultar_codigo_barras"))


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
        ImagemColecionavel.objects.create(
            colecionavel_usuario=self.item,
            url_imagem="https://example.com/figura-de-teste.jpg",
            imagem_principal=True,
        )
        self.client.force_login(self.comprador)

    def test_adiciona_item_e_mantem_carrinho_entre_paginas(self):
        resposta = self.client.post(reverse("core:adicionar_ao_carrinho"), {"item_id": self.item.id})

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["ids"], [self.item.id])
        self.assertEqual(resposta.json()["quantidade"], 1)
        pagina = self.client.get(reverse("core:catalogo_figuras"))
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

    def test_exibicao_lista_apenas_colecionaveis_publicos(self):
        ColecionavelUsuario.objects.create(
            usuario=self.vendedor,
            modelo=self.item.modelo,
            nome_personalizado="Item privado",
            estado_peca="Excelente",
            condicao_caixa="Com caixa",
            preco_pago="80.00",
            status_privacidade=ColecionavelUsuario.PRIVACIDADE_PRIVADO,
        )

        resposta = self.client.get(
            reverse("core:catalogo_figuras"),
            {"tipo": "Action Figure"},
        )

        self.assertContains(resposta, "Figura de teste")
        self.assertNotContains(resposta, "Item privado")

    def test_catalogo_e_mercado_ocultam_item_sem_imagem_sem_exclui_lo(self):
        sem_imagem = ColecionavelUsuario.objects.create(
            usuario=self.vendedor,
            modelo=self.item.modelo,
            nome_personalizado="Batman sem imagem",
            estado_peca="Excelente",
            condicao_caixa="Com caixa",
            preco_pago="80.00",
            preco_anunciado="120.00",
            status_privacidade=ColecionavelUsuario.PRIVACIDADE_PUBLICO,
            status_negociacao=ColecionavelUsuario.NEGOCIACAO_VENDA,
        )

        catalogo = self.client.get(reverse("core:catalogo_figuras"))
        mercado = self.client.get(reverse("core:mercado"))

        self.assertContains(catalogo, "Figura de teste")
        self.assertNotContains(catalogo, "Batman sem imagem")
        self.assertContains(mercado, "Figura de teste")
        self.assertNotContains(mercado, "Batman sem imagem")
        self.assertTrue(ColecionavelUsuario.objects.filter(pk=sem_imagem.pk).exists())
