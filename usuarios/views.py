import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.views.decorators.http import require_http_methods

from .forms import CadastroUsuarioForm
from .models import Usuario
from .whatsapp_verify import WhatsAppVerifyError, conferir_codigo, enviar_codigo


def cadastrar_usuario(request):
    if request.user.is_authenticated:
        return redirect("core:index")

    form = CadastroUsuarioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        login(request, usuario)
        return redirect("core:verificar_whatsapp")

    return render(request, "core/cadastrar_usuario.html", {"form": form})


def recuperar_conta(request):
    """Envia um link de redefinição para o e-mail cadastrado sem expor contas."""
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        ultimo_envio = request.session.get("recuperacao_email_ultimo_envio", 0)
        restante = 60 - int(time.time() - ultimo_envio)
        if restante > 0:
            messages.warning(request, f"Aguarde {restante} segundos antes de solicitar outro link.")
        elif not settings.EMAIL_CONFIGURADO:
            messages.warning(request, "A recuperação por e-mail ainda está aguardando a configuração do servidor de e-mail.")
        else:
            candidato = Usuario.objects.filter(email__iexact=email, is_active=True).first()
            if candidato:
                uid = urlsafe_base64_encode(force_bytes(candidato.pk))
                token = default_token_generator.make_token(candidato)
                link = request.build_absolute_uri(reverse("core:redefinir_senha_email", args=[uid, token]))
                try:
                    send_mail(
                        "Redefina sua senha da ForjaGeek",
                        f"Olá, {candidato.nome}!\n\nUse o link abaixo para criar uma nova senha:\n{link}\n\nSe não foi você, ignore esta mensagem.",
                        settings.DEFAULT_FROM_EMAIL,
                        [candidato.email],
                        fail_silently=False,
                    )
                except Exception:
                    messages.error(request, "Não foi possível enviar o e-mail agora. Tente novamente em instantes.")
                else:
                    request.session["recuperacao_email_ultimo_envio"] = int(time.time())
                    request.session.modified = True
                    messages.success(request, "Se houver uma conta com esse e-mail, enviaremos um link para redefinir a senha.")
                    return redirect("core:recuperar_conta")
            else:
                messages.success(request, "Se houver uma conta com esse e-mail, enviaremos um link para redefinir a senha.")
    return render(request, "core/recuperar_conta.html")


def redefinir_senha_email(request, uidb64, token):
    try:
        usuario_id = urlsafe_base64_decode(uidb64).decode()
        usuario = Usuario.objects.get(pk=usuario_id, is_active=True)
    except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
        usuario = None
    if not usuario or not default_token_generator.check_token(usuario, token):
        messages.error(request, "Este link é inválido ou expirou. Solicite um novo e-mail de recuperação.")
        return redirect("core:recuperar_conta")
    if request.method == "POST":
        senha = request.POST.get("password1", "")
        confirmacao = request.POST.get("password2", "")
        if senha != confirmacao:
            messages.error(request, "As senhas não coincidem.")
        else:
            try:
                validate_password(senha, usuario)
            except ValidationError as exc:
                messages.error(request, " ".join(exc.messages))
            else:
                usuario.set_password(senha)
                usuario.save(update_fields=["password"])
                messages.success(request, "Senha atualizada. Entre com sua nova senha.")
                return redirect("core:login")
    return render(request, "core/redefinir_senha_email.html", {"usuario": usuario})


def _telefone_mascarado(numero):
    if len(numero) < 6:
        return numero
    return f"{numero[:3]} •••••• {numero[-4:]}"


@login_required
@require_http_methods(["GET", "POST"])
def verificar_whatsapp(request):
    if request.user.whatsapp_validado:
        return redirect("core:index")

    if request.method == "POST":
        acao = request.POST.get("acao")
        if acao == "enviar":
            ultimo_envio = request.session.get("whatsapp_otp_enviado_em", 0)
            restante = 60 - int(time.time() - ultimo_envio)
            if restante > 0:
                messages.warning(request, f"Aguarde {restante} segundos antes de solicitar outro código.")
            else:
                try:
                    enviar_codigo(request.user.telefone_whatsapp)
                    request.session["whatsapp_otp_enviado_em"] = int(time.time())
                    messages.success(request, "Código enviado pelo WhatsApp. Ele expira em poucos minutos.")
                except WhatsAppVerifyError as exc:
                    messages.error(request, str(exc))
        elif acao == "confirmar":
            codigo = request.POST.get("codigo", "").strip()
            if not codigo.isdigit() or not 4 <= len(codigo) <= 10:
                messages.error(request, "Digite o código numérico recebido no WhatsApp.")
            else:
                try:
                    if conferir_codigo(request.user.telefone_whatsapp, codigo):
                        request.user.whatsapp_validado = True
                        request.user.save(update_fields=["whatsapp_validado"])
                        request.session.pop("whatsapp_otp_enviado_em", None)
                        messages.success(request, "WhatsApp confirmado com sucesso.")
                        return redirect("core:index")
                    messages.error(request, "Código incorreto ou expirado. Confira e tente novamente.")
                except WhatsAppVerifyError as exc:
                    messages.error(request, str(exc))

    return render(request, "core/verificar_whatsapp.html", {
        "telefone_mascarado": _telefone_mascarado(request.user.telefone_whatsapp),
        "servico_configurado": settings.WHATSAPP_VERIFY_CONFIGURADO,
    })
