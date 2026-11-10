# Analisador Caveira - Copyright (c) 2026 Hiagor Franklin. Licença MIT (veja LICENSE).
"""Regras que olham só o texto da URL (não precisam de internet)."""

import re

from .dominio import eh_ip
from .marcas import MARCAS, imita_marca

ENCURTADORES = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "ow.ly", "cutt.ly",
    "rebrand.ly", "shorturl.at", "tiny.cc", "rb.gy", "encurtador.com.br", "s.id",
}

TLDS_SUSPEITOS = {
    "zip", "mov", "xyz", "top", "click", "link", "work", "rest", "gq", "tk",
    "ml", "cf", "ga", "buzz", "cam", "country", "kim", "loan", "monster",
    "online", "site", "support", "icu", "live", "shop",
}

PALAVRAS_ISCA = (
    "login", "signin", "entrar", "senha", "password", "verificar", "verify",
    "confirmar", "atualizar", "update", "seguranca", "security", "conta",
    "account", "desbloquear", "unlock", "premio", "resgate", "token", "pix",
)


def sinais_da_url(info: dict) -> list:
    """Recebe o resultado de separar_url() e devolve [(motivo, pontos), ...]."""
    sinais = []
    host = info["host"]

    if eh_ip(host):
        sinais.append(("O endereço é um número de IP em vez de um nome de site", 30))

    if "@" in info["netloc"]:
        sinais.append(("Tem '@' no endereço: tudo antes dele é ignorado e esconde o destino real", 25))

    if host.startswith("xn--") or ".xn--" in host:
        sinais.append(("Domínio com letras especiais (punycode), que podem imitar outras letras", 25))

    qtd_sub = len(info["subdominio"].split(".")) if info["subdominio"] else 0
    if qtd_sub >= 3:
        sinais.append((f"Muitos subdomínios encadeados ({qtd_sub})", 20))

    if info["dominio_principal"] in ENCURTADORES:
        sinais.append(("Link encurtado: não dá para ver para onde ele leva", 15))

    if info["tld"] in TLDS_SUSPEITOS:
        sinais.append((f"Terminação '.{info['tld']}' é muito usada em golpes", 10))

    if info["esquema"] == "http":
        sinais.append(("Sem HTTPS: a conexão não é criptografada", 10))

    if len(info["url"]) > 80:
        sinais.append(("URL muito comprida, pode estar escondendo o destino", 10))

    if info["nome"].count("-") >= 2:
        sinais.append(("Nome do site cheio de hífens, comum em sites falsos", 10))

    marca = imita_marca(info["nome"])
    if marca:
        sinais.append((f"O nome lembra a marca '{marca}' sem ser o site oficial (typosquatting)", 35))
    else:
        # Marca no subdomínio: paypal.conta-segura.com NÃO é o PayPal.
        partes_sub = re.split(r"[.\-]", info["subdominio"])
        for marca in MARCAS:
            if len(marca) >= 4 and marca in partes_sub and info["nome"] != marca:
                sinais.append((f"Usa '{marca}' no começo do endereço, mas o site é {info['dominio_principal']}", 30))
                break

    resto = (info["caminho"] + "?" + info["consulta"]).lower()
    iscas = [p for p in PALAVRAS_ISCA if p in resto]
    if iscas:
        sinais.append((f"Palavras de isca no link: {', '.join(iscas[:3])}", 5))

    return sinais
