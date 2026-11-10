# Analisador Caveira - Copyright (c) 2026 Hiagor Franklin. Todos os direitos reservados.
# Código proprietário: proibido copiar, modificar ou distribuir sem autorização. Veja LICENSE.
"""Marcas muito imitadas em golpes e a comparação de nomes parecidos."""

MARCAS = (
    "paypal", "google", "gmail", "facebook", "instagram", "whatsapp",
    "amazon", "microsoft", "outlook", "apple", "icloud", "netflix",
    "nubank", "itau", "bradesco", "santander", "caixa", "bancodobrasil",
    "picpay", "mercadolivre", "mercadopago", "magalu", "shopee",
    "correios", "serasa", "receita", "gov",
)

# Trocas que golpistas usam para enganar o olho: rn -> m, 0 -> o, 1 -> l...
TROCAS_VISUAIS = (("rn", "m"), ("vv", "w"), ("0", "o"), ("1", "l"), ("3", "e"), ("5", "s"), ("@", "a"))


def quantas_diferencas(a: str, b: str) -> int:
    """Conta quantas letras precisam mudar para transformar `a` em `b`
    (inserir, apagar ou trocar uma letra conta 1)."""
    if len(a) < len(b):
        a, b = b, a
    linha = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        nova = [i]
        for j, cb in enumerate(b, 1):
            nova.append(min(linha[j] + 1, nova[j - 1] + 1, linha[j - 1] + (ca != cb)))
        linha = nova
    return linha[-1]


def desfazer_truques(nome: str) -> str:
    nome = nome.lower().replace("-", "")
    for falso, real in TROCAS_VISUAIS:
        nome = nome.replace(falso, real)
    return nome


def imita_marca(nome: str):
    """Devolve a marca que `nome` parece imitar, ou None.
    O nome exatamente igual à marca NÃO conta (é o site verdadeiro)."""
    nome = (nome or "").lower()
    if not nome or nome in MARCAS:
        return None
    # Testa o nome inteiro e cada pedaço separado por hífen
    # ("paypa1-login" -> "paypa1-login", "paypa1", "login").
    candidatos = [nome] + [p for p in nome.split("-") if p] if "-" in nome else [nome]
    for marca in MARCAS:
        if len(marca) < 4:
            continue  # nomes curtos geram muito alarme falso
        # Quanto maior a marca, mais letras diferentes toleramos.
        if len(marca) >= 8:
            tolerancia = 2
        elif len(marca) >= 6:
            tolerancia = 1
        else:
            tolerancia = 0
        for candidato in candidatos:
            limpo = desfazer_truques(candidato)
            if limpo == marca:
                return marca  # ex.: "paypa1" vira "paypal", "nubank-seguro" tem "nubank"
            if tolerancia and quantas_diferencas(limpo, marca) <= tolerancia:
                return marca
    return None
