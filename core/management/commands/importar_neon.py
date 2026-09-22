import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalogo.models import Caracteristica, ModeloCaracteristica, ModeloColecionavel, TipoColecionavel
from inventario.models import ColecionavelUsuario
from usuarios.models import Usuario


class Command(BaseCommand):
    help = "Importa o catálogo do Neon e, opcionalmente, vincula uma peça de cada modelo a um usuário."

    def add_arguments(self, parser):
        parser.add_argument("--usuario", required=True, help="Nome de usuário local que receberá os colecionáveis.")
        parser.add_argument("--dry-run", action="store_true", help="Mostra o que seria importado sem alterar o banco local.")

    def handle(self, *args, **options):
        try:
            import psycopg2
        except ImportError as exc:
            raise CommandError("Instale psycopg2-binary para acessar o Neon.") from exc

        database_url = os.getenv("NEON_DATABASE_URL") or os.getenv("DATABASE_URL")
        if not database_url:
            raise CommandError("Configure NEON_DATABASE_URL no arquivo .env.")
        try:
            usuario = Usuario.objects.get(username=options["usuario"])
        except Usuario.DoesNotExist as exc:
            raise CommandError(f"Usuário local '{options['usuario']}' não encontrado.") from exc

        try:
            connection = psycopg2.connect(database_url, connect_timeout=15)
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT m.id, t.nome_tipo, m.nome_modelo, m.nome_personagem,
                           m.franquia, m.fabricante, m.codigo_barras_ean_jan,
                           m.codigo_fabricante_sku
                    FROM modelos_colecionaveis m
                    JOIN tipos_colecionaveis t ON t.id = m.tipo_id
                    ORDER BY m.id
                """)
                modelos = cursor.fetchall()
                cursor.execute("""
                    SELECT mc.modelo_id, c.nome_caracteristica, c.tipo_dado, mc.valor
                    FROM modelos_caracteristicas mc
                    JOIN caracteristicas c ON c.id = mc.caracteristica_id
                    ORDER BY mc.modelo_id, c.nome_caracteristica
                """)
                valores = cursor.fetchall()
        except Exception as exc:
            raise CommandError(f"Não foi possível ler o catálogo do Neon: {exc}") from exc
        finally:
            if "connection" in locals():
                connection.close()

        valores_por_modelo = {}
        for modelo_id, nome, tipo_dado, valor in valores:
            valores_por_modelo.setdefault(modelo_id, []).append((nome, tipo_dado, valor))

        if options["dry_run"]:
            self.stdout.write(f"Neon: {len(modelos)} modelos e {len(valores)} características; destino: {usuario.username}.")
            return

        novos_modelos = modelos_atualizados = novas_pecas = pecas_existentes = 0
        with transaction.atomic():
            for remote_id, nome_tipo, nome_modelo, personagem, franquia, fabricante, ean, sku in modelos:
                tipo, _ = TipoColecionavel.objects.get_or_create(nome_tipo=nome_tipo)
                modelo = ModeloColecionavel.objects.filter(nome_modelo__iexact=nome_modelo).first()
                dados = {
                    "tipo": tipo,
                    "nome_modelo": nome_modelo,
                    "nome_personagem": personagem,
                    "franquia": franquia,
                    "fabricante": fabricante,
                    "codigo_barras_ean_jan": ean or None,
                    "codigo_fabricante_sku": sku or None,
                }
                if modelo:
                    for campo, valor in dados.items():
                        setattr(modelo, campo, valor)
                    modelo.save()
                    modelos_atualizados += 1
                else:
                    modelo = ModeloColecionavel.objects.create(**dados)
                    novos_modelos += 1

                for nome_caracteristica, tipo_dado, valor in valores_por_modelo.get(remote_id, []):
                    caracteristica, _ = Caracteristica.objects.get_or_create(
                        nome_caracteristica=nome_caracteristica,
                        defaults={"tipo_dado": tipo_dado},
                    )
                    caracteristica.tipos.add(tipo)
                    ModeloCaracteristica.objects.update_or_create(
                        modelo=modelo,
                        caracteristica=caracteristica,
                        defaults={"valor": valor},
                    )

                _, criada = ColecionavelUsuario.objects.get_or_create(
                    usuario=usuario,
                    modelo=modelo,
                    defaults={
                        "personalizado": False,
                        "estado_peca": "Não informado",
                        "condicao_caixa": "Não informado",
                        "nota": "Importado do catálogo Neon; complete os dados específicos da sua peça.",
                        "preco_pago": 0,
                        "status_privacidade": ColecionavelUsuario.PRIVACIDADE_PUBLICO,
                        "status_negociacao": ColecionavelUsuario.NEGOCIACAO_EXIBICAO,
                    },
                )
                if criada:
                    novas_pecas += 1
                else:
                    pecas_existentes += 1

        self.stdout.write(self.style.SUCCESS(
            f"Importação concluída: {novos_modelos} modelos novos, {modelos_atualizados} atualizados, "
            f"{novas_pecas} peças vinculadas a {usuario.username} e {pecas_existentes} já existentes."
        ))
