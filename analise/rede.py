# Analisador Caveira - Copyright (c) 2026 Hiagor Franklin. Licença MIT (veja LICENSE).
"""Verificações que precisam de internet: idade do domínio, certificado SSL
e para onde o link redireciona.

Proteção: antes de conectar em qualquer endereço, conferimos se ele NÃO
aponta para a sua rede interna (roteador, 127.0.0.1, 192.168.x.x...). Sem isso,
alguém poderia usar o analisador para espiar a sua rede (ataque SSRF).
"""

import http.client
import ipaddress
import json
import socket
import ssl
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

from .dominio import eh_ip, separar_url
from .marcas import imita_marca

TEMPO_LIMITE = 5  # segundos
MAX_SALTOS = 5


class EnderecoProibido(ValueError):
    pass


def conferir_endereco_publico(host: str) -> None:
    """Dá erro se o host resolver para um IP interno/reservado."""
    try:
        respostas = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise EnderecoProibido("O domínio não existe ou não foi encontrado.")
    for resposta in respostas:
        ip = ipaddress.ip_address(resposta[4][0].split("%")[0])
        if ip.version == 6 and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if not ip.is_global or ip.is_multicast:
            raise EnderecoProibido("Esse endereço aponta para uma rede interna; não vou acessá-lo.")


# ---------------------------------------------------------------- idade (RDAP)
def data_de_registro(dominio: str):
    """Consulta o RDAP (o 'WHOIS moderno', em JSON) para saber quando o
    domínio foi registrado. Devolve datetime ou None."""
    if not dominio or eh_ip(dominio) or "." not in dominio:
        return None
    try:
        pedido = urllib.request.Request(
            f"https://rdap.org/domain/{dominio}",
            headers={"Accept": "application/rdap+json", "User-Agent": "analisador-caveira/1.0"},
        )
        with urllib.request.urlopen(pedido, timeout=TEMPO_LIMITE) as resposta:
            dados = json.loads(resposta.read(500_000))
    except Exception:
        return None
    for evento in dados.get("events", []):
        if evento.get("eventAction") == "registration":
            try:
                return datetime.fromisoformat(evento["eventDate"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                return None
    return None


def sinal_idade(dominio: str):
    data = data_de_registro(dominio)
    if data is None:
        return None
    if data.tzinfo is None:
        data = data.replace(tzinfo=timezone.utc)
    dias = (datetime.now(timezone.utc) - data).days
    if dias < 30:
        return (f"Domínio criado há só {dias} dia(s)", 30)
    if dias < 180:
        return (f"Domínio recente: criado há {dias} dias", 15)
    return None


# ---------------------------------------------------------------- certificado
def situacao_certificado(host: str) -> str:
    """'ok', 'ruim' (inválido/vencido/de outro site) ou 'sem_resposta'."""
    try:
        conferir_endereco_publico(host)
    except EnderecoProibido:
        return "sem_resposta"
    contexto = ssl.create_default_context()
    try:
        with socket.create_connection((host, 443), timeout=TEMPO_LIMITE) as bruto:
            with contexto.wrap_socket(bruto, server_hostname=host):
                return "ok"
    except ssl.SSLCertVerificationError:
        return "ruim"
    except (OSError, ssl.SSLError):
        return "sem_resposta"


def sinal_certificado(host: str):
    if situacao_certificado(host) == "ruim":
        return ("Certificado de segurança (SSL) inválido, vencido ou de outro site", 25)
    return None


# ---------------------------------------------------------------- redirecionamentos
def caminho_de_redirecionamentos(url: str) -> list:
    """Visita o link SEM baixar a página e anota cada salto (301, 302...)."""
    caminho = [url]
    atual = url
    for _ in range(MAX_SALTOS):
        partes = urlsplit(atual)
        if partes.scheme not in ("http", "https") or not partes.hostname:
            break
        try:
            conferir_endereco_publico(partes.hostname)
        except EnderecoProibido:
            break
        classe = http.client.HTTPSConnection if partes.scheme == "https" else http.client.HTTPConnection
        conexao = classe(partes.hostname, partes.port, timeout=TEMPO_LIMITE)
        alvo = (partes.path or "/") + (f"?{partes.query}" if partes.query else "")
        try:
            conexao.request("GET", alvo, headers={"User-Agent": "Mozilla/5.0 (analisador-caveira)"})
            resposta = conexao.getresponse()
            codigo = resposta.status
            destino = resposta.getheader("Location")
        except (OSError, http.client.HTTPException):
            break
        finally:
            conexao.close()
        if codigo not in (301, 302, 303, 307, 308) or not destino:
            break
        atual = urljoin(atual, destino)
        caminho.append(atual)
    return caminho


def sinais_redirecionamento(info: dict) -> tuple:
    caminho = caminho_de_redirecionamentos(info["url"])
    sinais = []
    if len(caminho) > 1:
        try:
            final = separar_url(caminho[-1])
        except ValueError:
            return sinais, caminho
        if final["dominio_principal"] != info["dominio_principal"]:
            sinais.append((f"Redireciona para outro site: {final['dominio_principal']}", 20))
            marca = imita_marca(final["nome"])
            if marca:
                sinais.append((f"O destino final imita a marca '{marca}'", 35))
    return sinais, caminho
