from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from catalogo.models import ModeloColecionavel


class ColecionavelUsuario(models.Model):
    """Uma unidade física específica que um usuário possui (não o modelo em si)."""

    PRIVACIDADE_PUBLICO = "publico"
    PRIVACIDADE_PRIVADO = "privado"
    PRIVACIDADE_APENAS_LINK = "apenas_link"
    PRIVACIDADE_CHOICES = [
        (PRIVACIDADE_PUBLICO, "Público"),
        (PRIVACIDADE_PRIVADO, "Privado"),
        (PRIVACIDADE_APENAS_LINK, "Apenas com link"),
    ]

    NEGOCIACAO_EXIBICAO = "exibicao"
    NEGOCIACAO_VENDA = "venda"
    NEGOCIACAO_TROCA = "troca"
    NEGOCIACAO_VENDA_OU_TROCA = "venda_ou_troca"
    NEGOCIACAO_CHOICES = [
        (NEGOCIACAO_EXIBICAO, "Só exibição"),
        (NEGOCIACAO_VENDA, "À venda"),
        (NEGOCIACAO_TROCA, "Para troca"),
        (NEGOCIACAO_VENDA_OU_TROCA, "Venda ou troca"),
    ]

    nome_personalizado = models.CharField(max_length=255, blank=True)
    personalizado = models.BooleanField(default=False)
    estado_peca = models.CharField(max_length=50, default='Não informado')
    nota = models.TextField(blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="colecionaveis",
    )
    modelo = models.ForeignKey(
        ModeloColecionavel,
        on_delete=models.PROTECT,
        related_name="unidades",
    )
    condicao_caixa = models.CharField(
        max_length=255,
        help_text="Ex: MISB lacrado, Aberto p/ exibição, Loose, Caixa avariada",
    )
    data_inclusao = models.DateTimeField(auto_now_add=True)
    preco_pago = models.DecimalField(max_digits=20, decimal_places=2)
    local_armazenamento = models.CharField(max_length=255, blank=True, null=True)

    status_privacidade = models.CharField(
        max_length=20,
        choices=PRIVACIDADE_CHOICES,
        default=PRIVACIDADE_PUBLICO,
    )

    status_negociacao = models.CharField(
        max_length=20,
        choices=NEGOCIACAO_CHOICES,
        default=NEGOCIACAO_EXIBICAO,
    )
    preco_anunciado = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Preço solicitado (obrigatório se estiver à venda)",
    )
    interesses_troca = models.TextField(
        blank=True,
        null=True,
        help_text="Descrição opcional dos itens de interesse para troca",
    )

    class Meta:
        db_table = "colecionaveis_usuario"
        verbose_name = "Colecionável do usuário"
        verbose_name_plural = "Colecionáveis dos usuários"
        ordering = ["-data_inclusao"]

    def __str__(self):
        return f"{self.modelo} de {self.usuario}"

    def esta_anunciado(self):
        return self.status_negociacao != self.NEGOCIACAO_EXIBICAO


class EstanteVirtual(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="estantes",
    )
    nome_estante = models.CharField(max_length=255)
    status_privacidade = models.CharField(max_length=50, default="privado")
    ordem_exibicao = models.IntegerField(default=0)
    tema_visual = models.CharField(max_length=100, default="padrao")
    quantidade_dioramas = models.PositiveSmallIntegerField(default=1)
    diorama_destaque = models.PositiveSmallIntegerField(default=1)

    class Meta:
        db_table = "estantes_virtuais"
        verbose_name = "Estante virtual"
        verbose_name_plural = "Estantes virtuais"
        ordering = ["usuario", "ordem_exibicao"]

    def __str__(self):
        return f"{self.nome_estante} de {self.usuario}"


class AvaliacaoEstante(models.Model):
    """Avaliação comunitária de uma estante pública."""

    estante = models.ForeignKey(
        EstanteVirtual,
        on_delete=models.CASCADE,
        related_name="avaliacoes",
    )
    avaliador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="avaliacoes_estante_feitas",
    )
    nota = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Nota de 1 a 5 estrelas.",
    )
    comentario = models.TextField(blank=True, max_length=500)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "avaliacoes_estantes"
        verbose_name = "Avaliação de estante"
        verbose_name_plural = "Avaliações de estantes"
        ordering = ["-criado_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["estante", "avaliador"],
                name="uniq_avaliacao_por_usuario_estante",
            ),
            models.CheckConstraint(
                condition=models.Q(nota__gte=1, nota__lte=5),
                name="avaliacao_estante_nota_entre_1_e_5",
            ),
        ]

    def clean(self):
        if self.estante_id and self.avaliador_id == self.estante.usuario_id:
            raise ValidationError("Você não pode avaliar a própria estante.")

    def __str__(self):
        return f"{self.nota} estrelas para {self.estante}"


class Diorama(models.Model):
    """Cenário de uma das três prateleiras (fileiras) da estante virtual."""
    estante = models.ForeignKey(EstanteVirtual, on_delete=models.CASCADE, related_name="dioramas")
    titulo = models.CharField(max_length=100, default="Meu diorama")
    descricao = models.CharField(max_length=180, blank=True)
    ordem = models.PositiveSmallIntegerField()
    configurado = models.BooleanField(default=False)

    class Meta:
        db_table = "dioramas_ia"
        ordering = ["ordem"]
        constraints = [models.UniqueConstraint(fields=["estante", "ordem"], name="uniq_diorama_por_posicao")]

    def __str__(self):
        return f"{self.titulo} ({self.estante})"


class ItemEstante(models.Model):
    estante = models.ForeignKey(
        EstanteVirtual,
        on_delete=models.CASCADE,
        related_name="itens",
    )
    colecionavel_usuario = models.OneToOneField(
        ColecionavelUsuario,
        on_delete=models.CASCADE,
        related_name="posicionamento",
        help_text="OneToOne: garante que o item fique em apenas 1 slot, como no diagrama original",
    )
    posicao_slot = models.IntegerField(null=True, blank=True)
    data_posicionamento = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "itens_estante"
        verbose_name = "Item da estante"
        verbose_name_plural = "Itens das estantes"
        ordering = ["estante", "posicao_slot"]

    def __str__(self):
        return f"{self.colecionavel_usuario} em {self.estante}"


class ImagemColecionavel(models.Model):
    arquivo = models.ImageField(upload_to='colecionaveis/%Y/%m/', blank=True)
    colecionavel_usuario = models.ForeignKey(ColecionavelUsuario, on_delete=models.CASCADE, related_name='imagens')
    url_imagem = models.URLField(max_length=500)
    ordem_exibicao = models.IntegerField(default=0)
    imagem_principal = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "imagens_colecionaveis"
        ordering = ['ordem_exibicao', 'pk']
        constraints = [models.UniqueConstraint(fields=['colecionavel_usuario'], condition=models.Q(imagem_principal=True), name='unica_principal_inventario')]


class ItemWishlist(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="itens_wishlist",
    )
    colecionavel_usuario = models.ForeignKey(
        ColecionavelUsuario,
        on_delete=models.CASCADE,
        related_name="salvo_por",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "wishlist_itens"
        ordering = ["-criado_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "colecionavel_usuario"],
                name="uniq_wishlist_usuario_item",
            )
        ]
