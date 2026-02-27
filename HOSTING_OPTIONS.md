# HappyBot Hosting Options (Quick + Fully Hosted)

Last updated: 2026-02-27

This guide gives you practical hosting paths for your current HappyBot codebase.

## Option 1 (Fastest, Free): Run locally + public URL via Cloudflare Tunnel

Use this when you want to go live in minutes and URL does not matter.

### 1. Fix cloudflared command not found (your current issue)

Your binary exists at:

`C:\Program Files (x86)\cloudflared\cloudflared.exe`

Run directly right now:

```powershell
& "C:\Program Files (x86)\cloudflared\cloudflared.exe" --version
```

If that works, add to PATH permanently (current user):

```powershell
$cfDir = "C:\Program Files (x86)\cloudflared"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (($userPath -split ';') -notcontains $cfDir) {
  [Environment]::SetEnvironmentVariable("Path", ($userPath.TrimEnd(';') + ";" + $cfDir), "User")
}
```

Close all terminals and open a new PowerShell, then test:

```powershell
cloudflared --version
```

### 2. Start HappyBot API

From project root `C:\Users\yuvra\Desktop\PROJECTS\happybot`:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. Expose it publicly

In another terminal:

```powershell
cloudflared tunnel --url http://localhost:8000
```

Copy the generated `https://*.trycloudflare.com` URL and share it.

### 4. Important notes

- Your machine must stay ON.
- If your app process stops, URL stops.
- This is free and quickest.

---

## Option 2 (Totally hosted, free): Hugging Face Spaces (CPU)

Use this when you want cloud-only hosting without your laptop running.

Reality: your current stack can be heavy (`torch` + local Llama). For free CPU hosting, use a smaller model.

### 1. Prepare repository for cloud

In `requirements.txt`, keep only what runtime needs.

Recommended runtime requirements:

```txt
fastapi
uvicorn
jinja2
sqlalchemy
pydantic
python-multipart
torch
transformers
peft
accelerate
sentencepiece
safetensors
huggingface_hub
```

(Training-only packages like `datasets` can be removed for deploy.)

### 2. Add startup command for Space

Use Docker Space or start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 7860
```

### 3. Use smaller base model for free CPU

Your code reads env vars:

- `HAPPYBOT_BASE_MODEL_PATH`
- `HAPPYBOT_ADAPTER_PATH`

For free CPU, use a small model (for example TinyLlama class) and adapter compatible with that base.

### 4. Push project to GitHub

```powershell
git add .
git commit -m "Prepare HappyBot for HF deployment"
git push
```

### 5. Create Space

- Go to `https://huggingface.co/new-space`
- SDK: Docker (or Gradio/Static if you refactor)
- Visibility: Public
- Link your GitHub repo or push directly

### 6. Set Space variables/secrets

Set env vars matching your model paths in container.

### 7. Validate endpoints

- `/health`
- `/api/chat`

### 8. Limitations on free tier

- Cold starts
- CPU latency
- Memory limits

---

## Option 3 (Cloud app host, usually not fully free long-term): Render / Railway

Use this only if you accept free-tier limits and potential pricing changes.

### Render quick setup

1. Create Web Service from GitHub repo.
2. Build command:

```bash
pip install -r requirements.txt
```

3. Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

4. Add environment variables for model paths.
5. Deploy and test `/health`.

Notes:
- Free instances can sleep.
- Bandwidth/runtime limits may apply.

---

## What should you choose right now?

If the goal is "works quickly and free": choose Option 1 today.

If the goal is "fully hosted and I can accept slower responses": choose Option 2 with a smaller model.

---

## Your current repo status check (important)

Your `models/base_llama` folder appears to be missing full base model weights (`model.safetensors`).

Before any hosting path where chat must work, ensure base model weights are present and compatible with adapter.

You can verify locally by starting app and hitting:

- `http://127.0.0.1:8000/health`
- `POST /api/chat`

If `/api/chat` returns model-not-found errors, fix model download first.
