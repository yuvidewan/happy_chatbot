# HappyBot (FastAPI + Fine-Tuned Local Llama)

This project now uses **only Llama** for chat generation.
The previous retrieval model path has been removed.

## One-Time Setup (Windows)

1. Put your downloaded Llama HuggingFace model folder at:

```text
happybot/models/base_llama
```

Expected files in that folder include items like:
- `config.json`
- `tokenizer.json` / tokenizer files
- `model-*.safetensors` (or `pytorch_model.bin`)

2. Run one command:

```bat
setup_llama_once.bat
```

This does everything:
- creates/uses virtualenv
- installs dependencies
- prepares fine-tuning data
- fine-tunes a LoRA adapter for HappyBot

LoRA adapter output:

```text
happybot/models/happybot_lora
```

## One-Time Setup (macOS/Linux)

```bash
chmod +x setup_llama_once.sh
./setup_llama_once.sh
```

## Run App

```bash
uvicorn app.main:app --reload
```

Open:
- UI: `http://127.0.0.1:8000/`
- Health: `http://127.0.0.1:8000/health`

## How It Works

- `scripts_prepare_llama_data.py` converts conversation pairs into chat-format training records.
- `scripts_finetune_llama.py` runs LoRA fine-tuning on your local base Llama model.
- `app/services/llama_service.py` loads base + LoRA adapter and generates responses.

## Important Notes

- This is true local fine-tuning (LoRA), not just an external API call.
- Best experience is with CUDA GPU.
- CPU training/inference is possible but can be very slow.

## If Your Llama Is In Another Folder

Set environment variable before running:

```bat
set HAPPYBOT_BASE_MODEL_PATH=D:\path\to\your\llama
```

Then run:

```bat
setup_llama_once.bat
```

## Frontend

Frontend structure is unchanged.
Includes the updated aesthetic color theme and dark mode toggle.
