# Analisador Caveira - Copyright (c) 2026 Hiagor Franklin. Licença MIT (veja LICENSE).
"""O coração do analisador: junta as regras e calcula a nota de risco (0 a 100).

Três tipos de entrada:
  - analisar_url(texto)       -> um link
  - analisar_email(bytes)     -> um arquivo .eml (e-mail salvo)
  - analisar_texto(texto)     -> mensagem colada (SMS, WhatsApp, corpo ou código-fonte de e-mail)
"""

import re
import unicodedata
from email import message_from_bytes, policy
from email.utils import parseaddr

from .dominio import separar_url
from .marcas import MARCAS, imita_marca
from .regras_url import sinais_da_url

MAX_LINKS = 20

# Nota 0-19 = baixo | 20-49 = médio | 50-100 = alto
def nivel_do_risco(nota: int) -> str:
    if nota >= 50:
        return "alto"
    if nota >= 20:
        return "médio"
    return "baixo"


def somar(sinais: list) -> int:
    return min(100, sum(pontos for _, pontos in sinais))


def formatar(sinais: list) -> list:
    return [{"motivo": motivo, "pontos": pontos} for motivo, pontos in sinais]


# ======================================================================= URL
def analisar_url(url: str, usar_internet: bool = True) -> dict:
    info = separar_url(url)
    sinais = sinais_da_url(info)
    caminho = [info["url"]]

    if usar_internet:
        from . import rede  # só carrega quando precisa

        try:
            rede.conferir_endereco_publico(info["host"])
        except rede.EnderecoProibido as erro:
            # Domínio que nem existe também é um sinal.
            if "não existe" in str(erro):
                sinais.append(("O domínio não foi encontrado na internet (pode ter sido derrubado)", 10))
            else:
                raise ValueError(str(erro))
        else:
            idade = rede.sinal_idade(info["dominio_principal"])
            if idade:
                sinais.append(idade)
            if info["esquema"] == "https":
                cert = rede.sinal_certificado(info["host"])
                if cert:
                    sinais.append(cert)
            extras, caminho = rede.sinais_redirecionamento(info)
            sinais.extend(extras)

    nota = somar(sinais)
    return {
        "tipo": "url",
        "alvo": info["url"],
        "nota": nota,
        "nivel": nivel_do_risco(nota),
        "sinais": formatar(sinais),
        "redirecionamentos": caminho,
    }


# ======================================================================= links dentro de textos
PADRAO_LINK = re.compile(r"""(?:https?://|www\.)[^\s<>"'()\[\]{}]+""", re.IGNORECASE)
PADRAO_HREF = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)


def achar_links(texto: str) -> list:
    encontrados = []
    for link in PADRAO_HREF.findall(texto) + PADRAO_LINK.findall(texto):
        link = link.strip().rstrip(".,;:!?")
        if not link.lower().startswith(("http://", "https://", "www.")):
            continue  # ignora mailto:, tel:, #ancora...
        if link not in encontrados:
            encontrados.append(link)
    return encontrados


def analisar_links(links: list, usar_internet: bool) -> list:
    resultados = []
    for link in links[:MAX_LINKS]:
        try:
            resultados.append(analisar_url(link, usar_internet))
        except ValueError:
            continue
    return resultados


# ======================================================================= frases de golpe
FRASES_GOLPE = (
    (r"\burgente\b|\bimediatamente\b|\bem ate \d+ ?h|\bhoje ainda\b|\bultimo aviso\b|\bprazo final\b", "Tom de urgência para você agir sem pensar", 10),
    (r"\b(conta|cart[aã]o|acesso|cpf)\b.{0,30}\b(bloquead|suspens|cancelad|desativad)", "Ameaça de bloqueio ou cancelamento", 15),
    (r"\b(senha|c[oó]digo de (seguran[cç]a|verifica[cç][aã]o)|token|cvv)\b", "Pede senha, código ou token", 20),
    (r"\b(confirme|atualize|valide|verifique|regularize)\b.{0,30}\b(dados|cadastro|conta|informa[cç][oõ]es)\b", "Pede para confirmar ou atualizar dados", 15),
    (r"\b(ganhou|pr[eê]mio|sorteado|contemplad|resgat)", "Promete prêmio ou dinheiro fácil", 15),
    (r"\b(pix|boleto|transfer[eê]ncia)\b.{0,40}\b(pendente|em aberto|vencid|taxa)", "Cobrança ou taxa inesperada", 15),
    (r"\b(oi m[aã]e|oi pai|troquei de n[uú]mero|meu n[uú]mero novo)\b", "Golpe do 'troquei de número'", 25),
    (r"\b(clique|acesse|toque)\b.{0,20}\b(aqui|link|abaixo)\b", "Insiste para clicar no link", 5),
)


def sinais_de_texto(texto: str) -> list:
    sinais = []
    # Tira os acentos: "último" e "ultimo" passam a ser iguais.
    minusculo = "".join(
        c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn"
    )
    for padrao, motivo, pontos in FRASES_GOLPE:
        if re.search(padrao, minusculo):
            sinais.append((motivo, pontos))
    return sinais


# ======================================================================= e-mail
def dominio_do_cabecalho(valor) -> str:
    _, endereco = parseaddr(str(valor or ""))
    if "@" not in endereco:
        return ""
    try:
        return separar_url(endereco.rsplit("@", 1)[1])["dominio_principal"]
    except ValueError:
        return ""


def sinais_de_cabecalho(msg) -> list:
    sinais = []
    dom_de = dominio_do_cabecalho(msg["From"])
    dom_resp = dominio_do_cabecalho(msg["Reply-To"])
    dom_retorno = dominio_do_cabecalho(msg["Return-Path"])

    if dom_de and dom_resp and dom_de != dom_resp:
        sinais.append((f"A resposta vai para {dom_resp}, não para o remetente {dom_de}", 20))

    if dom_de and dom_retorno and dom_de != dom_retorno:
        sinais.append((f"Remetente técnico (Return-Path: {dom_retorno}) diferente de {dom_de}", 10))

    autenticacao = " ".join(str(v) for v in (msg.get_all("Authentication-Results") or [])).lower()
    falhas = [f for f in ("spf", "dkim", "dmarc") if re.search(rf"\b{f}=(fail|softfail)", autenticacao)]
    if falhas:
        sinais.append((f"O e-mail falhou na checagem de remetente ({', '.join(falhas).upper()})", 25))

    nome, _ = parseaddr(str(msg["From"] or ""))
    nome_limpo = re.sub(r"[^a-z]", "", nome.lower())
    nome_dominio = dom_de.split(".")[0]
    for marca in MARCAS:
        if len(marca) >= 4 and marca in nome_limpo and (marca not in dom_de or imita_marca(nome_dominio)):
            sinais.append((f"Nome do remetente diz '{marca}', mas o e-mail vem de {dom_de or 'endereço desconhecido'}", 30))
            break
    return sinais


def texto_do_email(msg) -> str:
    partes = []
    for parte in msg.walk():
        if parte.get_content_type() in ("text/plain", "text/html"):
            try:
                partes.append(parte.get_content())
            except Exception:
                continue
    return "\n".join(partes)


def analisar_mensagem_email(msg, nome: str, usar_internet: bool) -> dict:
    if not (msg["From"] or msg["Subject"]):
        raise ValueError("Isso não parece um e-mail (sem remetente nem assunto).")
    corpo = texto_do_email(msg)
    assunto = str(msg["Subject"] or "(sem assunto)")
    sinais = sinais_de_cabecalho(msg) + sinais_de_texto(assunto + "\n" + re.sub(r"<[^>]+>", " ", corpo))
    links = achar_links(corpo)
    resultados = analisar_links(links, usar_internet)
    pior_link = max((r["nota"] for r in resultados), default=0)
    nota = min(100, somar(sinais) + pior_link)
    return {
        "tipo": "email",
        "alvo": f"{nome} — {assunto}"[:200],
        "assunto": assunto[:200],
        "remetente": str(msg["From"] or "")[:200],
        "nota": nota,
        "nivel": nivel_do_risco(nota),
        "sinais": formatar(sinais),
        "links": resultados,
        "links_ignorados": max(0, len(links) - MAX_LINKS),
    }


def analisar_email(dados: bytes, nome: str = "email.eml", usar_internet: bool = False) -> dict:
    msg = message_from_bytes(dados, policy=policy.default)
    return analisar_mensagem_email(msg, nome, usar_internet)


# ======================================================================= texto colado
CABECALHO_EMAIL = re.compile(r"^(received|from|return-path|delivered-to|subject|message-id|mime-version):", re.IGNORECASE | re.MULTILINE)


def analisar_texto(texto: str, usar_internet: bool = False) -> dict:
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("Cole uma mensagem para analisar.")
    if len(texto) > 200_000:
        raise ValueError("Texto grande demais (máximo de 200 mil caracteres).")

    # Se a pessoa colou o "código-fonte" do e-mail, analisamos como e-mail.
    if len(CABECALHO_EMAIL.findall(texto[:5000])) >= 2:
        try:
            return analisar_email(texto.encode("utf-8"), "e-mail colado", usar_internet)
        except ValueError:
            pass

    sinais = sinais_de_texto(texto)
    links = achar_links(texto)
    resultados = analisar_links(links, usar_internet)
    pior_link = max((r["nota"] for r in resultados), default=0)
    nota = min(100, somar(sinais) + pior_link)
    resumo = " ".join(texto.split())
    return {
        "tipo": "texto",
        "alvo": resumo[:120] + ("…" if len(resumo) > 120 else ""),
        "nota": nota,
        "nivel": nivel_do_risco(nota),
        "sinais": formatar(sinais),
        "links": resultados,
        "links_ignorados": max(0, len(links) - MAX_LINKS),
    }
