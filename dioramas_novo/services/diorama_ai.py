import base64
import io
import logging
import os
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.request import urlopen

from django.conf import settings
from django.core.files.base import ContentFile
from openai import APIConnectionError, APIStatusError, OpenAI, RateLimitError
from PIL import Image, ImageFilter, ImageOps

logger = logging.getLogger(__name__)


class DioramaAIError(Exception):
    pass


class DioramaAIRateLimitError(DioramaAIError):
    pass


@dataclass(frozen=True)
class ResultadoGeracao:
    token: str
    caminho: Path
    prompt: str
    modelo: str


def _imagem_colecionavel(colecionavel):
    imagem = colecionavel.imagens.filter(imagem_principal=True).first() or colecionavel.imagens.first()
    if not imagem:
        raise DioramaAIError("O colecionável precisa ter uma imagem para gerar o diorama.")
    if imagem.arquivo:
        with imagem.arquivo.open("rb") as arquivo:
            return arquivo.read(), Path(imagem.arquivo.name).suffix.lower()
    if imagem.url_imagem:
        try:
            with urlopen(imagem.url_imagem, timeout=15) as resposta:
                return resposta.read(), Path(imagem.url_imagem).suffix.lower()
        except Exception as exc:
            logger.warning("Falha ao obter imagem remota do colecionável: %s", exc)
            raise DioramaAIError("Não foi possível acessar a imagem do colecionável.") from exc
    raise DioramaAIError("O colecionável precisa ter uma imagem válida.")


@lru_cache(maxsize=1)
def _sessao_recorte():
    os.environ.setdefault("REMBG_HOME", str(Path(settings.BASE_DIR) / ".rembg"))
    from rembg import new_session
    return new_session("u2netp")


def _recortar_fundo(item):
    """Segmenta o objeto principal, inclusive em fotos com fundos complexos."""
    rgba = item.convert("RGBA")
    alpha_original = rgba.getchannel("A")
    if alpha_original.getextrema()[0] < 250:
        return rgba
    try:
        from rembg import remove

        entrada = io.BytesIO()
        rgba.save(entrada, format="PNG")
        try:
            resultado = remove(
                entrada.getvalue(),
                session=_sessao_recorte(),
                alpha_matting=True,
                alpha_matting_foreground_threshold=235,
                alpha_matting_background_threshold=15,
                alpha_matting_erode_size=8,
            )
        except Exception:
            # O alpha matting pode falhar em imagens muito escuras ou com
            # pouco contraste. A segmentação principal continua funcionando.
            logger.warning("Alpha matting falhou; repetindo recorte sem matting", exc_info=True)
            resultado = remove(
                entrada.getvalue(),
                session=_sessao_recorte(),
                alpha_matting=False,
                post_process_mask=True,
            )
        recorte = Image.open(io.BytesIO(resultado)).convert("RGBA")
        # Logos, textos e faixas podem sobreviver à segmentação como ilhas
        # separadas. Mantém somente o maior componente (a peça principal).
        import numpy as np
        from scipy import ndimage

        alpha_array = np.asarray(recorte.getchannel("A")).copy()

        # Em fotos promocionais, uma faixa pode separar as botas do corpo. Uma
        # segunda leitura da parte inferior recupera pés que o recorte global
        # classificou como desconectados.
        inicio_inferior = int(rgba.height * .76)
        inferior = rgba.crop((0, inicio_inferior, rgba.width, rgba.height))
        buffer_inferior = io.BytesIO()
        inferior.save(buffer_inferior, format="PNG")
        resultado_inferior = remove(
            buffer_inferior.getvalue(),
            session=_sessao_recorte(),
            alpha_matting=False,
            post_process_mask=True,
        )
        alpha_inferior = np.asarray(
            Image.open(io.BytesIO(resultado_inferior)).convert("RGBA").getchannel("A")
        )
        corte_faixa = int(rgba.height * .80)
        deslocamento = corte_faixa - inicio_inferior
        alpha_array[corte_faixa:, :] = np.maximum(
            alpha_array[corte_faixa:, :],
            alpha_inferior[deslocamento:, :],
        )
        mascara_base = alpha_array > 24
        mascara_aberta = ndimage.binary_opening(mascara_base, structure=np.ones((3, 3)), iterations=2)
        rotulos, quantidade = ndimage.label(mascara_aberta)
        if quantidade:
            tamanhos = ndimage.sum(mascara_aberta, rotulos, range(1, quantidade + 1))
            principal = int(np.argmax(tamanhos)) + 1
            objetos = ndimage.find_objects(rotulos)
            caixa_principal = objetos[principal - 1]
            x_min = caixa_principal[1].start
            x_max = caixa_principal[1].stop
            manter = rotulos == principal
            tamanho_principal = tamanhos[principal - 1]
            for indice, caixa in enumerate(objetos, start=1):
                if indice == principal or caixa is None:
                    continue
                largura = caixa[1].stop - caixa[1].start
                altura = caixa[0].stop - caixa[0].start
                centro_x = (caixa[1].start + caixa[1].stop) / 2
                abaixo_do_corpo = caixa[0].start >= int(rgba.height * .77)
                alinhado = x_min - largura * .25 <= centro_x <= x_max + largura * .25
                tamanho_relevante = tamanhos[indice - 1] >= tamanho_principal * .008
                nao_e_faixa = largura / max(altura, 1) < 3
                if abaixo_do_corpo and alinhado and tamanho_relevante and nao_e_faixa:
                    manter |= rotulos == indice
            mascara = ndimage.binary_dilation(manter, iterations=2) & mascara_base
            alpha_limpo = np.where(mascara, alpha_array, 0).astype(np.uint8)
            alpha_limpo = np.asarray(
                Image.fromarray(alpha_limpo, mode="L").filter(ImageFilter.GaussianBlur(.65))
            )
            recorte.putalpha(Image.fromarray(alpha_limpo, mode="L"))
    except Exception as exc:
        logger.exception("Falha ao segmentar o fundo do colecionável")
        raise DioramaAIError("Não foi possível remover o fundo da foto do colecionável.") from exc
    if recorte.getchannel("A").getbbox() is None:
        raise DioramaAIError(
            "Não foi possível identificar o colecionável na foto. Escolha uma imagem em que a peça esteja bem visível."
        )
    caixa = recorte.getbbox()
    return recorte.crop(caixa) if caixa else recorte


def compor_preset_com_colecionavel(caminho_cenario, colecionavel):
    """Monta um preset 16:9 com a foto real do item no centro do cenário."""
    imagem_bytes, _ = _imagem_colecionavel(colecionavel)
    try:
        with Image.open(caminho_cenario) as origem_cenario, Image.open(io.BytesIO(imagem_bytes)) as origem_item:
            cenario = ImageOps.fit(origem_cenario.convert("RGB"), (1600, 900), method=Image.Resampling.LANCZOS)
            item = _recortar_fundo(origem_item)
            item.thumbnail((600, 590), Image.Resampling.LANCZOS)

            # Uma sombra suave ancora visualmente a peça à base do cenário.
            sombra = Image.new("RGBA", cenario.size, (0, 0, 0, 0))
            largura_sombra = max(180, int(item.width * .72))
            altura_sombra = max(28, int(item.height * .07))
            elipse = Image.new("RGBA", (largura_sombra, altura_sombra), (0, 0, 0, 115)).filter(ImageFilter.GaussianBlur(14))
            x = (cenario.width - item.width) // 2
            # Os presets possuem a plataforma principal na região central
            # inferior. Os pés devem tocar o tampo, não o rodapé da imagem.
            ponto_contato_y = int(cenario.height * .68)
            y = max(18, ponto_contato_y - item.height)
            sombra.alpha_composite(
                elipse,
                ((cenario.width - largura_sombra) // 2, ponto_contato_y - altura_sombra // 2),
            )

            composicao = cenario.convert("RGBA")
            composicao = Image.alpha_composite(composicao, sombra)
            composicao.alpha_composite(item, (x, y))

            saida = io.BytesIO()
            composicao.convert("RGB").save(saida, format="JPEG", quality=92, optimize=True)
            return ContentFile(saida.getvalue(), name="diorama-predefinido.jpg")
    except (OSError, ValueError) as exc:
        raise DioramaAIError("Não foi possível combinar a foto do colecionável com o cenário.") from exc


def montar_prompt(colecionavel, descricao, preset=None):
    modelo = colecionavel.modelo
    cenario = preset.prompt_base if preset else descricao
    return f"""Create a wide cinematic physical collectible diorama using the provided collectible reference image.

IMPORTANT OUTPUT COMPOSITION:
- Use a wide horizontal composition suitable for an approximately 16:9 display area.
- Place the collectible approximately at the horizontal center. The environment must extend naturally to both left and right.
- Keep the collectible visually dominant and large enough to remain recognizable as a full-width shelf banner.

Use the supplied collectible as the main subject. Preserve its appearance, colors, accessories, proportions and important visual characteristics.

CRITICAL PHYSICAL COMPOSITION:
- The collectible must be physically standing or resting on the UPPER SURFACE of the diorama base.
- Its lowest contact points (feet, wheels, supports or underside) must make believable contact with the base.
- It must NOT float, sink into the base, intersect it incorrectly, stand behind it, or look pasted over a background.
- Generate realistic contact shadows and ambient occlusion directly underneath the contact points.
- Perspective, scale and lighting direction must be coherent across collectible, base and environment.
- Keep the collectible predominantly inside the central safe area, about 55% to 70% of the useful height when appropriate for its shape.
- Keep head, feet, wheels, accessories and other important parts visible and away from crop edges.
- The lower image must contain a clearly visible physical display base connected naturally to the environment.
- The result must look like ONE physical miniature diorama photographed professionally.
- It will be displayed in a compact shelf slot with object-fit cover; keep essential elements inside the central safe area.

Collectible: {modelo.nome_modelo or modelo.nome_personagem}.
Character/object: {modelo.nome_personagem}. Franchise: {modelo.franquia}. Category: {modelo.tipo.nome_tipo}.
USER REQUESTED ENVIRONMENT: {cenario}
Additional user details: {descricao or 'None.'}

Use realistic contact shadows, ambient occlusion, perspective, scale, environmental lighting, depth and physical materials. Do not add random text, logos, watermarks or unrelated characters."""


def _imagem_para_openai(imagem_bytes):
    """Envia um PNG válido, sem depender da extensão do upload original."""
    try:
        with Image.open(io.BytesIO(imagem_bytes)) as origem:
            imagem = ImageOps.exif_transpose(origem)
            imagem.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
            saida = io.BytesIO()
            imagem.convert("RGBA" if "A" in imagem.getbands() else "RGB").save(saida, format="PNG")
    except (OSError, ValueError) as exc:
        raise DioramaAIError("A foto do colecionável não é uma imagem válida. Envie outra foto.") from exc
    saida.seek(0)
    saida.name = "colecionavel.png"
    return saida


def _mensagem_erro_openai(exc):
    detalhe = exc.body if isinstance(exc.body, dict) else {}
    erro = detalhe.get("error", detalhe)
    if not isinstance(erro, dict):
        erro = {}
    codigo = str(erro.get("code") or "").lower()
    parametro = str(erro.get("param") or "").lower()
    mensagem = str(erro.get("message") or "")
    logger.warning(
        "OpenAI recusou diorama: status=%s codigo=%s parametro=%s mensagem=%s",
        exc.status_code, codigo, parametro, mensagem[:500],
    )
    if exc.status_code == 401:
        return "A chave OPENAI_API_KEY é inválida. Verifique a configuração."
    if exc.status_code == 403:
        return "Este projeto OpenAI não tem acesso ao modelo de imagens configurado."
    if any(termo in codigo or termo in mensagem.lower() for termo in ("safety", "content_policy", "moderation")):
        return "A OpenAI bloqueou esta geração pela moderação de conteúdo. Tente outra foto ou descrição."
    if parametro in {"image", "image[]", "images"} or "invalid_image" in codigo:
        return "A OpenAI não aceitou a foto do colecionável. Envie outra imagem PNG ou JPG."
    if parametro in {"size", "quality", "input_fidelity", "output_format"}:
        return f"A OpenAI não aceitou o parâmetro '{parametro}' para este modelo."
    if parametro == "model":
        return "O modelo de imagens configurado não está disponível para esta chave. Verifique OPENAI_IMAGE_MODEL."
    if exc.status_code == 400:
        return "A OpenAI recusou a solicitação. Veja o motivo específico no terminal do servidor."
    return "Não foi possível gerar o diorama neste momento. Tente novamente mais tarde."


def mensagem_limite_openai(exc):
    """Distingue erros de cobrança de limites de ritmo (ambos usam HTTP 429)."""
    detalhe = exc.body if isinstance(exc.body, dict) else {}
    erro = detalhe.get("error", detalhe)
    if not isinstance(erro, dict):
        erro = {}
    codigo = str(erro.get("code") or "").lower()
    tipo = str(erro.get("type") or "").lower()
    logger.warning("OpenAI limite diorama: codigo=%s tipo=%s", codigo, tipo)
    if codigo == "credit_balance_exhausted" or (tipo == "insufficient_quota" and not codigo):
        return "Os créditos da API OpenAI acabaram ou não estão disponíveis neste projeto. Verifique o faturamento na plataforma OpenAI."
    if codigo in {"organization_spend_limit_exceeded", "project_spend_limit_exceeded"}:
        return "O limite de gastos da API OpenAI foi atingido. Verifique o limite do projeto ou da organização na plataforma OpenAI."
    if codigo == "organization_usage_limit_exceeded":
        return "O limite de uso da organização OpenAI foi atingido. Verifique os limites da conta na plataforma OpenAI."
    return "Limite temporário de solicitações à OpenAI. Aguarde e tente novamente."


def gerar_diorama(colecionavel, descricao, usuario_id, preset=None):
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        raise DioramaAIError("Configure OPENAI_API_KEY no arquivo .env para gerar dioramas com IA.")
    imagem_bytes, _ = _imagem_colecionavel(colecionavel)
    prompt = montar_prompt(colecionavel, descricao, preset)
    modelo = getattr(settings, "OPENAI_IMAGE_MODEL", "gpt-image-2.5-flare")
    arquivo_entrada = _imagem_para_openai(imagem_bytes)
    try:
        # O endpoint de edição usa a foto real como referência do colecionável.
        client = OpenAI(api_key=api_key, timeout=120.0, max_retries=1)
        resposta = client.images.edit(
            model=modelo,
            image=arquivo_entrada,
            prompt=prompt,
            size="1536x864",
            quality="medium",
            output_format="png",
        )
        imagem_gerada = resposta.data[0].b64_json if resposta.data else None
        if not imagem_gerada:
            raise DioramaAIError("A OpenAI não retornou uma imagem.")
        saida = base64.b64decode(imagem_gerada)
    except DioramaAIError:
        raise
    except RateLimitError as exc:
        raise DioramaAIRateLimitError(mensagem_limite_openai(exc)) from exc
    except APIStatusError as exc:
        raise DioramaAIError(_mensagem_erro_openai(exc)) from exc
    except (APIConnectionError, ValueError) as exc:
        logger.warning("Falha de comunicação ou resposta OpenAI ao gerar diorama: %s", type(exc).__name__)
        raise DioramaAIError("Não foi possível concluir a geração do diorama. Tente novamente mais tarde.") from exc
    token = uuid.uuid4().hex
    pasta = Path(settings.MEDIA_ROOT) / "diorama_previews_novo" / str(usuario_id)
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{token}.png"
    caminho.write_bytes(saida)
    return ResultadoGeracao(token=token, caminho=caminho, prompt=prompt, modelo=modelo)


def caminho_preview(usuario_id, token):
    if not token or len(token) != 32 or any(c not in "0123456789abcdef" for c in token):
        return None
    return Path(settings.MEDIA_ROOT) / "diorama_previews_novo" / str(usuario_id) / f"{token}.png"
