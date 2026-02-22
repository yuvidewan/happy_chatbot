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
    train_mode = os.getenv("HAPPYBOT_TRAIN_MODE", "laptop").strip().lower()
    use_4bit = os.getenv("HAPPYBOT_USE_4BIT", "1") == "1"

    # Laptop-friendly defaults; can be overridden via env vars.
    if train_mode == "laptop":
        default_max_length = 256
        default_epochs = 1
        default_grad_accum = 2
        default_lora_r = 8
        default_lora_alpha = 16
    else:
        default_max_length = 1024
        default_epochs = 3
        default_grad_accum = 8
        default_lora_r = 16
        default_lora_alpha = 32

    max_length = int(os.getenv("HAPPYBOT_MAX_LENGTH", str(default_max_length)))
    num_epochs = int(os.getenv("HAPPYBOT_EPOCHS", str(default_epochs)))
    grad_accum = int(os.getenv("HAPPYBOT_GRAD_ACCUM", str(default_grad_accum)))
    lora_r = int(os.getenv("HAPPYBOT_LORA_R", str(default_lora_r)))
    lora_alpha = int(os.getenv("HAPPYBOT_LORA_ALPHA", str(default_lora_alpha)))

    if not base_model_path.exists():
        raise FileNotFoundError(
            "Base model missing. Put downloaded llama model into models/base_llama "
            "or set HAPPYBOT_BASE_MODEL_PATH"
        )
    if not train_path.exists():
        raise FileNotFoundError("Training file missing. Run python scripts_prepare_llama_data.py first.")
    model_file = base_model_path / "model.safetensors"
    model_size_gb = (model_file.stat().st_size / (1024**3)) if model_file.exists() else None
    cpu_only = not torch.cuda.is_available()
    large_model_threshold_gb = float(os.getenv("HAPPYBOT_CPU_BLOCK_MODEL_GB", "5.0"))

    if cpu_only and train_mode == "laptop":
        # Allow lightweight local models on CPU; block only large models.
        if model_size_gb is not None and model_size_gb > large_model_threshold_gb:
            raise RuntimeError(
                f"No CUDA GPU detected and base model is ~{model_size_gb:.2f} GB. "
                "CPU fine-tuning this model is not practical for most 12-16GB laptops. "
                "Use a smaller base model (1B-3B) or train on a GPU machine."
            )
        # CPU-safe training defaults for lightweight models.
        max_length = int(os.getenv("HAPPYBOT_MAX_LENGTH", "128"))
        num_epochs = int(os.getenv("HAPPYBOT_EPOCHS", "1"))
        grad_accum = int(os.getenv("HAPPYBOT_GRAD_ACCUM", "1"))
        lora_r = int(os.getenv("HAPPYBOT_LORA_R", "4"))
        lora_alpha = int(os.getenv("HAPPYBOT_LORA_ALPHA", "8"))

    tokenizer = AutoTokenizer.from_pretrained(base_model_path, use_fast=True)
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    quantization_config = None
    if torch.cuda.is_available() and use_4bit:
        try:
            from transformers import BitsAndBytesConfig

            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
        except Exception:
            quantization_config = None

    model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        torch_dtype=dtype,
        device_map="auto" if torch.cuda.is_available() else None,
        quantization_config=quantization_config,
        low_cpu_mem_usage=True,
    )
    model.gradient_checkpointing_enable()
    model.config.use_cache = False

    peft_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
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
            max_length=max_length,
            padding="max_length",
        )
        tokens["labels"] = tokens["input_ids"].copy()
        return tokens

    tokenized = dataset.map(preprocess, batched=True, remove_columns=dataset.column_names)

    args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=num_epochs,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=grad_accum,
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
