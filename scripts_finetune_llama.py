from __future__ import annotations

import json
import os
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)


def _build_text(tokenizer, messages):
    if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template:
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)

    lines = []
    for msg in messages:
        lines.append(f"{msg['role'].upper()}: {msg['content']}")
    return "\n".join(lines)


def main():
    base_model_path = Path(os.getenv("HAPPYBOT_BASE_MODEL_PATH", "models/base_llama"))
    train_path = Path("data/llama_train.jsonl")
    output_dir = Path("models/happybot_lora")

    if not base_model_path.exists():
        raise FileNotFoundError(
            "Base model missing. Put downloaded llama model into models/base_llama "
            "or set HAPPYBOT_BASE_MODEL_PATH"
        )
    if not train_path.exists():
        raise FileNotFoundError("Training file missing. Run python scripts_prepare_llama_data.py first.")

    tokenizer = AutoTokenizer.from_pretrained(base_model_path, use_fast=True)
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        torch_dtype=dtype,
        device_map="auto" if torch.cuda.is_available() else None,
    )

    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, peft_config)

    dataset = load_dataset("json", data_files=str(train_path), split="train")

    def preprocess(examples):
        texts = [_build_text(tokenizer, msgs) for msgs in examples["messages"]]
        tokens = tokenizer(
            texts,
            truncation=True,
            max_length=1024,
            padding="max_length",
        )
        tokens["labels"] = tokens["input_ids"].copy()
        return tokens

    tokenized = dataset.map(preprocess, batched=True, remove_columns=dataset.column_names)

    args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=3,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        logging_steps=10,
        save_strategy="epoch",
        fp16=torch.cuda.is_available(),
        bf16=False,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
    )

    trainer.train()
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    info = {
        "base_model_path": str(base_model_path),
        "adapter_path": str(output_dir),
        "trained_rows": len(dataset),
    }
    Path("models").mkdir(parents=True, exist_ok=True)
    Path("models/happybot_lora_train_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print("LoRA fine-tuning completed.")


if __name__ == "__main__":
    main()
