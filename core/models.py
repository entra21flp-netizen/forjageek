from django.conf import settings
from django.db import models

from inventario.models import ColecionavelUsuario


class Conversa(models.Model):
    iniciado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversas_iniciadas")
    destinatario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversas_recebidas")
    colecionavel = models.ForeignKey(ColecionavelUsuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="conversas")
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "conversas"
        ordering = ["-atualizada_em"]
        constraints = [models.UniqueConstraint(fields=["iniciado_por", "destinatario", "colecionavel"], name="uniq_conversa_anuncio")]


class Mensagem(models.Model):
    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name="mensagens")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mensagens_enviadas")
    texto = models.TextField()
    enviada_em = models.DateTimeField(auto_now_add=True)
    lida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mensagens"
        ordering = ["enviada_em"]
