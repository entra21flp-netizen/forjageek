from django import template

register = template.Library()

# condicao_caixa é texto livre no banco (ex: "MISB lacrado", "Aberto p/ exibição").
# Este mapeamento decide qual cor de badge usar com base em palavras-chave,
# reaproveitando exatamente as classes já definidas em componentes.css.
_REGRAS_BADGE = [
    ("misb", "badge-misb", "MISB"),
    ("lacrad", "badge-misb", "MISB"),
    ("abert", "badge-aberto", "Aberto"),
    ("loose", "badge-loose", "Loose"),
    ("avariad", "badge-avariado", "Avariado"),
]


@register.filter
def badge_classe(condicao_caixa):
    texto = (condicao_caixa or "").lower()
    for palavra_chave, classe, _ in _REGRAS_BADGE:
        if palavra_chave in texto:
            return classe
    return "badge-loose"  # fallback neutro


@register.filter
def badge_rotulo(condicao_caixa):
    texto = (condicao_caixa or "").lower()
    for palavra_chave, _, rotulo in _REGRAS_BADGE:
        if palavra_chave in texto:
            return rotulo
    return condicao_caixa


@register.filter
def negociacao_badge_classe(status_negociacao):
    return {
        "venda": "badge-misb",
        "troca": "badge-troca",
        "venda_ou_troca": "badge-troca",
        "exibicao": "badge-loose",
    }.get(status_negociacao, "badge-loose")


@register.filter
def negociacao_rotulo(status_negociacao):
    return {
        "venda": "À venda",
        "troca": "Troca",
        "venda_ou_troca": "Venda/Troca",
        "exibicao": "Exibição",
    }.get(status_negociacao, status_negociacao)
