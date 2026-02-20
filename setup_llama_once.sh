#!/usr/bin/env bash
set -e

if [ ! -d ".venv" ]; then
  python -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if [ ! -d "models/base_llama" ]; then
  echo "ERROR: models/base_llama not found."
  echo "Put your downloaded Llama HF model folder in models/base_llama"
  exit 1
fi

python scripts_prepare_llama_data.py
python scripts_finetune_llama.py

echo "One-time Llama setup complete."
echo "Start app with: uvicorn app.main:app --reload"
