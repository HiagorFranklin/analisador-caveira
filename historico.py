# Analisador Caveira - Copyright (c) 2026 Hiagor Franklin. Todos os direitos reservados.
# Código proprietário: proibido copiar, modificar ou distribuir sem autorização. Veja LICENSE.
"""Guarda as análises num arquivo SQLite (historico.db) ao lado do projeto."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ARQUIVO = Path(__file__).parent / "historico.db"


def conectar():
    conexao = sqlite3.connect(ARQUIVO)
    conexao.row_factory = sqlite3.Row
    return conexao


def criar_tabela():
    with conectar() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS analises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                alvo TEXT NOT NULL,
                nota INTEGER NOT NULL,
                nivel TEXT NOT NULL,
                sinais TEXT NOT NULL,
                quando TEXT NOT NULL
            )"""
        )


def salvar(resultado: dict):
    with conectar() as c:
        c.execute(
            "INSERT INTO analises (tipo, alvo, nota, nivel, sinais, quando) VALUES (?, ?, ?, ?, ?, ?)",
            (
                resultado["tipo"],
                resultado["alvo"][:500],
                resultado["nota"],
                resultado["nivel"],
                json.dumps(resultado["sinais"], ensure_ascii=False),
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )


def ultimas(limite: int = 20) -> list:
    with conectar() as c:
        linhas = c.execute(
            "SELECT * FROM analises ORDER BY id DESC LIMIT ?", (limite,)
        ).fetchall()
    return [
        {**dict(linha), "sinais": json.loads(linha["sinais"])}
        for linha in linhas
    ]


def apagar_tudo():
    with conectar() as c:
        c.execute("DELETE FROM analises")
