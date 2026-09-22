from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from inventario.models import ColecionavelUsuario


class TransacaoVenda(models.Model):
    STATUS_PENDENTE = "pendente"
    STATUS_PAGO = "confirmada"
    STATUS_CONCLUIDO = "concluida"
    STATUS_CANCELADO = "cancelada"
    STATUS_CHOICES = [
        (STATUS_PENDENTE, "Pendente"),
        (STATUS_PAGO, "Pago"),
        (STATUS_CONCLUIDO, "Concluído"),
        (STATUS_CANCELADO, "Cancelado"),
    ]

    comprador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="compras",
    )
    vendedor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vendas",
    )
    # NOTA: o diagrama original tinha `colecionavel_usuario_id` como uma coluna
    # solta, sem relacionamento (Ref:) declarado. Aqui ela vira uma FK de
    # verdade com PROTECT — assim o item vendido não pode ser apagado do
    # inventário enquanto existir uma transação ligada a ele, preservando o
    # histórico financeiro.
    colecionavel_usuario = models.ForeignKey(
        ColecionavelUsuario,
        on_delete=models.PROTECT,
        related_name="transacoes",
    )

    valor_item = models.DecimalField(max_digits=20, decimal_places=2)
    taxa_plataforma = models.DecimalField(max_digits=20, decimal_places=2)
    valor_liquido_vendedor = models.DecimalField(max_digits=20, decimal_places=2)

    # registro de contato da transação — o número no momento da compra, que
    # pode ser diferente do telefone_whatsapp ATUAL do usuário (ex: usuário
    # trocou de número depois)
    whatsapp_comprador = models.CharField(
        max_length=20,
        help_text="Número de contato salvo no momento da compra",
    )
    whatsapp_vendedor = models.CharField(
        max_length=20,
        help_text="Número de contato do vendedor",
    )

    status_transacao = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default=STATUS_PENDENTE,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    concluido_em = models.DateTimeField(null=True, blank=True)
    stripe_checkout_session_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    stripe_payment_intent_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "transacoes_venda"
        verbose_name = "Transação de venda"
        verbose_name_plural = "Transações de venda"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"Venda #{self.pk} — {self.vendedor} → {self.comprador}"


class AvaliacaoVenda(models.Model):
    """Avaliação que o comprador deixa para o vendedor após a compra."""

    transacao = models.OneToOneField(
        TransacaoVenda,
        on_delete=models.PROTECT,
        related_name="avaliacao",
    )
    avaliador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="avaliacoes_feitas",
    )
    avaliado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="avaliacoes_recebidas",
    )
    nota = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Nota de 1 a 5 estrelas.",
    )
    comentario = models.TextField(blank=True, max_length=700)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "avaliacoes_venda"
        verbose_name = "Avaliação de venda"
        verbose_name_plural = "Avaliações de vendas"
        ordering = ["-criado_em"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(nota__gte=1, nota__lte=5),
                name="avaliacao_venda_nota_entre_1_e_5",
            ),
        ]

    def clean(self):
        if self.transacao_id:
            if self.avaliador_id != self.transacao.comprador_id:
                raise ValidationError("Somente o comprador pode avaliar esta venda.")
            if self.avaliado_id != self.transacao.vendedor_id:
                raise ValidationError("A avaliação deve ser destinada ao vendedor da compra.")

    def __str__(self):
        return f"{self.nota} estrelas para {self.avaliado} — venda #{self.transacao_id}"
