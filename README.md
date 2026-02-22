# HappyBot Setup Guide (Local Llama + Fine-Tuning)

This README is intentionally simple. Follow the steps in order.

## What you get

- FastAPI chatbot app
- Local model inference (no hosted API)
- One-time LoRA fine-tuning for your happiness-chatbot style
- Frontend already connected to backend

---

## 1. Prerequisites

Install before anything else:

- Python 3.10+ (recommended 3.11)
- Git (optional but useful)
- NVIDIA GPU + CUDA (recommended for speed)

CPU works, but training/inference can be very slow.

## Reality Check For Normal Laptops (12-16GB RAM)

- Fine-tuning **Mistral-7B** on CPU-only laptops is usually not practical.
- On a laptop with CUDA GPU, it can work in the provided `laptop` mode (reduced settings).
- If you have no CUDA GPU, use a smaller model (1B-3B) for local fine-tuning.

---

## 2. Hugging Face Account Setup (One Time)

1. Create account:
- Open: `https://huggingface.co/join`
- Verify email

2. Create access token:
- Open: `https://huggingface.co/settings/tokens`
- Click `New token`
- Name: anything (example: `happybot-local`)
- Role: `Read`
- Create token and copy it

3. Install project dependencies:

```bat
setup_env.bat
```

4. Login to Hugging Face CLI:

```bat
huggingface-cli login
```

Paste your token when prompted.

---

## 3. Model Options (Keep all 3)

Choose one base model to place in `models\base_llama`.

### Option A: Mistral-7B (your original command, best quality on GPU)

```bat
huggingface-cli download mistralai/Mistral-7B-Instruct-v0.2 --local-dir models\base_llama --local-dir-use-symlinks False
```

Use this if:
- you have a CUDA GPU
- you want highest quality among these options

### Option B: TinyLlama-1.1B (your existing lightweight option)

```bat
huggingface-cli download TinyLlama/TinyLlama-1.1B-Chat-v1.0 --local-dir models\base_llama --local-dir-use-symlinks False
```

Use this if:
- you are on CPU-only or lower-end laptop
- you want fastest setup and inference

### Option C (Recommended for normal laptops): Qwen2.5-1.5B-Instruct

```bat
huggingface-cli download Qwen/Qwen2.5-1.5B-Instruct --local-dir models\base_llama --local-dir-use-symlinks False
```

Use this if:
- you have 12-16 GB RAM laptop
- you want better quality than TinyLlama but much lighter than 7B

After download, you should have files like `config.json`, tokenizer files, and weights inside:

```text
models/base_llama
```

---

## 4. One-Time Fine-Tune Setup

Run:

```bat
setup_llama_once.bat
```

Manual commands (same flow) if you prefer explicit steps:

```bat
python scripts_prepare_llama_data.py
python scripts_finetune_llama.py
```

This script does all of this automatically:

- creates/uses `.venv`
- installs requirements
- prepares training file
- fine-tunes LoRA adapter
- saves adapter to `models/happybot_lora`

You only need this once (run again only if you retrain).

Optional for faster/lower-VRAM GPU training (if install works on your machine):

```bat
pip install bitsandbytes
```

---

## 5. Start the App

```bat
uvicorn app.main:app --reload
```

Open:

- App: `http://127.0.0.1:8000/`
- Health: `http://127.0.0.1:8000/health`

---

## 6. Daily Usage (after setup)

Normally you only run:

```bat
uvicorn app.main:app --reload
```

No need to repeat Hugging Face login/download/fine-tune unless you change models or retrain.

---

## 7. If model is stored somewhere else

Set this before setup/run:

```bat
set HAPPYBOT_BASE_MODEL_PATH=D:\path\to\your\model
```

Then run:

```bat
setup_llama_once.bat
```

---

## 8. Common Issues

1. `huggingface-cli` not found
- Run `setup_env.bat` first
- Then reopen terminal or run from `.venv` active shell

2. Fine-tuning looks stuck at `0%`
- It is usually running first heavy steps
- Check GPU usage with `nvidia-smi`
- CPU-only can appear stuck for several minutes

3. `/api/chat` returns model missing error
- Ensure `models/base_llama` exists
- Ensure you already ran `setup_llama_once.bat`

---

## 9. Important Note

This project performs local fine-tuning/inference and does not replace professional mental health care.
