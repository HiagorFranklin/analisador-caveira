# Analisador Caveira - Copyright (c) 2026 Hiagor Franklin. Licença MIT (veja LICENSE).
"""Testes automáticos. Rode com:  python -m pytest -q"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from analise import analisar_email, analisar_texto, analisar_url
from analise.dominio import separar_url
from analise.marcas import imita_marca

EXEMPLOS = Path(__file__).parent.parent / "exemplos"


def test_separa_dominio_brasileiro():
    info = separar_url("https://login.banco.com.br/x")
    assert info["dominio_principal"] == "banco.com.br"
    assert info["subdominio"] == "login"


@pytest.mark.parametrize("nome,marca", [("paypa1", "paypal"), ("g00gle", "google"), ("nubank-seguro", "nubank"), ("arnazon", "amazon")])
def test_detecta_imitacao(nome, marca):
    assert imita_marca(nome) == marca


@pytest.mark.parametrize("nome", ["paypal", "google", "internet", "wikipedia", "github", "baixa"])
def test_nao_acusa_sites_normais(nome):
    assert imita_marca(nome) is None


def test_url_oficial_e_baixo_risco():
    assert analisar_url("https://www.google.com", usar_internet=False)["nivel"] == "baixo"


def test_url_golpe_e_alto_risco():
    r = analisar_url("http://paypa1-login.xyz/verificar", usar_internet=False)
    assert r["nivel"] == "alto"


def test_ip_e_arroba():
    r = analisar_url("http://banco.com@185.10.10.10/login", usar_internet=False)
    motivos = " ".join(s["motivo"] for s in r["sinais"])
    assert "IP" in motivos and "@" in motivos


def test_url_vazia_da_erro():
    with pytest.raises(ValueError):
        analisar_url("   ", usar_internet=False)


def test_email_golpe():
    r = analisar_email((EXEMPLOS / "golpe_banco.eml").read_bytes())
    assert r["nivel"] == "alto"
    assert len(r["links"]) == 2


def test_email_limpo():
    assert analisar_email((EXEMPLOS / "limpo.eml").read_bytes())["nivel"] == "baixo"


def test_texto_whatsapp():
    r = analisar_texto((EXEMPLOS / "mensagem_whatsapp.txt").read_text(encoding="utf-8"))
    assert r["nivel"] == "alto"


def test_texto_colado_com_cabecalho_vira_email():
    texto = (EXEMPLOS / "golpe_banco.eml").read_text(encoding="utf-8")
    assert analisar_texto(texto)["tipo"] == "email"


def test_rede_interna_bloqueada():
    with pytest.raises(ValueError):
        analisar_url("http://127.0.0.1/admin", usar_internet=True)


def test_api(tmp_path, monkeypatch):
    import historico
    monkeypatch.setattr(historico, "ARQUIVO", tmp_path / "t.db")
    from app import app
    historico.criar_tabela()
    cliente = TestClient(app)
    assert cliente.post("/api/url", json={"url": "bit.ly/x", "usar_internet": False}).status_code == 200
    eml = (EXEMPLOS / "golpe_banco.eml").read_bytes()
    r = cliente.post("/api/email", files={"arquivo": ("g.eml", eml)})
    assert r.json()["nivel"] == "alto"
    assert cliente.post("/api/email", files={"arquivo": ("g.txt", eml)}).status_code == 400
    assert len(cliente.get("/api/historico").json()) == 2
    assert "Caveira" in cliente.get("/").text
