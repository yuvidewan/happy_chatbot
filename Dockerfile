FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860 \
    HF_HOME=/data/.cache/huggingface \
    HAPPYBOT_BASE_MODEL_PATH=/data/models/base_llama \
    HAPPYBOT_ADAPTER_PATH=/data/models/happybot_lora

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app
COPY *.py ./
COPY happybot.db ./happybot.db

RUN mkdir -p /data/models/base_llama /data/models/happybot_lora

EXPOSE 7860

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
