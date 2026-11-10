# Analisador Caveira - Copyright (c) 2026 Hiagor Franklin. Licença MIT (veja LICENSE).
"""Servidor web do Analisador Caveira.

Rode com:  python app.py
Depois abra http://127.0.0.1:8000 no navegador.
"""

import socket
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import historico
from analise import analisar_email, analisar_texto, analisar_url

LIMITE_EML = 2 * 1024 * 1024  # 2 MB

historico.criar_tabela()
app = FastAPI(title="Analisador Caveira", description="Detector de phishing em URLs, e-mails e mensagens.")


class PedidoUrl(BaseModel):
    url: str = Field(max_length=2048)
    usar_internet: bool = True


class PedidoTexto(BaseModel):
    texto: str = Field(max_length=200_000)
    usar_internet: bool = False


def executar(funcao, *argumentos):
    """Roda a análise, transforma erros em mensagens amigáveis e salva no histórico."""
    try:
        resultado = funcao(*argumentos)
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro))
    except Exception:
        raise HTTPException(status_code=500, detail="Algo deu errado durante a análise.")
    historico.salvar(resultado)
    return resultado


@app.post("/api/url")
def rota_url(pedido: PedidoUrl):
    return executar(analisar_url, pedido.url, pedido.usar_internet)


@app.post("/api/texto")
def rota_texto(pedido: PedidoTexto):
    return executar(analisar_texto, pedido.texto, pedido.usar_internet)


@app.post("/api/email")
def rota_email(arquivo: UploadFile = File(...), usar_internet: bool = Form(False)):
    nome = Path(arquivo.filename or "email.eml").name[:100]
    if not nome.lower().endswith(".eml"):
        raise HTTPException(status_code=400, detail="Envie um arquivo .eml.")
    dados = arquivo.file.read(LIMITE_EML + 1)  # lido só na memória, nunca salvo em disco
    if len(dados) > LIMITE_EML:
        raise HTTPException(status_code=413, detail="O arquivo passa de 2 MB.")
    if not dados.strip():
        raise HTTPException(status_code=400, detail="O arquivo está vazio.")
    return executar(analisar_email, dados, nome, usar_internet)


@app.get("/api/historico")
def rota_historico(limite: int = Query(20, ge=1, le=100)):
    return historico.ultimas(limite)


@app.delete("/api/historico")
def rota_apagar_historico():
    historico.apagar_tudo()
    return {"ok": True}


app.mount("/", StaticFiles(directory=Path(__file__).parent / "site", html=True), name="site")


def ip_na_rede_local() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))  # não envia nada, só descobre o IP local
            return s.getsockname()[0]
    except OSError:
        return "SEU-IP"


if __name__ == "__main__":
    import sys

    import uvicorn

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    no_celular = "--celular" in sys.argv
    host = "0.0.0.0" if no_celular else "127.0.0.1"
    print("\n  ☠  ANALISADOR CAVEIRA  ☠")
    print("  No computador: http://127.0.0.1:8000")
    if no_celular:
        print(f"  No celular (mesmo Wi-Fi): http://{ip_na_rede_local()}:8000")
    else:
        print("  Para abrir no celular, rode:  python app.py --celular")
    print("  Para parar: Ctrl + C\n")
    uvicorn.run(app, host=host, port=8000)
