import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ConsultaCodigoBarrasIndisponivel(Exception):
    pass


def _primeiro_texto(valor):
    if isinstance(valor, str):
        return valor.strip()
    if isinstance(valor, list):
        return next((str(item).strip() for item in valor if str(item).strip()), "")
    return ""


def consultar_upcitemdb(codigo):
    """Consulta somente os dados publicados pelo provedor; não grava nada no banco."""
    chave = os.getenv("UPCITEMDB_USER_KEY", "").strip()
    if chave:
        requisicao = Request(
            "https://api.upcitemdb.com/prod/v1/lookup",
            data=json.dumps({"upc": codigo}).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "key_type": "3scale",
                "user_key": chave,
            },
            method="POST",
        )
    else:
        parametros = urlencode({"upc": codigo})
        requisicao = Request(
            f"https://api.upcitemdb.com/prod/trial/lookup?{parametros}",
            headers={"Accept": "application/json", "User-Agent": "ForjaGeek/1.0"},
        )

    try:
        with urlopen(requisicao, timeout=8) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            return None
        if exc.code == 429:
            raise ConsultaCodigoBarrasIndisponivel(
                "O limite de consultas foi atingido. Tente novamente mais tarde."
            ) from exc
        raise ConsultaCodigoBarrasIndisponivel(
            "A consulta de código de barras está temporariamente indisponível."
        ) from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ConsultaCodigoBarrasIndisponivel(
            "A consulta de código de barras está temporariamente indisponível."
        ) from exc

    itens = dados.get("items") or []
    if not itens:
        return None

    item = itens[0]
    return {
        "nome_modelo": _primeiro_texto(item.get("title")),
        "fabricante": _primeiro_texto(item.get("brand")),
        "categoria_origem": _primeiro_texto(item.get("category")),
        "imagem_modelo": _primeiro_texto(item.get("images")),
        "codigo_barras_ean_jan": codigo,
    }
