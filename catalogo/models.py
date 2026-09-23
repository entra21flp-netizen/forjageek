from django.db import models


class TipoColecionavel(models.Model):
    nome_tipo = models.CharField(
        max_length=100,
        unique=True,
        help_text="Ex: Action Figure, Model Kit, Funko Pop, Estátua",
    )

    class Meta:
        db_table = "catalogo_tipocolecionavel"
        verbose_name = "Tipo de colecionável"
        verbose_name_plural = "Tipos de colecionáveis"
        ordering = ["nome_tipo"]

    def __str__(self):
        return self.nome_tipo


class ModeloColecionavel(models.Model):
    """Catálogo geral e imutável — o "produto" em si, não a unidade física de ninguém."""

    nome_modelo = models.CharField(max_length=255, blank=True)
    tipo = models.ForeignKey(
        TipoColecionavel,
        on_delete=models.PROTECT,
        related_name="modelos",
    )
    nome_personagem = models.CharField(max_length=255)
    franquia = models.CharField(max_length=255)
    fabricante = models.CharField(max_length=255)
    codigo_barras_ean_jan = models.CharField(
        max_length=13,
        unique=True,
        null=True,
        blank=True,
        help_text="Código EAN-13, JAN ou UPC impresso na caixa",
    )
    codigo_fabricante_sku = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Código interno da marca (ex: BAN5061234, #42)",
    )

    class Meta:
        db_table = "catalogo_modelocolecionavel"
        verbose_name = "Modelo de colecionável"
        verbose_name_plural = "Catálogo de modelos"
        ordering = ["franquia", "nome_personagem"]

    def __str__(self):
        return self.nome_modelo or f"{self.nome_personagem} — {self.franquia}"


class Caracteristica(models.Model):
    """Define os TIPOS de característica que um modelo pode ter (Escala, Grade, Altura...)."""

    TIPO_DADO_TEXTO = "texto"
    TIPO_DADO_NUMERO = "numero"
    TIPO_DADO_BOOLEAN = "boolean"
    TIPO_DADO_CHOICES = [
        (TIPO_DADO_TEXTO, "Texto"),
        (TIPO_DADO_NUMERO, "Número"),
        (TIPO_DADO_BOOLEAN, "Sim/Não"),
    ]

    tipos = models.ManyToManyField(TipoColecionavel, related_name='caracteristicas', blank=True, db_table='catalogo_caracteristica_tipos')
    nome_caracteristica = models.CharField(
        max_length=100,
        unique=True,
        help_text="Ex: Escala, Grau/Grade, Pontos de Articulação, Altura (cm), Possui LED",
    )
    tipo_dado = models.CharField(
        max_length=20,
        choices=TIPO_DADO_CHOICES,
        default=TIPO_DADO_TEXTO,
    )

    class Meta:
        db_table = "catalogo_caracteristica"
        verbose_name = "Característica"
        verbose_name_plural = "Características"
        ordering = ["nome_caracteristica"]

    def __str__(self):
        return self.nome_caracteristica


class ModeloCaracteristica(models.Model):
    """Valor de uma característica para um modelo específico (o padrão EAV do diagrama)."""

    modelo = models.ForeignKey(
        ModeloColecionavel,
        on_delete=models.CASCADE,
        related_name="valores_caracteristicas",
    )
    caracteristica = models.ForeignKey(
        Caracteristica,
        on_delete=models.CASCADE,
        related_name="valores",
    )
    valor = models.CharField(
        max_length=255,
        help_text="Ex: 1/144, RG, 16, true, Polystone",
    )

    class Meta:
        db_table = "catalogo_modelocaracteristica"
        verbose_name = "Característica do modelo"
        verbose_name_plural = "Características dos modelos"
        constraints = [
            models.UniqueConstraint(
                fields=["modelo", "caracteristica"],
                name="uniq_modelo_caracteristica",
            )
        ]

    def __str__(self):
        return f"{self.modelo} · {self.caracteristica}: {self.valor}"


class ImagemModelo(models.Model):
    modelo = models.ForeignKey(ModeloColecionavel, on_delete=models.CASCADE, related_name='imagens')
    url_imagem = models.URLField(max_length=500)
    ordem_exibicao = models.IntegerField(default=0)
    imagem_principal = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "catalogo_imagemmodelo"
        ordering = ['ordem_exibicao', 'pk']
        constraints = [models.UniqueConstraint(fields=['modelo'], condition=models.Q(imagem_principal=True), name='unica_principal_catalogo')]
