from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


@dataclass
class ChatTurn:
    role: str
    text: str


@dataclass
class GenerationProfile:
    max_new_tokens: int
    temperature: float
    top_p: float
    repetition_penalty: float
    do_sample: bool = True


class FineTunedLlamaModel:
    def __init__(self):
        self.base_model_path = Path(os.getenv("HAPPYBOT_BASE_MODEL_PATH", "models/base_llama"))
        self.adapter_path = Path(os.getenv("HAPPYBOT_ADAPTER_PATH", "models/happybot_lora"))
        self.adapter_config_path = self.adapter_path / "adapter_config.json"

        if not self.base_model_path.exists():
            raise FileNotFoundError(
                "Base Llama model not found. Put your downloaded model at models/base_llama "
                "or set HAPPYBOT_BASE_MODEL_PATH."
            )

        self.tokenizer = AutoTokenizer.from_pretrained(self.base_model_path, use_fast=True)
        if self.tokenizer.pad_token is None and self.tokenizer.eos_token is not None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        tokenizer_max = getattr(self.tokenizer, "model_max_length", 4096)
        if not isinstance(tokenizer_max, int) or tokenizer_max <= 0 or tokenizer_max > 32768:
            tokenizer_max = 4096

        default_max = min(3072, tokenizer_max)
        self.max_input_tokens = self._env_int("HAPPYBOT_MAX_INPUT_TOKENS", default=default_max, minimum=512)
        self.max_reply_chars = self._env_int("HAPPYBOT_MAX_REPLY_CHARS", default=1800, minimum=400)
        self.num_candidates = self._env_int("HAPPYBOT_REPLY_CANDIDATES", default=2, minimum=1)

        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        base = AutoModelForCausalLM.from_pretrained(
            self.base_model_path,
            torch_dtype=dtype,
            device_map="auto" if torch.cuda.is_available() else None,
        )

        if self.adapter_config_path.exists():
            self.model = PeftModel.from_pretrained(base, self.adapter_path)
        else:
            self.model = base

        self.model.eval()

    def _env_int(self, key: str, default: int, minimum: int = 1) -> int:
        raw = os.getenv(key)
        if raw is None:
            return max(default, minimum)
        try:
            value = int(raw)
        except ValueError:
            return max(default, minimum)
        return max(value, minimum)

    def infer_sentiment(self, message: str) -> str:
        text = message.lower()
        negative = [
            "sad",
            "anxious",
            "depressed",
            "angry",
            "upset",
            "stressed",
            "tired",
            "lonely",
            "burnout",
            "overwhelmed",
            "hopeless",
            "panic",
        ]
        positive = [
            "happy",
            "excited",
            "great",
            "good",
            "amazing",
            "thankful",
            "better",
            "confident",
            "calm",
            "productive",
        ]
        if any(word in text for word in negative):
            return "low"
        if any(word in text for word in positive):
            return "high"
        return "neutral"

    def detect_intent(self, message: str) -> str:
        text = self._normalize_text(message)
        if self._is_farewell(text):
            return "farewell"
        if self._is_gratitude(text):
            return "gratitude"
        if self._is_greeting(text):
            return "greeting"
        if any(k in text for k in ["joke", "funny", "laugh", "meme", "roast"]):
            return "humor"
        if any(k in text for k in ["anxious", "stress", "overwhelmed", "panic", "nervous", "worry", "burnout"]):
            return "anxiety"
        if any(k in text for k in ["sad", "down", "depressed", "lonely", "hopeless", "empty"]):
            return "sadness"
        if any(k in text for k in ["motivate", "goal", "discipline", "productivity", "focus", "study"]):
            return "motivation"
        if any(k in text for k in ["code", "python", "javascript", "bug", "error", "api", "debug", "stack trace"]):
            return "technical"
        return "general"

    def detect_task_type(self, message: str, intent: str | None = None) -> str:
        text = message.lower()
        resolved_intent = intent or self.detect_intent(message)
        if resolved_intent in {"greeting", "gratitude", "farewell"}:
            return "social"
        if any(k in text for k in ["code", "python", "javascript", "bug", "error", "api", "debug", "stack trace"]):
            return "technical"
        if any(k in text for k in ["explain", "what is", "how does", "difference between", "compare"]):
            return "factual"
        if any(k in text for k in ["write", "draft", "caption", "poem", "story", "creative"]):
            return "creative"
        if any(k in text for k in ["sad", "anxious", "stressed", "lonely", "panic", "overwhelmed"]):
            return "emotional_support"
        return "general"

    def generate_reply(self, message: str, history: list[ChatTurn]) -> tuple[str, str, str]:
        sentiment = self.infer_sentiment(message)
        intent = self.detect_intent(message)

        social_reply = self._social_reply(intent)
        if social_reply:
            return social_reply, sentiment, intent

        task_type = self.detect_task_type(message, intent=intent)
        explicit_distress = self._has_explicit_distress(message)
        explicit_fun = self._has_explicit_fun(message)

        messages = [
            {"role": "system", "content": self._system_prompt()},
            {
                "role": "system",
                "content": self._mode_prompt(
                    intent=intent,
                    sentiment=sentiment,
                    task_type=task_type,
                    explicit_distress=explicit_distress,
                    explicit_fun=explicit_fun,
                ),
            },
        ]

        for turn in history[-6:]:
            role = "assistant" if turn.role == "assistant" else "user"
            messages.append({"role": role, "content": turn.text})
        messages.append({"role": "user", "content": message})

        prompt = self._build_prompt(messages)
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_input_tokens,
        )

        if torch.cuda.is_available():
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        profile = self._generation_profile(intent=intent, task_type=task_type)
        candidates = self._generate_candidates(inputs, profile, num_candidates=self.num_candidates)
        raw_reply = self._select_best_candidate(candidates, message=message, intent=intent, task_type=task_type)
        reply = self._postprocess_reply(raw_reply)

        if self._is_low_quality(reply, message=message, intent=intent):
            reply = self._fallback_reply(message=message, intent=intent, task_type=task_type, sentiment=sentiment)

        if not reply:
            reply = "I am here with you. Tell me what you want to solve, and I will help clearly."

        return reply[: self.max_reply_chars].strip(), sentiment, intent

    def _system_prompt(self) -> str:
        return (
            "You are HappyBot, a high-quality assistant with ChatGPT-like response behavior. "
            "Rules: "
            "1) Answer the user's latest message directly in the first sentence. "
            "2) Stay on-topic and avoid generic filler. "
            "3) Be concise, clear, and practical. "
            "4) Use bullets only when helpful. "
            "5) Ask at most one short follow-up question only if needed. "
            "6) Never end the conversation unless the user is clearly saying goodbye. "
            "7) Never say 'you're welcome' unless the user thanked you. "
            "8) Never invent facts; if unsure, state uncertainty and propose a next step."
        )

    def _mode_prompt(
        self,
        intent: str,
        sentiment: str,
        task_type: str,
        explicit_distress: bool,
        explicit_fun: bool,
    ) -> str:
        if explicit_distress or intent in ["sadness", "anxiety"]:
            return (
                "Mode: support. "
                "Start with one validating line. "
                "Then provide 2-3 actionable coping steps. "
                "Use calm tone; avoid therapy jargon."
            )
        if explicit_fun or intent == "humor":
            return (
                "Mode: fun. "
                "Be playful and witty. Keep it light and concise."
            )
        if task_type == "technical":
            return (
                "Mode: technical. "
                "Give precise steps. Prefer concrete fixes, short examples, and exact checks."
            )
        if task_type == "factual":
            return (
                "Mode: factual. "
                "Prioritize accuracy and directness."
            )
        if intent == "motivation":
            return (
                "Mode: motivation. "
                "Give a practical mini-plan user can start immediately."
            )
        if sentiment == "low":
            return (
                "Mode: balanced-supportive. "
                "Be grounding and practical."
            )
        return "Mode: balanced. Direct answer first, then concise helpful detail."

    def _generation_profile(self, intent: str, task_type: str) -> GenerationProfile:
        if intent == "humor":
            return GenerationProfile(
                max_new_tokens=200,
                temperature=0.9,
                top_p=0.94,
                repetition_penalty=1.06,
                do_sample=True,
            )
        if task_type in {"technical", "factual"}:
            return GenerationProfile(
                max_new_tokens=220,
                temperature=0.5,
                top_p=0.82,
                repetition_penalty=1.12,
                do_sample=True,
            )
        if intent in {"anxiety", "sadness"} or task_type == "emotional_support":
            return GenerationProfile(
                max_new_tokens=220,
                temperature=0.62,
                top_p=0.88,
                repetition_penalty=1.1,
                do_sample=True,
            )
        return GenerationProfile(
            max_new_tokens=210,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.08,
            do_sample=True,
        )

    def _generate_candidates(
        self,
        inputs: dict[str, torch.Tensor],
        profile: GenerationProfile,
        num_candidates: int,
    ) -> list[str]:
        num_sequences = max(1, min(num_candidates, 3))
        if not profile.do_sample:
            num_sequences = 1

        generation_kwargs = {
            "max_new_tokens": profile.max_new_tokens,
            "do_sample": profile.do_sample,
            "temperature": profile.temperature,
            "top_p": profile.top_p,
            "repetition_penalty": profile.repetition_penalty,
            "no_repeat_ngram_size": 3,
            "eos_token_id": self.tokenizer.eos_token_id,
            "pad_token_id": self.tokenizer.pad_token_id,
        }
        if num_sequences > 1:
            generation_kwargs["num_return_sequences"] = num_sequences

        with torch.inference_mode():
            output = self.model.generate(**inputs, **generation_kwargs)

        if output.dim() == 1:
            output = output.unsqueeze(0)

        input_len = inputs["input_ids"].shape[-1]
        candidates: list[str] = []
        for idx in range(output.shape[0]):
            generated = output[idx][input_len:]
            text = self.tokenizer.decode(generated, skip_special_tokens=True).strip()
            if text:
                candidates.append(text)
        return candidates or [""]

    def _select_best_candidate(
        self,
        candidates: list[str],
        message: str,
        intent: str,
        task_type: str,
    ) -> str:
        if len(candidates) == 1:
            return candidates[0]

        scored = [
            (self._score_candidate(candidate, message=message, intent=intent, task_type=task_type), candidate)
            for candidate in candidates
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1]

    def _score_candidate(self, candidate: str, message: str, intent: str, task_type: str) -> float:
        if not candidate.strip():
            return -100.0

        text = self._postprocess_reply(candidate)
        lowered = text.lower()
        score = 0.0

        length = len(text)
        if 70 <= length <= 900:
            score += 4.0
        elif length < 30:
            score -= 8.0
        elif length > 1400:
            score -= 2.0

        if self._looks_like_signoff(lowered) and intent != "farewell":
            score -= 8.0
        if self._looks_like_gratitude_reply(lowered) and intent != "gratitude":
            score -= 6.0

        if any(marker in lowered for marker in ["as an ai", "language model"]):
            score -= 4.0

        if task_type == "technical" and not any(k in lowered for k in ["step", "check", "try", "fix"]):
            score -= 2.0

        question_count = text.count("?")
        if question_count > 2:
            score -= 1.5

        message_terms = self._content_terms(message)
        candidate_terms = self._content_terms(text)
        overlap = len(message_terms.intersection(candidate_terms))
        score += min(float(overlap), 4.0)

        words = re.findall(r"[a-zA-Z']+", lowered)
        if len(words) >= 10:
            unique_ratio = len(set(words)) / max(len(words), 1)
            if unique_ratio < 0.38:
                score -= 3.0

        return score

    def _content_terms(self, text: str) -> set[str]:
        tokens = re.findall(r"[a-zA-Z]{4,}", text.lower())
        stop = {
            "this",
            "that",
            "with",
            "from",
            "your",
            "what",
            "when",
            "where",
            "have",
            "about",
            "would",
            "could",
            "should",
            "really",
            "please",
            "just",
            "want",
            "need",
            "help",
            "like",
        }
        return {token for token in tokens if token not in stop}

    def _is_low_quality(self, reply: str, message: str, intent: str) -> bool:
        text = reply.strip()
        if not text:
            return True

        lowered = text.lower()
        word_count = len(re.findall(r"[a-zA-Z']+", lowered))

        if word_count < 5:
            return True
        if "match your vibe" in lowered:
            return True
        if self._looks_like_signoff(lowered) and intent != "farewell":
            return True
        if self._looks_like_gratitude_reply(lowered) and intent != "gratitude":
            return True

        message_terms = self._content_terms(message)
        if message_terms:
            overlap = len(message_terms.intersection(self._content_terms(text)))
            if overlap == 0 and word_count < 25:
                return True

        return False

    def _fallback_reply(self, message: str, intent: str, task_type: str, sentiment: str) -> str:
        if intent == "anxiety":
            return (
                "That sounds stressful. Let us make it manageable:\n"
                "1. Do 4-7-8 breathing for 60 seconds.\n"
                "2. Write what you can control in the next hour.\n"
                "3. Start one small 10-minute action now.\n"
                "If you want, share the exact trigger and I will tailor this."
            )
        if intent == "sadness" or sentiment == "low":
            return (
                "I hear you. Let us keep this simple and gentle:\n"
                "1. Name what you feel in one sentence.\n"
                "2. Take 5 slow breaths and relax your shoulders.\n"
                "3. Do one kind, low-effort action for yourself in the next hour."
            )
        if task_type == "technical":
            return (
                "I can help you debug this quickly.\n"
                "1. Share the exact error message.\n"
                "2. Share the smallest code snippet that reproduces it.\n"
                "3. Tell me expected output vs actual output.\n"
                "Then I will give you a precise fix."
            )
        if intent == "motivation":
            return (
                "Let us make momentum now:\n"
                "1. Pick one task you can finish in 10 minutes.\n"
                "2. Set a 25-minute focus timer.\n"
                "3. Start immediately, then report progress."
            )
        if task_type == "factual":
            return (
                "Good question. I can give a direct answer, but I need one line of context so I do not guess."
            )
        return (
            "Got it. Tell me your exact goal and constraints in one or two lines, and I will give you a clear, no-fluff plan."
        )

    def _has_explicit_distress(self, message: str) -> bool:
        text = message.lower()
        cues = [
            "i am sad",
            "i'm sad",
            "i feel sad",
            "i am anxious",
            "i'm anxious",
            "i feel anxious",
            "i am depressed",
            "i'm depressed",
            "i feel depressed",
            "i feel lonely",
            "i am stressed",
            "i'm stressed",
            "panic",
            "overwhelmed",
            "hopeless",
        ]
        return any(cue in text for cue in cues)

    def _has_explicit_fun(self, message: str) -> bool:
        text = message.lower()
        cues = ["joke", "funny", "laugh", "roast", "meme", "banter", "fun mode"]
        return any(cue in text for cue in cues)

    def _normalize_text(self, message: str) -> str:
        lowered = message.lower().strip()
        cleaned = re.sub(r"[^a-z0-9'\s]", " ", lowered)
        return re.sub(r"\s+", " ", cleaned).strip()

    def _is_greeting(self, normalized: str) -> bool:
        greetings = {
            "hi",
            "hii",
            "hiii",
            "hello",
            "hey",
            "hey there",
            "hi there",
            "hello there",
            "yo",
            "sup",
            "whats up",
            "what's up",
            "good morning",
            "good afternoon",
            "good evening",
        }
        if normalized in greetings:
            return True
        tokens = normalized.split()
        return bool(tokens and tokens[0] in {"hi", "hii", "hiii", "hello", "hey", "yo"} and len(tokens) <= 3)

    def _is_gratitude(self, normalized: str) -> bool:
        gratitude = {
            "thanks",
            "thank you",
            "thankyou",
            "thanks a lot",
            "thank you so much",
            "much appreciated",
            "appreciate it",
            "thx",
            "ty",
        }
        if normalized in gratitude:
            return True
        tokens = normalized.split()
        return bool(tokens and tokens[0] in {"thanks", "thankyou", "thx", "ty"} and len(tokens) <= 4)

    def _is_farewell(self, normalized: str) -> bool:
        farewells = {
            "bye",
            "goodbye",
            "see you",
            "see you later",
            "see ya",
            "cya",
            "talk to you later",
            "catch you later",
            "good night",
            "take care",
            "ttyl",
        }
        if normalized in farewells:
            return True
        tokens = normalized.split()
        return bool(tokens and tokens[0] in {"bye", "goodbye", "cya", "ttyl"} and len(tokens) <= 4)

    def _social_reply(self, intent: str) -> str | None:
        if intent == "greeting":
            return "Hey! Good to see you. What do you want help with right now?"
        if intent == "gratitude":
            return "You're welcome. Glad it helped. If you want, we can keep going."
        if intent == "farewell":
            return "Anytime. Take care, and come back whenever you want to chat."
        return None

    def _looks_like_signoff(self, lowered_text: str) -> bool:
        signoff_cues = [
            "take care",
            "see you",
            "goodbye",
            "come back anytime",
            "talk to you later",
        ]
        return any(cue in lowered_text for cue in signoff_cues)

    def _looks_like_gratitude_reply(self, lowered_text: str) -> bool:
        gratitude_cues = [
            "you're welcome",
            "you are welcome",
            "glad it helped",
            "happy to help",
        ]
        return any(cue in lowered_text for cue in gratitude_cues)

    def _postprocess_reply(self, text: str) -> str:
        if not text:
            return ""

        cleaned = text.replace("\r", "").strip()
        lowered = cleaned.lower()

        for prefix in ("assistant:", "happybot:", "bot:", "ai:"):
            if lowered.startswith(prefix):
                cleaned = cleaned[len(prefix) :].strip()
                lowered = cleaned.lower()
                break

        stop_markers = [
            "\nUSER:",
            "\nUser:",
            "\nSYSTEM:",
            "\nSystem:",
            "\nASSISTANT:",
            "\nAssistant:",
            "\nHAPPYBOT:",
        ]
        cut_positions = [cleaned.find(marker) for marker in stop_markers if marker in cleaned]
        if cut_positions:
            cleaned = cleaned[: min(cut_positions)].strip()

        lines = [line.rstrip() for line in cleaned.splitlines()]
        deduped_lines: list[str] = []
        prev_normalized = ""
        for line in lines:
            normalized = re.sub(r"\s+", " ", line.strip().lower())
            if not normalized:
                if deduped_lines and deduped_lines[-1] != "":
                    deduped_lines.append("")
                continue
            if normalized == prev_normalized:
                continue
            deduped_lines.append(line.strip())
            prev_normalized = normalized

        cleaned = "\n".join(deduped_lines).strip()
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        return cleaned

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
