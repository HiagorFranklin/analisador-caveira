@echo off
REM Analisador Caveira - Copyright (c) 2026 Hiagor Franklin. Licenca MIT (veja LICENSE).
REM Clique duas vezes neste arquivo para instalar (na 1a vez) e iniciar o analisador.
REM Funciona mesmo se a pasta for movida: se o ambiente quebrar, ele e recriado.
cd /d "%~dp0"
set "PY=.venv\Scripts\python.exe"

if exist "%PY%" (
  "%PY%" -c "import fastapi, uvicorn, multipart" >nul 2>&1 || (
    echo Ambiente do Python quebrado ^(a pasta foi movida?^). Recriando...
    rmdir /s /q .venv
  )
)

if not exist "%PY%" (
  echo Criando ambiente do Python ^(so na primeira vez, pode levar 1 minuto^)...
  python -m venv .venv
  if errorlevel 1 (
    echo.
    echo Python nao encontrado. Instale em https://www.python.org/downloads/
    echo e marque "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
  )
  "%PY%" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo.
    echo Falha ao instalar as dependencias. Confira sua internet e tente de novo.
    pause
    exit /b 1
  )
)

"%PY%" app.py %*
pause