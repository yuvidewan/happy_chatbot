from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


@dataclass
class ChatTurn:
    role: str
    text: str


class FineTunedLlamaModel:
    def __init__(self):
        self.base_model_path = Path(os.getenv("HAPPYBOT_BASE_MODEL_PATH", "models/base_llama"))
        self.adapter_path = Path(os.getenv("HAPPYBOT_ADAPTER_PATH", "models/happybot_lora"))

        if not self.base_model_path.exists():
            raise FileNotFoundError(
                "Base Llama model not found. Put your downloaded model at models/base_llama "
                "or set HAPPYBOT_BASE_MODEL_PATH."
            )

        self.tokenizer = AutoTokenizer.from_pretrained(self.base_model_path, use_fast=True)
        if self.tokenizer.pad_token is None and self.tokenizer.eos_token is not None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        base = AutoModelForCausalLM.from_pretrained(
            self.base_model_path,
            torch_dtype=dtype,
            device_map="auto" if torch.cuda.is_available() else None,
        )

        if self.adapter_path.exists():
            self.model = PeftModel.from_pretrained(base, self.adapter_path)
        else:
            self.model = base

        self.model.eval()

    def infer_sentiment(self, message: str) -> str:
        text = message.lower()
        negative = ["sad", "anxious", "depressed", "angry", "upset", "stressed", "tired", "lonely"]
        positive = ["happy", "excited", "great", "good", "amazing", "thankful", "better"]
        if any(word in text for word in negative):
            return "low"
        if any(word in text for word in positive):
            return "high"
        return "neutral"

    def detect_intent(self, message: str) -> str:
        text = message.lower()
        if any(k in text for k in ["joke", "funny", "laugh", "meme", "roast"]):
            return "humor"
        if any(k in text for k in ["anxious", "stress", "overwhelmed", "panic", "nervous", "worry"]):
            return "anxiety"
        if any(k in text for k in ["sad", "down", "depressed", "lonely", "hopeless", "empty"]):
            return "sadness"
        if any(k in text for k in ["motivate", "goal", "discipline", "productivity", "focus", "study"]):
            return "motivation"
        return "general"

    def generate_reply(self, message: str, history: list[ChatTurn]) -> tuple[str, str, str]:
        sentiment = self.infer_sentiment(message)
        intent = self.detect_intent(message)

        system_prompt = (
            "You are HappyBot, a warm and natural conversational AI. "
            "Speak like a caring human friend with emotional intelligence. "
            "You can be funny when asked, supportive when needed, and practical with suggestions. "
            "Never say you are an AI model unless asked directly. Keep responses concise but natural."
        )

        messages = [{"role": "system", "content": system_prompt}]
        for turn in history[-8:]:
            role = "assistant" if turn.role == "assistant" else "user"
            messages.append({"role": role, "content": turn.text})
        messages.append({"role": "user", "content": message})

        prompt = self._build_prompt(messages)
        inputs = self.tokenizer(prompt, return_tensors="pt")

        if torch.cuda.is_available():
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        with torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=220,
                do_sample=True,
                temperature=0.85,
                top_p=0.92,
                repetition_penalty=1.05,
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.pad_token_id,
            )

        generated = output[0][inputs["input_ids"].shape[-1]:]
        reply = self.tokenizer.decode(generated, skip_special_tokens=True).strip()

        if not reply:
            reply = "I hear you. Tell me more about what you need right now."

        return reply, sentiment, intent

    def _build_prompt(self, messages: list[dict]) -> str:
        if hasattr(self.tokenizer, "apply_chat_template") and self.tokenizer.chat_template:
            return self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )

        lines = []
        for msg in messages:
            role = msg["role"].upper()
            lines.append(f"{role}: {msg['content']}")
        lines.append("ASSISTANT:")
        return "\n".join(lines)
