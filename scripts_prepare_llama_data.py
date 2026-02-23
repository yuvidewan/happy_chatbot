from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict


def convert_conversations_to_llama_train(
    source_path: Path = Path("data/conversations_train.jsonl"),
    output_path: Path = Path("data/llama_train.jsonl"),
):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    system_prompt = (
        "You are HappyBot, a friendly and emotionally intelligent assistant. "
        "Respond naturally with warmth, clarity, and practical help. "
        "Default behavior: ask fewer questions, give more concrete suggestions. "
        "For sadness/anxiety: calm first, then 2-3 tips, then optional one short follow-up question. "
        "For fun mode: joke around and keep it playful."
    )

    def _as_pair_messages(user_text: str, assistant_text: str):
        return [
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": assistant_text},
        ]

    raw_rows = []
    with source_path.open("r", encoding="utf-8") as src:
        for line in src:
            line = line.strip()
            if not line:
                continue
            raw_rows.append(json.loads(line))

    flow_groups: dict[str, list[dict]] = defaultdict(list)
    standalone_rows: list[dict] = []

    for row in raw_rows:
        messages = row.get("messages")
        if isinstance(messages, list) and messages:
            standalone_rows.append(row)
            continue

        flow_id = str(row.get("flow_id", "")).strip()
        user = str(row.get("user", "")).strip()
        assistant = str(row.get("assistant", "")).strip()
        if not user or not assistant:
            continue

        if flow_id:
            flow_groups[flow_id].append(row)
        else:
            standalone_rows.append(row)

    rows_written = 0
    with output_path.open("w", encoding="utf-8") as dst:
        for row in standalone_rows:
            if isinstance(row.get("messages"), list):
                cleaned = []
                for item in row["messages"]:
                    role = str(item.get("role", "")).strip().lower()
                    content = str(item.get("content", "")).strip()
                    if role in {"system", "user", "assistant"} and content:
                        cleaned.append({"role": role, "content": content})
                if not cleaned:
                    continue
                if cleaned[0]["role"] != "system":
                    cleaned = [{"role": "system", "content": system_prompt}] + cleaned
                out = {"messages": cleaned}
            else:
                user = str(row.get("user", "")).strip()
                assistant = str(row.get("assistant", "")).strip()
                if not user or not assistant:
                    continue
                out = {
                    "messages": [{"role": "system", "content": system_prompt}] + _as_pair_messages(user, assistant)
                }
            dst.write(json.dumps(out, ensure_ascii=True) + "\n")
            rows_written += 1

        for flow_id in sorted(flow_groups.keys()):
            turns = flow_groups[flow_id]
            turns.sort(key=lambda x: int(x.get("turn", 10**9)))
            rolling_context: list[dict] = []
            for row in turns:
                user = str(row.get("user", "")).strip()
                assistant = str(row.get("assistant", "")).strip()
                if not user or not assistant:
                    continue

                sample_messages = [{"role": "system", "content": system_prompt}] + rolling_context + _as_pair_messages(
                    user, assistant
                )
                out = {"messages": sample_messages}
                dst.write(json.dumps(out, ensure_ascii=True) + "\n")
                rows_written += 1

                rolling_context.extend(_as_pair_messages(user, assistant))
                if len(rolling_context) > 8:
                    rolling_context = rolling_context[-8:]

    return rows_written


if __name__ == "__main__":
    total = convert_conversations_to_llama_train()
    print(f"Prepared {total} rows -> data/llama_train.jsonl")
