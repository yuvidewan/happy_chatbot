---
title: happiness_bot
sdk: docker
app_port: 7860
---



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

## 3. Download Base Model (Your Exact Command)

Run this in project root (`happybot` folder):

```bat
huggingface-cli download mistralai/Mistral-7B-Instruct-v0.2 --local-dir models\base_llama --local-dir-use-symlinks False
```

After this, you should have files like `config.json`, tokenizer files, and model weights inside:

```text
models/base_llama
```

Laptop-friendly alternative (recommended if your machine is struggling):

```bat
huggingface-cli download TinyLlama/TinyLlama-1.1B-Chat-v1.0 --local-dir models\base_llama --local-dir-use-symlinks False
```

---

## 4. One-Time Fine-Tune Setup

Run:

```bat
setup_llama_once.bat
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
