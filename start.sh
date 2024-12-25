#!/usr/bin/env bash

# Получаем абсолютный путь к директории скрипта
SCRIPT_DIR=$(dirname "$0")

cd "$SCRIPT_DIR"
./venv/bin/python ./main.py


# venv/bin/pip install requirements.txt
