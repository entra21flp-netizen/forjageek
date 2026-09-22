from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils import timezone


class Usuario(AbstractUser):
    """
    Usuário da plataforma.

    Estende o AbstractUser do Django em vez de reproduzir o campo `senha`
    do diagrama original: o Django já cuida do hash seguro de senha,
    sessões de login, permissões e recuperação de senha — reimplementar
    isso na mão seria reinventar a roda (e com mais risco de segurança).

    Campos do AbstractUser que já cobrem o diagrama:
    - username  -> usamos como "login"
    - email     -> igual ao diagrama
    - password  -> substitui `senha` (guardado com hash, nunca em texto puro)
    - date_joined -> equivalente a `criado_em`

    Os campos abaixo são os que o diagrama original tinha e o Django
    não fornece de fábrica.
    """

    password = models.CharField("password", max_length=128, db_column="senha")
    last_login = models.DateTimeField("last login", blank=True, null=True)
    is_superuser = models.BooleanField("superuser status", default=False)
    username = models.CharField("username", max_length=150, unique=True, db_column="login", validators=[UnicodeUsernameValidator()])
    first_name = models.CharField("first name", max_length=150, blank=True, db_column="nome")
    last_name = models.CharField("last name", max_length=150, blank=True)
    email = models.EmailField("email address", blank=True)
    is_staff = models.BooleanField("staff status", default=False)
    is_active = models.BooleanField("active", default=True)
    date_joined = models.DateTimeField("date joined", default=timezone.now, db_column="criado_em")

    cpf = models.CharField(max_length=15, unique=True)
    telefone_whatsapp = models.CharField(
        max_length=20,
        help_text="Formato internacional, ex: +5547999999999",
    )
    whatsapp_validado = models.BooleanField(
        default=False,
        help_text="Indica se o número foi verificado via PIN/OTP",
    )
    pontos = models.IntegerField(default=0)

    # aliases só pra facilitar a leitura do código em português,
    # sem duplicar dado nenhum no banco
    @property
    def nome(self):
        return self.get_full_name() or self.username

    @property
    def login(self):
        return self.username

    @property
    def criado_em(self):
        return self.date_joined

    class Meta:
        db_table = "usuarios"
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self):
        return self.nome
