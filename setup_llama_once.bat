@echo off
setlocal

if not exist .venv (
  python -m venv .venv
)

call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if not exist models\base_llama (
  echo ERROR: models\base_llama not found.
  echo Put your downloaded Llama HF model folder in: models\base_llama
  echo Example: models\base_llama\config.json , tokenizer.json , model-*.safetensors
  exit /b 1
)

python scripts_prepare_llama_data.py
python scripts_finetune_llama.py

echo.
echo One-time Llama setup complete.
echo Start app with: uvicorn app.main:app --reload
endlocal
