from django.core.management.base import BaseCommand
from django.db import transaction
from catalogo.models import TipoColecionavel, ModeloColecionavel, Caracteristica, ModeloCaracteristica

FIGURAS = [
    ('Son Goku', 'Dragon Ball Z', 'S.H.Figuarts Super Saiyan Full Power SON GOKU', '2021', '14.0'),
    ('Vegeta', 'Dragon Ball Z', 'S.H.Figuarts VEGETA <Z-FIGHTERS>', '2027', '13.5'),
    ('Trunks', 'Dragon Ball Z', 'S.H.Figuarts Trunks <Z-FIGHTERS>', '2027', '14.0'),
    ('Naruto Uzumaki', 'Naruto: Shippuden', 'S.H.Figuarts NARUTO UZUMAKI -The Hope Entrusted to the Nine-Tailed Fox Jinchuriki-', '2026', '14.5'),
    ('Sasuke Uchiha', 'Naruto: Shippuden', 'S.H.Figuarts SASUKE UCHIHA -He who bears all Hatred-', '2022', '14.5'),
    ('Kakashi Hatake', 'Naruto: Shippuden', 'S.H.Figuarts KAKASHI HATAKE -The Legendary Hero of the Sharingan-', '2022', '16.0'),
]

class Command(BaseCommand):
    help = 'Importa as seis fichas fornecidas pelo usuário, sem duplicar modelos.'

    @transaction.atomic
    def handle(self, *args, **options):
        tipo, _ = TipoColecionavel.objects.get_or_create(nome_tipo='Action Figure')
        for personagem, franquia, nome, ano, altura in FIGURAS:
            modelo = ModeloColecionavel.objects.filter(tipo=tipo, valores_caracteristicas__caracteristica__nome_caracteristica='Nome', valores_caracteristicas__valor=nome).first()
            if modelo is None:
                modelo = ModeloColecionavel.objects.create(tipo=tipo, nome_personagem=personagem, franquia=franquia, fabricante='Bandai Spirits')
            dados = {'Origem dos dados': ('Exemplo fornecido pelo usuário', 'texto'), 'Nome': (nome, 'texto'), 'Série': ('S.H.Figuarts', 'texto'), 'Ano de lançamento': (ano, 'numero'), 'Altura (cm)': (altura, 'numero'), 'Material': ('PVC, ABS', 'texto'), 'Possui acessórios': ('true', 'boolean'), 'Possui troca de rosto': ('true', 'boolean'), 'Possui troca de mãos': ('true', 'boolean')}
            for chave, (valor, tipo_dado) in dados.items():
                caracteristica, _ = Caracteristica.objects.get_or_create(nome_caracteristica=chave, defaults={'tipo_dado': tipo_dado})
                ModeloCaracteristica.objects.update_or_create(modelo=modelo, caracteristica=caracteristica, defaults={'valor': valor})
        self.stdout.write(self.style.SUCCESS('6 fichas de action figures importadas.'))
