import base64
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


class WhatsAppVerifyError(Exception):
    pass


def _post(caminho, dados):
    if not settings.WHATSAPP_VERIFY_CONFIGURADO:
        raise WhatsAppVerifyError("A verificação por WhatsApp ainda não foi configurada pelo administrador.")
    url = f"https://verify.twilio.com/v2/Services/{settings.TWILIO_VERIFY_SERVICE_SID}/{caminho}"
    credenciais = base64.b64encode(f"{settings.TWILIO_ACCOUNT_SID}:{settings.TWILIO_AUTH_TOKEN}".encode()).decode()
    requisicao = Request(
        url,
        data=urlencode(dados).encode(),
        headers={"Authorization": f"Basic {credenciais}", "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(requisicao, timeout=15) as resposta:
            return json.loads(resposta.read().decode())
    except HTTPError as exc:
        try:
            detalhe = json.loads(exc.read().decode()).get("message", "")
        except (ValueError, UnicodeDecodeError):
            detalhe = ""
        raise WhatsAppVerifyError(detalhe or "O WhatsApp não aceitou a solicitação. Tente novamente.") from exc
    except (URLError, TimeoutError) as exc:
        raise WhatsAppVerifyError("Não foi possível contatar o serviço de verificação agora.") from exc


def enviar_codigo(telefone):
    resposta = _post("Verifications", {"To": telefone, "Channel": "whatsapp", "Locale": "pt-BR"})
    if resposta.get("status") not in {"pending", "approved"}:
        raise WhatsAppVerifyError("Não foi possível enviar o código para este número.")
    return resposta


def conferir_codigo(telefone, codigo):
    resposta = _post("VerificationCheck", {"To": telefone, "Code": codigo})
    return resposta.get("status") == "approved"
