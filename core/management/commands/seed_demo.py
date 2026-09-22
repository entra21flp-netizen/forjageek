"""
Popula o banco com dados de demonstração — os 3 usuários combinados lá no
início do projeto (sem tela de cadastro no MVP, lembra?), cada um com itens
na prateleira, estantes e cruzamentos de wishlist/venda pra dar pra mostrar
match, chat e negociação funcionando de verdade.

Uso:
    python manage.py seed_demo
    python manage.py seed_demo --limpar   (apaga os dados de demo antes de recriar)
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from catalogo.models import Caracteristica, ModeloCaracteristica, ModeloColecionavel, TipoColecionavel
from inventario.models import ColecionavelUsuario, EstanteVirtual, ItemEstante
from usuarios.models import Usuario


class Command(BaseCommand):
    help = "Cria os 3 usuários de demonstração com catálogo e itens de exemplo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limpar",
            action="store_true",
            help="Apaga os usuários de demonstração (rafageek, colecionasp, mesageek) antes de recriar.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["limpar"]:
            Usuario.objects.filter(username__in=["rafageek", "colecionasp", "mesageek"]).delete()
            self.stdout.write(self.style.WARNING("Usuários de demonstração removidos."))

        tipos = self._criar_tipos()
        modelos = self._criar_catalogo(tipos)
        usuarios = self._criar_usuarios()
        self._criar_inventario(usuarios, modelos)

        self.stdout.write(self.style.SUCCESS("Seed de demonstração concluído."))
        self.stdout.write("Usuários criados (login / senha):")
        for username in ["rafageek", "colecionasp", "mesageek"]:
            self.stdout.write(f"  - {username} / demo12345")

    def _criar_tipos(self):
        nomes = ["Action Figure", "Model Kit", "Funko Pop", "Estátua"]
        tipos = {}
        for nome in nomes:
            tipo, _ = TipoColecionavel.objects.get_or_create(nome_tipo=nome)
            tipos[nome] = tipo
        return tipos

    def _criar_catalogo(self, tipos):
        escala = Caracteristica.objects.get_or_create(
            nome_caracteristica="Escala", defaults={"tipo_dado": Caracteristica.TIPO_DADO_TEXTO}
        )[0]
        material = Caracteristica.objects.get_or_create(
            nome_caracteristica="Material", defaults={"tipo_dado": Caracteristica.TIPO_DADO_TEXTO}
        )[0]

        catalogo_base = [
            {
                "nome_personagem": "Optimus Prime Studio Series",
                "franquia": "Transformers",
                "fabricante": "Hasbro",
                "tipo": tipos["Action Figure"],
                "ean": "7891234560017",
                "caracteristicas": {escala: "6 polegadas", material: "PVC/ABS"},
            },
            {
                "nome_personagem": "Batman Beyond",
                "franquia": "DC Comics",
                "fabricante": "McFarlane Toys",
                "tipo": tipos["Action Figure"],
                "ean": "7891234560024",
                "caracteristicas": {escala: "7 polegadas", material: "PVC"},
            },
            {
                "nome_personagem": "Pikachu Celebrations",
                "franquia": "Pokémon",
                "fabricante": "Funko",
                "tipo": tipos["Funko Pop"],
                "ean": "7891234560031",
                "caracteristicas": {escala: "N/A", material: "Vinil"},
            },
            {
                "nome_personagem": "Gundam RX-78-2 HG",
                "franquia": "Mobile Suit Gundam",
                "fabricante": "Bandai",
                "tipo": tipos["Model Kit"],
                "ean": "7891234560048",
                "caracteristicas": {escala: "1/144", material: "Plástico injetado"},
            },
            {
                "nome_personagem": "Gandalf, o Cinzento",
                "franquia": "O Senhor dos Anéis",
                "fabricante": "Weta Workshop",
                "tipo": tipos["Estátua"],
                "ean": "7891234560055",
                "caracteristicas": {escala: "1/6", material: "Polystone"},
            },
            {
                "nome_personagem": "Jurassic Park T-Rex",
                "franquia": "Jurassic Park",
                "fabricante": "NECA",
                "tipo": tipos["Action Figure"],
                "ean": "7891234560062",
                "caracteristicas": {escala: "1/12", material: "PVC"},
            },
        ]

        modelos = {}
        for item in catalogo_base:
            modelo, _ = ModeloColecionavel.objects.get_or_create(
                codigo_barras_ean_jan=item["ean"],
                defaults={
                    "nome_personagem": item["nome_personagem"],
                    "franquia": item["franquia"],
                    "fabricante": item["fabricante"],
                    "tipo": item["tipo"],
                },
            )
            for caracteristica, valor in item["caracteristicas"].items():
                ModeloCaracteristica.objects.get_or_create(
                    modelo=modelo, caracteristica=caracteristica, defaults={"valor": valor}
                )
            modelos[item["nome_personagem"]] = modelo

        return modelos

    def _criar_usuarios(self):
        dados = [
            dict(username="rafageek", first_name="Rafa", last_name="Geek",
                 email="rafa@forjageek.com.br", cpf="11111111111", telefone_whatsapp="+5547991110001"),
            dict(username="colecionasp", first_name="Coleciona", last_name="SP",
                 email="colecionasp@forjageek.com.br", cpf="22222222222", telefone_whatsapp="+5511992220002"),
            dict(username="mesageek", first_name="Mesa", last_name="Geek",
                 email="mesageek@forjageek.com.br", cpf="33333333333", telefone_whatsapp="+5547993330003"),
        ]

        usuarios = {}
        for dado in dados:
            usuario, criado = Usuario.objects.get_or_create(
                username=dado["username"],
                defaults={k: v for k, v in dado.items() if k != "username"},
            )
            if criado:
                usuario.set_password("demo12345")
                usuario.whatsapp_validado = True
                usuario.save()
            usuarios[dado["username"]] = usuario

        return usuarios

    def _criar_inventario(self, usuarios, modelos):
        rafa = usuarios["rafageek"]
        colecionasp = usuarios["colecionasp"]
        mesageek = usuarios["mesageek"]

        estante_rafa, _ = EstanteVirtual.objects.get_or_create(
            usuario=rafa, nome_estante="Sala de exposição", defaults={"ordem_exibicao": 1}
        )
        estante_colecionasp, _ = EstanteVirtual.objects.get_or_create(
            usuario=colecionasp, nome_estante="Prateleira principal", defaults={"ordem_exibicao": 1}
        )
        estante_mesageek, _ = EstanteVirtual.objects.get_or_create(
            usuario=mesageek, nome_estante="Mesa de trabalho", defaults={"ordem_exibicao": 1}
        )

        # (usuário, modelo, condição, preço pago, status de negociação, preço anunciado, estante)
        itens = [
            (rafa, "Optimus Prime Studio Series", "MISB lacrado", "249.90",
             ColecionavelUsuario.NEGOCIACAO_VENDA, "289.90", estante_rafa),
            (rafa, "Batman Beyond", "Aberto p/ exibição", "159.90",
             ColecionavelUsuario.NEGOCIACAO_EXIBICAO, None, estante_rafa),
            (colecionasp, "Pikachu Celebrations", "MISB lacrado", "119.90",
             ColecionavelUsuario.NEGOCIACAO_VENDA_OU_TROCA, "149.90", estante_colecionasp),
            (colecionasp, "Gandalf, o Cinzento", "Loose", "699.90",
             ColecionavelUsuario.NEGOCIACAO_VENDA, "849.90", estante_colecionasp),
            (mesageek, "Gundam RX-78-2 HG", "MISB lacrado", "89.90",
             ColecionavelUsuario.NEGOCIACAO_EXIBICAO, None, estante_mesageek),
            (mesageek, "Jurassic Park T-Rex", "Caixa avariada", "129.90",
             ColecionavelUsuario.NEGOCIACAO_TROCA, None, estante_mesageek),
        ]

        for posicao, (usuario, nome_modelo, condicao, preco_pago, negociacao, preco_anunciado, estante) in enumerate(itens, start=1):
            colecionavel, criado = ColecionavelUsuario.objects.get_or_create(
                usuario=usuario,
                modelo=modelos[nome_modelo],
                defaults={
                    "condicao_caixa": condicao,
                    "preco_pago": preco_pago,
                    "status_negociacao": negociacao,
                    "preco_anunciado": preco_anunciado,
                    "status_privacidade": ColecionavelUsuario.PRIVACIDADE_PUBLICO,
                },
            )
            if criado:
                ItemEstante.objects.get_or_create(
                    estante=estante, colecionavel_usuario=colecionavel, defaults={"posicao_slot": posicao}
                )
