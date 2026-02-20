from __future__ import annotations

import json
from pathlib import Path


def convert_conversations_to_llama_train(
    source_path: Path = Path("data/conversations_train.jsonl"),
    output_path: Path = Path("data/llama_train.jsonl"),
):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    system_prompt = (
        "You are HappyBot, a friendly and emotionally intelligent assistant. "
        "Respond naturally, with warmth, clarity, and practical help."
    )

    rows_written = 0
    with source_path.open("r", encoding="utf-8") as src, output_path.open("w", encoding="utf-8") as dst:
        for line in src:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            user = row.get("user", "").strip()
            assistant = row.get("assistant", "").strip()
            if not user or not assistant:
                continue

            out = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": assistant},
                ]
            }
            dst.write(json.dumps(out, ensure_ascii=True) + "\n")
            rows_written += 1

    return rows_written


if __name__ == "__main__":
    total = convert_conversations_to_llama_train()
    print(f"Prepared {total} rows -> data/llama_train.jsonl")
