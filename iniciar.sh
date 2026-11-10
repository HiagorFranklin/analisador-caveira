#!/usr/bin/env bash
# Analisador Caveira - Copyright (c) 2026 Hiagor Franklin. Licença MIT (veja LICENSE).
# Inicia o Analisador Caveira no Linux (Kali, Ubuntu, Debian...).
# Uso:  ./iniciar.sh            (só neste computador)
#       ./iniciar.sh --celular  (libera para o celular no mesmo Wi-Fi)
set -e
cd "$(dirname "$0")"

# Uma pasta .venv copiada do Windows não funciona no Linux: recria.
if [ -d .venv ] && [ ! -f .venv/bin/activate ]; then
  echo "Removendo .venv do Windows..."
  rm -rf .venv
fi

if [ ! -d .venv ]; then
  echo "Criando ambiente virtual..."
  if ! python3 -m venv .venv; then
    echo "Falta o pacote venv. Rode:  sudo apt update && sudo apt install -y python3-venv"
    exit 1
  fi
  .venv/bin/pip install -r requirements.txt
fi

exec .venv/bin/python app.py "$@"
