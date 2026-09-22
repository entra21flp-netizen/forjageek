import json
import os
import time

try:
    from google import genai
    from google.genai import errors, types
except ImportError:
    genai = None
    errors = None
    types = None


ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "tipo_colecionavel": {"type": "string", "enum": ["action_figure", "estatua", "funko_pop", "busto", "diorama", "figura_de_vinil", "outro_colecionavel", "indeterminado"]},
        "altura_estimada": {"type": "string"},
        "referencia_de_escala": {"type": "string"},
        "identificacao": {"type": "string"},
        "fabricante": {"type": "string"},
        "codigo_produto": {"type": "string"},
        "altura_fabricante": {"type": "string"},
        "peso_fabricante": {"type": "string"},
        "fonte_especificacoes": {"type": "string"},
        "tem_caixa": {"type": "string", "enum": ["sim", "nao", "nao_e_possivel_confirmar"]},
        "pecas_faltando_visiveis": {"type": "array", "items": {"type": "string"}},
        "avarias_visiveis": {"type": "array", "items": {"type": "string"}},
        "estado_geral": {"type": "string", "enum": ["novo", "excelente", "bom", "regular", "danificado", "indeterminado"]},
        "confianca": {"type": "integer", "minimum": 0, "maximum": 100},
        "observacoes": {"type": "string"},
        "fotos_recomendadas": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["tipo_colecionavel", "altura_estimada", "referencia_de_escala", "identificacao", "fabricante", "codigo_produto", "altura_fabricante", "peso_fabricante", "fonte_especificacoes", "tem_caixa", "pecas_faltando_visiveis", "avarias_visiveis", "estado_geral", "confianca", "observacoes", "fotos_recomendadas"],
}

PROMPT = """Você é especialista cuidadoso em colecionáveis. Analise APENAS o que é visível nas fotos, entendendo que elas mostram ângulos, embalagem ou código de barras do mesmo item. Classifique o tipo sem supor que todo boneco é action figure. Só estime altura quando houver referência de escala confiável e visível. Identifique personagem ou linha somente quando houver evidência. Leia códigos apenas quando estiverem nítidos. Avalie caixa, peças faltantes visíveis, avarias e estado considerando o conjunto de imagens. Não afirme que uma peça está faltando se ela puder estar fora do enquadramento. Não autentique e não invente ano, edição, raridade, preço ou valor de mercado. Quando houver código informado ou legível, pesquise a ficha técnica e preencha altura, peso e fonte somente quando confirmados. Responda em português brasileiro."""


def analisar_imagens(uploads, codigo_produto=""):
    if genai is None or types is None:
        raise ValueError("O recurso de IA ainda não foi instalado neste ambiente.")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("A chave do analisador Gemini não foi configurada no servidor.")

    partes = [PROMPT]
    if codigo_produto:
        partes.append(f"Código do produto informado pelo usuário: {codigo_produto}.")
    for upload in uploads:
        partes.append(types.Part.from_bytes(data=upload.read(), mime_type=upload.content_type))
    client = genai.Client(api_key=api_key)

    for tentativa in range(3):
        try:
            resposta = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
                contents=partes,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ANALYSIS_SCHEMA,
                    temperature=0.1,
                    tools=[types.Tool(google_search=types.GoogleSearch())] if codigo_produto else None,
                ),
            )
            return json.loads(resposta.text)
        except errors.ServerError as exc:
            if exc.code != 503 or tentativa == 2:
                raise ValueError("O Gemini está temporariamente indisponível. Tente novamente em instantes.") from exc
            time.sleep(2 ** tentativa)
        except errors.ClientError as exc:
            if exc.code in (401, 403):
                raise ValueError(
                    "A chave do Gemini foi recusada. Configure uma chave de API válida do Google AI Studio no servidor."
                ) from exc
            if exc.code == 429:
                raise ValueError("O limite de análises do Gemini foi atingido. Aguarde e tente novamente.") from exc
            raise
