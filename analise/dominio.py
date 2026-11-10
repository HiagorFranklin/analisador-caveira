# Analisador Caveira - Copyright (c) 2026 Hiagor Franklin. Todos os direitos reservados.
# Código proprietário: proibido copiar, modificar ou distribuir sem autorização. Veja LICENSE.
"""Separa uma URL em pedaços úteis (esquema, host, domínio principal...)."""

import ipaddress
from urllib.parse import urlsplit

# Sufixos com duas partes. Sem esta lista, "banco.com.br" viraria "com.br".
SUFIXOS_COMPOSTOS = {
    "com.br", "net.br", "org.br", "gov.br", "edu.br", "art.br", "blog.br",
    "app.br", "dev.br", "eco.br", "emp.br", "ind.br", "inf.br", "jus.br",
    "leg.br", "mil.br", "nom.br", "tv.br", "seg.br", "srv.br", "tur.br",
    "co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "net.au", "co.jp",
    "com.ar", "com.mx", "co.in", "com.pt", "co.za", "com.co", "com.cn",
}


def eh_ip(texto: str) -> bool:
    try:
        ipaddress.ip_address(texto.strip("[]"))
        return True
    except ValueError:
        return False


def separar_url(url: str) -> dict:
    """Recebe um texto de URL e devolve um dicionário com as partes."""
    url = (url or "").strip()
    if not url:
        raise ValueError("Digite uma URL para analisar.")
    if len(url) > 2048:
        raise ValueError("URL grande demais (máximo de 2048 caracteres).")

    # Se a pessoa digitar só "site.com", tratamos como http://site.com
    if "://" not in url:
        url = "http://" + url

    partes = urlsplit(url)
    host = (partes.hostname or "").rstrip(".").lower()
    if not host:
        raise ValueError("Não encontrei o endereço do site nessa URL.")

    if eh_ip(host):
        return {
            "url": url, "esquema": partes.scheme.lower(), "netloc": partes.netloc,
            "host": host, "subdominio": "", "nome": host, "tld": "",
            "dominio_principal": host, "caminho": partes.path, "consulta": partes.query,
        }

    pedacos = host.split(".")
    if len(pedacos) >= 3 and ".".join(pedacos[-2:]) in SUFIXOS_COMPOSTOS:
        tld = ".".join(pedacos[-2:])
        resto = pedacos[:-2]
    elif len(pedacos) >= 2:
        tld = pedacos[-1]
        resto = pedacos[:-1]
    else:
        tld = ""
        resto = pedacos

    nome = resto[-1] if resto else ""
    subdominio = ".".join(resto[:-1])
    principal = f"{nome}.{tld}" if tld else nome

    return {
        "url": url,
        "esquema": partes.scheme.lower(),
        "netloc": partes.netloc,
        "host": host,
        "subdominio": subdominio,
        "nome": nome,
        "tld": tld,
        "dominio_principal": principal,
        "caminho": partes.path,
        "consulta": partes.query,
    }
