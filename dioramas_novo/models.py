from pathlib import Path

from django.conf import settings
from django.db import models

from inventario.models import ColecionavelUsuario


def caminho_diorama(instance, filename):
    extensao = Path(filename).suffix.lower() or ".png"
    return f"dioramas_novo/{instance.usuario_id}/{instance.pk or 'novo'}{extensao}"


class DioramaPresetNovo(models.Model):
    nome = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    descricao = models.CharField(max_length=300)
    imagem_preview = models.ImageField(upload_to="dioramas_novo/presets/", blank=True)
    prompt_base = models.TextField()
    ativo = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dioramas_padrao"
        ordering = ["nome"]
        verbose_name = "Diorama padrão"
        verbose_name_plural = "Dioramas padrão"

    def __str__(self):
        return self.nome


class DioramaGeradoNovo(models.Model):
    TIPO_PREDEFINIDO = "predefinido"
    TIPO_PERSONALIZADO = "personalizado"
    TIPO_CHOICES = [(TIPO_PREDEFINIDO, "Predefinido"), (TIPO_PERSONALIZADO, "Personalizado")]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dioramas_gerados_novos")
    colecionavel = models.ForeignKey(ColecionavelUsuario, on_delete=models.CASCADE, related_name="dioramas_gerados_novos")
    preset = models.ForeignKey(DioramaPresetNovo, on_delete=models.SET_NULL, null=True, blank=True, related_name="dioramas")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descricao = models.TextField(blank=True)
    imagem = models.ImageField(upload_to=caminho_diorama)
    prompt_utilizado = models.TextField()
    data_criacao = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dioramas_ia"
        ordering = ["-data_criacao"]
        verbose_name = "Diorama criado pelo usuário"
        verbose_name_plural = "Dioramas criados pelos usuários"
        indexes = [models.Index(fields=["usuario", "-data_criacao"], name="diorama_novo_usuario_idx")]

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.colecionavel.modelo}"

    @property
    def titulo(self):
        return self.preset.nome if self.preset_id else f"Diorama de {self.colecionavel.modelo.nome_personagem}"
