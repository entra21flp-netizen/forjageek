import io
import shutil
import tempfile
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from catalogo.models import ModeloColecionavel, TipoColecionavel
from inventario.models import ColecionavelUsuario, EstanteVirtual, ImagemColecionavel, ItemEstante
from usuarios.models import Usuario

from .models import DioramaGeradoNovo, DioramaPresetNovo
from .services.diorama_ai import DioramaAIError, DioramaAIRateLimitError, ResultadoGeracao, _mensagem_erro_openai, gerar_diorama, mensagem_limite_openai


class DioramaNovoTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        self.user = Usuario.objects.create_user(username="dono", password="senha-forte", cpf="1", telefone_whatsapp="1")
        self.other = Usuario.objects.create_user(username="outro", password="senha-forte", cpf="2", telefone_whatsapp="2")
        tipo = TipoColecionavel.objects.create(nome_tipo="Action Figure")
        modelo = ModeloColecionavel.objects.create(tipo=tipo, nome_modelo="Herói", nome_personagem="Herói", franquia="Saga", fabricante="Forja")
        self.item = ColecionavelUsuario.objects.create(usuario=self.user, modelo=modelo, condicao_caixa="Boa", preco_pago="100.00")
        self.outro_item = ColecionavelUsuario.objects.create(usuario=self.other, modelo=modelo, condicao_caixa="Boa", preco_pago="100.00")
        imagem_item = io.BytesIO()
        foto = Image.new("RGBA", (240, 420), (255, 255, 255, 0))
        foto.paste((35, 55, 90, 255), (70, 35, 170, 390))
        foto.save(imagem_item, format="PNG")
        ImagemColecionavel.objects.create(
            colecionavel_usuario=self.item,
            arquivo=SimpleUploadedFile("item.png", imagem_item.getvalue(), content_type="image/png"),
            url_imagem="",
            imagem_principal=True,
        )
        self.preset = DioramaPresetNovo.objects.create(nome="Cidade", slug="cidade", descricao="Noite", prompt_base="Cidade noturna")
        DioramaPresetNovo.objects.get_or_create(
            slug="nova-york-noturna",
            defaults={"nome": "Nova York Noturna", "descricao": "Coberturas e arranha-céus sob chuva.", "prompt_base": "Cobertura noturna."},
        )
        self.client.login(username="dono", password="senha-forte")

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media, ignore_errors=True)

    def _resultado(self):
        token = uuid.uuid4().hex
        caminho = Path(self.media) / "diorama_previews_novo" / str(self.user.pk) / f"{token}.png"
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(b"imagem-gerada")
        return ResultadoGeracao(token, caminho, "prompt seguro", "modelo-teste")

    def _diorama(self, usuario=None, colecionavel=None):
        return DioramaGeradoNovo.objects.create(
            usuario=usuario or self.user,
            colecionavel=colecionavel or self.item,
            tipo="personalizado",
            descricao="Cena",
            imagem=SimpleUploadedFile(f"d-{uuid.uuid4().hex}.png", b"img"),
            prompt_utilizado="prompt preservado",
        )

    @override_settings(OPENAI_API_KEY=None)
    def test_geracao_exige_chave_openai(self):
        with self.assertRaisesMessage(DioramaAIError, "OPENAI_API_KEY"):
            gerar_diorama(self.item, "Cidade noturna", self.user.pk)

    @override_settings(OPENAI_API_KEY="chave-de-teste", OPENAI_IMAGE_MODEL="gpt-image-2.5-flare")
    @patch("dioramas_novo.services.diorama_ai.OpenAI")
    def test_geracao_openai_usa_foto_e_salva_preview(self, cliente_mock):
        import base64

        imagem_saida = b"imagem-png-de-teste"
        cliente_mock.return_value.images.edit.return_value = SimpleNamespace(
            data=[SimpleNamespace(b64_json=base64.b64encode(imagem_saida).decode("ascii"))]
        )
        resultado = gerar_diorama(self.item, "Cidade noturna", self.user.pk)
        argumentos = cliente_mock.return_value.images.edit.call_args.kwargs
        self.assertEqual(argumentos["model"], "gpt-image-2.5-flare")
        self.assertEqual(argumentos["size"], "1536x864")
        self.assertNotIn("input_fidelity", argumentos)
        self.assertEqual(argumentos["image"].read(8), b"\x89PNG\r\n\x1a\n")
        self.assertEqual(resultado.caminho.read_bytes(), imagem_saida)
        self.assertEqual(resultado.modelo, "gpt-image-2.5-flare")

    @override_settings(OPENAI_API_KEY="chave-de-teste")
    @patch("dioramas_novo.services.diorama_ai.OpenAI")
    def test_geracao_trata_chave_invalida(self, cliente_mock):
        import httpx
        from openai import APIStatusError

        resposta = httpx.Response(401, request=httpx.Request("POST", "https://api.openai.com/v1/images/edits"))
        cliente_mock.return_value.images.edit.side_effect = APIStatusError("Unauthorized", response=resposta, body={})
        with self.assertRaisesMessage(DioramaAIError, "OPENAI_API_KEY"):
            gerar_diorama(self.item, "Cidade noturna", self.user.pk)

    @override_settings(OPENAI_API_KEY="chave-de-teste")
    @patch("dioramas_novo.services.diorama_ai.OpenAI")
    def test_geracao_trata_falha_de_conexao(self, cliente_mock):
        import httpx
        from openai import APIConnectionError

        cliente_mock.return_value.images.edit.side_effect = APIConnectionError(
            request=httpx.Request("POST", "https://api.openai.com/v1/images/edits")
        )
        with self.assertRaisesMessage(DioramaAIError, "Não foi possível concluir"):
            gerar_diorama(self.item, "Cidade noturna", self.user.pk)

    @override_settings(OPENAI_API_KEY="chave-de-teste")
    @patch("dioramas_novo.services.diorama_ai.OpenAI")
    def test_geracao_trata_resposta_sem_imagem(self, cliente_mock):
        cliente_mock.return_value.images.edit.return_value = SimpleNamespace(data=[])
        with self.assertRaisesMessage(DioramaAIError, "não retornou uma imagem"):
            gerar_diorama(self.item, "Cidade noturna", self.user.pk)

    @override_settings(OPENAI_API_KEY="chave-de-teste")
    @patch("dioramas_novo.services.diorama_ai.OpenAI")
    def test_geracao_rejeita_foto_invalida(self, cliente_mock):
        imagem = self.item.imagens.get(imagem_principal=True)
        imagem.arquivo.save("invalida.png", SimpleUploadedFile("invalida.png", b"nao-e-imagem"), save=True)
        with self.assertRaisesMessage(DioramaAIError, "não é uma imagem válida"):
            gerar_diorama(self.item, "Cidade noturna", self.user.pk)
        cliente_mock.return_value.images.edit.assert_not_called()

    def test_erro_400_de_parametro_nao_culpa_foto(self):
        erro = SimpleNamespace(
            status_code=400,
            body={"error": {"code": "invalid_request_error", "param": "size", "message": "Invalid size"}},
        )
        self.assertIn("parâmetro 'size'", _mensagem_erro_openai(erro))

    def test_erro_input_fidelity_nao_culpa_modelo(self):
        erro = SimpleNamespace(
            status_code=400,
            body={"error": {"code": "invalid_input_fidelity_model", "param": "input_fidelity", "message": "Unsupported parameter"}},
        )
        self.assertIn("parâmetro 'input_fidelity'", _mensagem_erro_openai(erro))

    def test_erro_400_desconhecido_pede_detalhe_do_terminal(self):
        erro = SimpleNamespace(status_code=400, body={"error": {"message": "Unknown issue"}})
        mensagem = _mensagem_erro_openai(erro)
        self.assertIn("terminal", mensagem)
        self.assertNotIn("foto", mensagem)

    def test_erro_429_creditos_nao_sugere_tentar_mais_tarde(self):
        erro = SimpleNamespace(body={"error": {"code": "credit_balance_exhausted", "type": "insufficient_quota"}})
        mensagem = mensagem_limite_openai(erro)
        self.assertIn("créditos", mensagem)
        self.assertNotIn("tente novamente", mensagem)

    def test_erro_429_ritmo_e_temporario(self):
        erro = SimpleNamespace(body={"error": {"code": "rate_limit_exceeded", "type": "rate_limit_error"}})
        self.assertIn("temporário", mensagem_limite_openai(erro))

    def test_rotas_exigem_login(self):
        self.client.logout()
        resposta = self.client.get(reverse("dioramas_novo:selecionar"))
        self.assertEqual(resposta.status_code, 302)

    def test_lista_apenas_colecionaveis_do_usuario(self):
        resposta = self.client.get(reverse("dioramas_novo:selecionar"))
        self.assertContains(resposta, "Herói")
        self.assertQuerySetEqual(resposta.context["colecionaveis"], [self.item])

    def test_nao_configura_colecionavel_de_outro_usuario(self):
        resposta = self.client.get(reverse("dioramas_novo:configurar", args=[self.outro_item.pk]))
        self.assertEqual(resposta.status_code, 404)

    @patch("dioramas_novo.views.gerar_diorama")
    def test_gerar_preview_nao_cria_registro(self, gerar_mock):
        gerar_mock.return_value = self._resultado()
        resposta = self.client.post(reverse("dioramas_novo:gerar", args=[self.item.pk]), {"tipo": "personalizado", "descricao": "Chuva e cidade"})
        self.assertRedirects(resposta, reverse("dioramas_novo:preview"), fetch_redirect_response=False)
        self.assertEqual(DioramaGeradoNovo.objects.count(), 0)

    @patch("dioramas_novo.views.gerar_diorama")
    def test_erro_429_e_tratado(self, gerar_mock):
        gerar_mock.side_effect = DioramaAIRateLimitError("Limite temporário de geração atingido.")
        resposta = self.client.post(reverse("dioramas_novo:gerar", args=[self.item.pk]), {"tipo": "personalizado", "descricao": "Chuva"})
        self.assertEqual(resposta.status_code, 503)
        self.assertContains(resposta, "Limite temporário", status_code=503)

    @patch("dioramas_novo.views.gerar_diorama")
    def test_confirmar_e_idempotente(self, gerar_mock):
        gerar_mock.return_value = self._resultado()
        self.client.post(reverse("dioramas_novo:gerar", args=[self.item.pk]), {"tipo": "personalizado", "descricao": "Cidade noturna"})
        resposta = self.client.post(reverse("dioramas_novo:confirmar"))
        diorama = DioramaGeradoNovo.objects.get()
        self.assertRedirects(resposta, reverse("dioramas_novo:posicionar", args=[diorama.pk]), fetch_redirect_response=False)
        self.assertEqual(DioramaGeradoNovo.objects.count(), 1)
        self.client.post(reverse("dioramas_novo:confirmar"))
        self.assertEqual(DioramaGeradoNovo.objects.count(), 1)

    def test_preset_salva_diretamente_sem_chamar_ia(self):
        preset = DioramaPresetNovo.objects.get(slug="nova-york-noturna")
        with patch("dioramas_novo.views.gerar_diorama") as gerar_mock:
            resposta = self.client.post(
                reverse("dioramas_novo:gerar", args=[self.item.pk]),
                {"tipo": "predefinido", "preset": preset.pk},
            )
        diorama = DioramaGeradoNovo.objects.get()
        self.assertRedirects(resposta, reverse("dioramas_novo:posicionar", args=[diorama.pk]), fetch_redirect_response=False)
        gerar_mock.assert_not_called()
        self.assertEqual(diorama.tipo, DioramaGeradoNovo.TIPO_PREDEFINIDO)
        self.assertEqual(diorama.preset, preset)
        self.assertTrue(diorama.imagem.name)
        with Image.open(diorama.imagem.path) as imagem:
            self.assertEqual(imagem.size, (1600, 900))

    @patch("dioramas_novo.views.gerar_diorama")
    def test_cancelar_nao_cria_registro(self, gerar_mock):
        gerar_mock.return_value = self._resultado()
        self.client.post(reverse("dioramas_novo:gerar", args=[self.item.pk]), {"tipo": "personalizado", "descricao": "Floresta"})
        self.client.post(reverse("dioramas_novo:cancelar"))
        self.assertEqual(DioramaGeradoNovo.objects.count(), 0)

    def test_exclusao_post_e_ownership(self):
        diorama = self._diorama()
        estante = EstanteVirtual.objects.create(usuario=self.user, nome_estante="Principal", ordem_exibicao=1)
        ItemEstante.objects.create(estante=estante, diorama_novo=diorama, posicao_slot=1)
        caminho_imagem = Path(diorama.imagem.path)
        self.assertEqual(self.client.get(reverse("dioramas_novo:excluir", args=[diorama.pk])).status_code, 200)
        self.assertTrue(DioramaGeradoNovo.objects.filter(pk=diorama.pk).exists())
        self.assertTrue(ItemEstante.objects.filter(diorama_novo=diorama, posicao_slot=1).exists())
        client_outro = Client()
        client_outro.login(username="outro", password="senha-forte")
        self.assertEqual(client_outro.post(reverse("dioramas_novo:excluir", args=[diorama.pk])).status_code, 404)
        self.client.post(reverse("dioramas_novo:excluir", args=[diorama.pk]))
        self.assertFalse(DioramaGeradoNovo.objects.filter(pk=diorama.pk).exists())
        self.assertFalse(ItemEstante.objects.filter(diorama_novo_id=diorama.pk).exists())
        self.assertFalse(caminho_imagem.exists())
        self.assertTrue(ColecionavelUsuario.objects.filter(pk=self.item.pk).exists())

    def test_posicionar_remover_e_adicionar_mesmo_diorama(self):
        diorama = self._diorama()
        self.client.post(reverse("dioramas_novo:posicionar", args=[diorama.pk]), {"linha": 1})
        posicao = ItemEstante.objects.get(diorama_novo=diorama)
        self.assertEqual(posicao.posicao_slot, 1)
        prateleira = self.client.get(reverse("core:prateleira"))
        self.assertContains(prateleira, 'class="dn-shelf-row"', count=1)
        imagem = diorama.imagem.name
        with patch("dioramas_novo.views.gerar_diorama") as gerar_mock:
            self.client.post(reverse("dioramas_novo:remover_prateleira", args=[diorama.pk]))
        gerar_mock.assert_not_called()
        self.assertFalse(ItemEstante.objects.filter(diorama_novo=diorama).exists())
        diorama.refresh_from_db()
        self.assertEqual(diorama.imagem.name, imagem)
        self.assertEqual(diorama.prompt_utilizado, "prompt preservado")
        self.client.post(reverse("dioramas_novo:posicionar", args=[diorama.pk]), {"linha": 3})
        self.assertEqual(ItemEstante.objects.get(diorama_novo=diorama).posicao_slot, 9)
        self.assertEqual(DioramaGeradoNovo.objects.get().pk, diorama.pk)

    def test_drag_and_drop_move_diorama_entre_linhas(self):
        estante = EstanteVirtual.objects.create(usuario=self.user, nome_estante="Principal", ordem_exibicao=1)
        diorama = self._diorama()
        ItemEstante.objects.create(estante=estante, diorama_novo=diorama, posicao_slot=1)
        with patch("dioramas_novo.views.gerar_diorama") as gerar_mock:
            resposta = self.client.post(reverse("core:mover_item_estante"), {
                "item_id": diorama.pk, "item_type": "diorama", "destino": 10, "estante_id": estante.pk,
            })
        self.assertEqual(resposta.status_code, 200)
        gerar_mock.assert_not_called()
        self.assertEqual(ItemEstante.objects.get(diorama_novo=diorama).posicao_slot, 9)

    def test_diorama_nao_entra_em_linha_parcialmente_ocupada(self):
        estante = EstanteVirtual.objects.create(usuario=self.user, nome_estante="Principal", ordem_exibicao=1)
        diorama = self._diorama()
        ItemEstante.objects.create(estante=estante, diorama_novo=diorama, posicao_slot=1)
        ItemEstante.objects.create(estante=estante, colecionavel_usuario=self.item, posicao_slot=6)
        resposta = self.client.post(reverse("core:mover_item_estante"), {
            "item_id": diorama.pk, "item_type": "diorama", "destino": 6, "estante_id": estante.pk,
        })
        self.assertEqual(resposta.status_code, 409)
        self.assertEqual(ItemEstante.objects.get(diorama_novo=diorama).posicao_slot, 1)
        self.assertEqual(ItemEstante.objects.get(colecionavel_usuario=self.item).posicao_slot, 6)

    def test_colecionavel_nao_entra_em_linha_com_diorama(self):
        estante = EstanteVirtual.objects.create(usuario=self.user, nome_estante="Principal", ordem_exibicao=1)
        diorama = self._diorama()
        ItemEstante.objects.create(estante=estante, diorama_novo=diorama, posicao_slot=1)
        resposta = self.client.post(reverse("core:mover_item_estante"), {
            "item_id": self.item.pk, "item_type": "colecionavel", "destino": 3, "estante_id": estante.pk,
        })
        self.assertEqual(resposta.status_code, 409)
        self.assertFalse(ItemEstante.objects.filter(colecionavel_usuario=self.item, posicao_slot=3).exists())

    def test_prateleira_cheia_nao_sobrescreve(self):
        estante = EstanteVirtual.objects.create(usuario=self.user, nome_estante="Principal", ordem_exibicao=1)
        for numero in range(1, 13):
            item = ColecionavelUsuario.objects.create(
                usuario=self.user, modelo=self.item.modelo, condicao_caixa="Boa", preco_pago="1.00",
            )
            ItemEstante.objects.create(estante=estante, colecionavel_usuario=item, posicao_slot=numero)
        diorama = self._diorama()
        resposta = self.client.get(reverse("dioramas_novo:posicionar", args=[diorama.pk]))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "não existe uma linha completamente livre")
        self.assertEqual(ItemEstante.objects.filter(estante=estante).count(), 12)
        self.assertTrue(DioramaGeradoNovo.objects.filter(pk=diorama.pk).exists())
        self.assertFalse(ItemEstante.objects.filter(diorama_novo=diorama).exists())

    def test_seguranca_remover_diorama_de_outro_usuario(self):
        diorama = self._diorama(usuario=self.other, colecionavel=self.outro_item)
        self.assertEqual(self.client.post(reverse("dioramas_novo:remover_prateleira", args=[diorama.pk])).status_code, 404)

    def test_csrf_protege_confirmacao(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(reverse("dioramas_novo:confirmar")).status_code, 403)

    def test_prateleira_funciona_sem_diorama_antigo(self):
        estante = EstanteVirtual.objects.create(usuario=self.user, nome_estante="Principal", ordem_exibicao=1)
        ItemEstante.objects.create(estante=estante, colecionavel_usuario=self.item, posicao_slot=1)
        resposta = self.client.get(reverse("core:prateleira"))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "+ Criar Diorama")
        self.assertContains(resposta, self.item.imagens.get(imagem_principal=True).arquivo.url)
        self.assertNotContains(resposta, '<span aria-label="Sem imagem cadastrada">📦</span>')

    def test_rotas_gerais_permanecem_acessiveis(self):
        rotas = [
            reverse("core:index"),
            reverse("core:catalogo_figuras"),
            reverse("core:produto", args=[self.item.modelo_id]),
            reverse("core:meus_colecionaveis"),
            reverse("core:prateleira"),
            reverse("core:wishlist"),
            reverse("core:perfil_colecionador", args=[self.user.username]),
            reverse("core:login"),
            reverse("core:cadastro_usuario"),
        ]
        for rota in rotas:
            with self.subTest(rota=rota):
                self.assertLess(self.client.get(rota).status_code, 500)
        self.assertLess(self.client.post(reverse("core:logout")).status_code, 500)

    def test_diorama_publico_respeita_privacidade_do_colecionavel(self):
        estante = EstanteVirtual.objects.create(
            usuario=self.user, nome_estante="Pública", ordem_exibicao=1, status_privacidade="publico",
        )
        diorama = self._diorama()
        ItemEstante.objects.create(estante=estante, diorama_novo=diorama, posicao_slot=1)
        rota = reverse("core:prateleira_publica", args=[self.user.username])
        self.item.status_privacidade = ColecionavelUsuario.PRIVACIDADE_PRIVADO
        self.item.save(update_fields=["status_privacidade"])
        self.assertNotContains(self.client.get(rota), 'class="dn-shelf-row"')
        self.item.status_privacidade = ColecionavelUsuario.PRIVACIDADE_PUBLICO
        self.item.save(update_fields=["status_privacidade"])
        self.assertContains(self.client.get(rota), 'class="dn-shelf-row"', count=1)
