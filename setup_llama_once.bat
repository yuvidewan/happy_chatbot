@echo off
setlocal

if not exist .venv (
  python -m venv .venv
)

call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

set HAPPYBOT_TRAIN_MODE=laptop
set HAPPYBOT_USE_4BIT=1
set HAPPYBOT_MAX_LENGTH=256
set HAPPYBOT_EPOCHS=1
set HAPPYBOT_GRAD_ACCUM=2
set HAPPYBOT_LORA_R=8
set HAPPYBOT_LORA_ALPHA=16

if not exist models\base_llama (
  echo ERROR: models\base_llama not found.
  echo Put your downloaded Llama HF model folder in: models\base_llama
  echo Example: models\base_llama\config.json , tokenizer.json , model-*.safetensors
  exit /b 1
)

python scripts_prepare_llama_data.py
if errorlevel 1 (
  echo.
  echo ERROR: Failed while preparing llama training data.
  exit /b 1
)

python scripts_finetune_llama.py
if errorlevel 1 (
  echo.
  echo ERROR: Fine-tuning failed.
  echo If you are on CPU-only laptop, use a smaller base model in models\base_llama.
  echo Recommended: Qwen/Qwen2.5-1.5B-Instruct or TinyLlama/TinyLlama-1.1B-Chat-v1.0
  exit /b 1
)

echo.
echo One-time Llama setup complete (laptop mode).
echo Start app with: uvicorn app.main:app --reload
endlocal
