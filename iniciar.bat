REM Analisador Caveira - Copyright (c) 2026 Hiagor Franklin. Todos os direitos reservados.
@echo off
REM Clique duas vezes neste arquivo para instalar (na 1a vez) e iniciar o analisador.
cd /d "%~dp0"
if not exist .venv (
  echo Criando ambiente virtual...
  python -m venv .venv || (echo Python nao encontrado. Instale em https://www.python.org/downloads/ & pause & exit /b)
  call .venv\Scripts\activate
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate
)
python app.py %*
pause
