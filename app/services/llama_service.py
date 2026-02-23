from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import random
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

        default_max = min(2048, tokenizer_max)
        self.max_input_tokens = self._env_int("HAPPYBOT_MAX_INPUT_TOKENS", default=default_max, minimum=512)
        self.max_reply_chars = self._env_int("HAPPYBOT_MAX_REPLY_CHARS", default=1800, minimum=400)
        self.num_candidates = self._env_int("HAPPYBOT_REPLY_CANDIDATES", default=1, minimum=1)
        self.humor_num_candidates = self._env_int("HAPPYBOT_HUMOR_CANDIDATES", default=4, minimum=3)
        self._use_cuda = torch.cuda.is_available()
        if self._use_cuda:
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True

        dtype = torch.float16 if self._use_cuda else torch.float32
        base = AutoModelForCausalLM.from_pretrained(
            self.base_model_path,
            torch_dtype=dtype,
            device_map="auto" if self._use_cuda else None,
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
            "heartbreak",
            "heartbroken",
            "grief",
            "grieving",
            "loss",
            "breakup",
            "broke up",
            "betrayed",
            "hurt",
            "pain",
            "alone",
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
            "relieved",
            "proud",
            "hopeful",
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
        if any(
            k in text
            for k in [
                "joke",
                "funny",
                "laugh",
                "meme",
                "roast",
                "cheer me up",
                "lighten my mood",
                "lift my mood",
                "mood up",
                "make me smile",
                "make my mood better",
                "crack me up",
            ]
        ):
            return "humor"
        if any(k in text for k in ["anxious", "stress", "overwhelmed", "panic", "nervous", "worry", "burnout"]):
            return "anxiety"
        if any(
            k in text
            for k in [
                "sad",
                "down",
                "depressed",
                "lonely",
                "hopeless",
                "empty",
                "heartbreak",
                "heartbroken",
                "grief",
                "breakup",
                "broke up",
                "betrayed",
                "hurt",
            ]
        ):
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
        if any(
            k in text
            for k in [
                "sad",
                "anxious",
                "stressed",
                "lonely",
                "panic",
                "overwhelmed",
                "heartbreak",
                "heartbroken",
                "grief",
                "breakup",
                "broke up",
                "betrayed",
            ]
        ):
            return "emotional_support"
        return "general"

    def generate_reply(self, message: str, history: list[ChatTurn]) -> tuple[str, str, str]:
        sentiment = self.infer_sentiment(message)
        intent = self.detect_intent(message)

        task_type = self.detect_task_type(message, intent=intent)
        explicit_distress = self._has_explicit_distress(message)
        explicit_fun = self._has_explicit_fun(message)
        humor_request = intent == "humor" or explicit_fun
        quality_intent = "humor" if humor_request else intent
        humor_topic = self._extract_humor_topic(message) if humor_request else ""
        humor_style = self._pick_humor_style() if humor_request else ""

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
        if humor_request:
            messages.append({"role": "system", "content": self._humor_prompt(topic=humor_topic, style=humor_style)})

        for turn in history[-6:]:
            role = "assistant" if turn.role == "assistant" else "user"
            messages.append({"role": role, "content": turn.text})
        messages.append({"role": "user", "content": message})

        profile = self._generation_profile(intent=intent, task_type=task_type, humor_request=humor_request)
        candidate_count = self.num_candidates
        if humor_request:
            candidate_count = max(candidate_count, self.humor_num_candidates)
            candidate_count = min(candidate_count, 4)

        reply = self._generate_from_messages(
            messages=messages,
            profile=profile,
            message=message,
            intent=intent,
            task_type=task_type,
            num_candidates=candidate_count,
            prefer_humor=humor_request,
            humor_topic=humor_topic,
        )

        if humor_request and self._is_weak_humor(reply, humor_topic=humor_topic):
            punchup_messages = messages + [{"role": "system", "content": self._humor_retry_prompt(topic=humor_topic)}]
            punchup_profile = GenerationProfile(
                max_new_tokens=165,
                temperature=1.12,
                top_p=0.98,
                repetition_penalty=1.03,
                do_sample=True,
            )
            punchup_reply = self._generate_from_messages(
                messages=punchup_messages,
                profile=punchup_profile,
                message=message,
                intent=intent,
                task_type=task_type,
                num_candidates=min(max(3, self.humor_num_candidates), 4),
                prefer_humor=True,
                humor_topic=humor_topic,
            )
            if punchup_reply and not self._is_weak_humor(punchup_reply, humor_topic=humor_topic):
                reply = punchup_reply
        if humor_request and self._is_weak_humor(reply, humor_topic=humor_topic):
            rerolled = self._reroll_humor(
                message=message,
                history=history,
                humor_topic=humor_topic,
                intent=intent,
                task_type=task_type,
            )
            if rerolled:
                reply = rerolled

        if self._is_low_quality(reply, message=message, intent=quality_intent):
            rescued = self._generate_quality_rescue(
                message=message,
                history=history,
                intent=intent,
                task_type=task_type,
                sentiment=sentiment,
                humor_request=humor_request,
                humor_topic=humor_topic,
                aggressive=False,
            )
            if rescued:
                reply = rescued

        if not reply or self._is_low_quality(reply, message=message, intent=quality_intent):
            rescued = self._generate_quality_rescue(
                message=message,
                history=history,
                intent=intent,
                task_type=task_type,
                sentiment=sentiment,
                humor_request=humor_request,
                humor_topic=humor_topic,
                aggressive=True,
            )
            if rescued:
                reply = rescued

        if not reply:
            emergency_messages = [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": message},
            ]
            emergency_profile = GenerationProfile(
                max_new_tokens=180,
                temperature=0.92,
                top_p=0.95,
                repetition_penalty=1.06,
                do_sample=True,
            )
            reply = self._generate_from_messages(
                messages=emergency_messages,
                profile=emergency_profile,
                message=message,
                intent=intent,
                task_type=task_type,
                num_candidates=2,
                prefer_humor=humor_request,
                humor_topic=humor_topic,
            )

        return reply[: self.max_reply_chars].strip(), sentiment, intent

    def _system_prompt(self) -> str:
        return (
            "You are HappyBot, a high-quality conversational assistant with ChatGPT-like response behavior. "
            "Rules: "
            "1) Understand the exact user intent and respond directly in the first line. "
            "2) Stay specific to the user's message and avoid generic filler. "
            "3) Keep tone natural, warm, and human. "
            "4) Be concise but complete; use bullets only if they add clarity. "
            "5) Ask at most one useful follow-up question when needed. "
            "6) Do not end the conversation unless the user clearly says goodbye. "
            "7) Do not invent facts; if uncertain, say so and give a useful next step."
        )

    def _mode_prompt(
        self,
        intent: str,
        sentiment: str,
        task_type: str,
        explicit_distress: bool,
        explicit_fun: bool,
    ) -> str:
        if explicit_fun or intent == "humor":
            return (
                "Mode: fun. "
                "Be playful and witty. Deliver one original joke with sharp setup and punchline. "
                "Keep it clean, surprising, topic-specific, and genuinely funny."
            )
        if explicit_distress or intent in {"sadness", "anxiety"} or task_type == "emotional_support":
            return (
                "Mode: emotional-support. "
                "Acknowledge the user's specific feeling in one line without sounding scripted. "
                "Then give grounded, situation-specific support that matches what they said. "
                "If useful, offer 1-3 practical next steps with brief rationale. "
                "Sound calm, warm, and human."
            )
        if intent in {"greeting", "gratitude", "farewell"}:
            return (
                "Mode: social. "
                "Reply naturally in 1-3 sentences and stay open for continued conversation."
            )
        if task_type == "technical":
            return (
                "Mode: technical. "
                "Give precise, step-by-step guidance. Prefer concrete fixes and exact checks."
            )
        if task_type == "factual":
            return (
                "Mode: factual. "
                "Prioritize accuracy, directness, and clear explanation."
            )
        if intent == "motivation":
            return (
                "Mode: motivation. "
                "Give an encouraging but practical mini-plan the user can start immediately."
            )
        if sentiment == "low":
            return (
                "Mode: balanced-supportive. "
                "Be grounding, practical, and context-aware."
            )
        return "Mode: balanced. Direct answer first, then concise helpful detail."

    def _generation_profile(self, intent: str, task_type: str, humor_request: bool = False) -> GenerationProfile:
        if humor_request or intent == "humor":
            return GenerationProfile(
                max_new_tokens=165,
                temperature=1.08,
                top_p=0.97,
                repetition_penalty=1.04,
                do_sample=True,
            )
        if task_type in {"technical", "factual"}:
            return GenerationProfile(
                max_new_tokens=170,
                temperature=0.58,
                top_p=0.9,
                repetition_penalty=1.12,
                do_sample=True,
            )
        if intent in {"anxiety", "sadness"} or task_type == "emotional_support":
            return GenerationProfile(
                max_new_tokens=190,
                temperature=0.74,
                top_p=0.93,
                repetition_penalty=1.08,
                do_sample=True,
            )
        return GenerationProfile(
            max_new_tokens=180,
            temperature=0.78,
            top_p=0.93,
            repetition_penalty=1.07,
            do_sample=True,
        )

    def _generate_from_messages(
        self,
        messages: list[dict],
        profile: GenerationProfile,
        message: str,
        intent: str,
        task_type: str,
        num_candidates: int,
        prefer_humor: bool = False,
        humor_topic: str = "",
    ) -> str:
        prompt = self._build_prompt(messages)
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_input_tokens,
        )

        if self._use_cuda:
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        candidates = self._generate_candidates(inputs, profile, num_candidates=num_candidates)
        raw_reply = self._select_best_candidate(
            candidates,
            message=message,
            intent=intent,
            task_type=task_type,
            prefer_humor=prefer_humor,
            humor_topic=humor_topic,
        )
        reply = self._postprocess_reply(raw_reply)
        if reply:
            return reply

        # Retry once with deterministic decoding to avoid empty sampled outputs.
        if profile.do_sample:
            deterministic_profile = GenerationProfile(
                max_new_tokens=profile.max_new_tokens,
                temperature=profile.temperature,
                top_p=profile.top_p,
                repetition_penalty=profile.repetition_penalty,
                do_sample=False,
            )
            deterministic_candidates = self._generate_candidates(inputs, deterministic_profile, num_candidates=1)
            deterministic_raw = self._select_best_candidate(
                deterministic_candidates,
                message=message,
                intent=intent,
                task_type=task_type,
                prefer_humor=prefer_humor,
                humor_topic=humor_topic,
            )
            return self._postprocess_reply(deterministic_raw)

        return ""

    def _generate_candidates(
        self,
        inputs: dict[str, torch.Tensor],
        profile: GenerationProfile,
        num_candidates: int,
    ) -> list[str]:
        num_sequences = max(1, min(num_candidates, 4))
        if not profile.do_sample:
            num_sequences = 1

        generation_kwargs = {
            "max_new_tokens": profile.max_new_tokens,
            "do_sample": profile.do_sample,
            "repetition_penalty": profile.repetition_penalty,
            "no_repeat_ngram_size": 3,
            "use_cache": True,
            "eos_token_id": self.tokenizer.eos_token_id,
            "pad_token_id": self.tokenizer.pad_token_id,
        }
        if profile.do_sample:
            generation_kwargs["temperature"] = profile.temperature
            generation_kwargs["top_p"] = profile.top_p
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
        prefer_humor: bool = False,
        humor_topic: str = "",
    ) -> str:
        if len(candidates) == 1:
            return candidates[0]

        scored = [
            (
                self._score_candidate(
                    candidate,
                    message=message,
                    intent=intent,
                    task_type=task_type,
                    prefer_humor=prefer_humor,
                    humor_topic=humor_topic,
                ),
                candidate,
            )
            for candidate in candidates
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1]

    def _score_candidate(
        self,
        candidate: str,
        message: str,
        intent: str,
        task_type: str,
        prefer_humor: bool = False,
        humor_topic: str = "",
    ) -> float:
        if not candidate.strip():
            return -100.0

        text = self._postprocess_reply(candidate)
        lowered = text.lower()
        score = 0.0

        length = len(text)
        if 45 <= length <= 900:
            score += 4.0
        elif length < 24:
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
        if intent in {"sadness", "anxiety"}:
            if not any(k in lowered for k in ["that sounds", "i hear", "i'm sorry", "i am sorry", "that hurts"]):
                score -= 1.2
            if any(k in lowered for k in ["goal and constraints", "no-fluff plan"]):
                score -= 6.0

        if prefer_humor:
            score += self._humor_score(text=text, humor_topic=humor_topic)

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

    def _humor_score(self, text: str, humor_topic: str) -> float:
        lowered = text.lower()
        words = re.findall(r"[a-zA-Z']+", lowered)
        score = 0.0

        if 16 <= len(words) <= 88:
            score += 2.0
        elif len(words) < 10:
            score -= 4.0
        elif len(words) > 130:
            score -= 1.5

        if any(sep in text for sep in ["\n", " - ", ":"]):
            score += 0.8

        twist_cues = ["but", "until", "then", "turns out", "instead", "plot twist", "suddenly", "except"]
        if any(cue in lowered for cue in twist_cues):
            score += 1.1

        if re.search(r"^\s*\d+\.", text, flags=re.MULTILINE):
            score -= 4.0

        stale_cues = [
            "why did the chicken cross the road",
            "knock knock",
            "as an ai",
            "sorry i can't",
            "sorry, i can't",
            "here's one",
            "here is one",
            "hope this helps",
            "hope this made you smile",
            "if you want another",
        ]
        if any(cue in lowered for cue in stale_cues):
            score -= 6.0

        topic_terms = self._content_terms(humor_topic)
        if topic_terms and humor_topic.strip().lower() not in {"everyday life", "general"}:
            overlap = len(topic_terms.intersection(self._content_terms(text)))
            score += min(float(overlap) * 1.8, 4.5)
            if overlap == 0:
                score -= 4.0

        return score

    def _is_weak_humor(self, reply: str, humor_topic: str) -> bool:
        text = (reply or "").strip()
        if not text:
            return True

        lowered = text.lower()
        words = re.findall(r"[a-zA-Z']+", lowered)
        if len(words) < 12:
            return True
        if len(words) > 140:
            return True

        weak_cues = [
            "as an ai",
            "i can't",
            "i cannot",
            "sorry",
            "here's a joke",
            "let me know if you want another",
            "hope this helps",
            "hope this made you smile",
            "i hope this",
        ]
        if any(cue in lowered for cue in weak_cues):
            return True

        stale_cues = ["why did the chicken cross the road", "knock knock"]
        if any(cue in lowered for cue in stale_cues):
            return True
        if re.search(r"^\s*\d+\.", text, flags=re.MULTILINE):
            return True

        topic_terms = self._content_terms(humor_topic)
        if topic_terms and humor_topic.strip().lower() not in {"everyday life", "general"}:
            overlap = len(topic_terms.intersection(self._content_terms(text)))
            if overlap == 0:
                return True

        return False

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
        emotional_input = intent in {"sadness", "anxiety"} or self._has_explicit_distress(message)

        if word_count < 4:
            return True
        if any(marker in lowered for marker in ["match your vibe", "goal and constraints", "clear, no-fluff plan"]):
            return True
        if self._looks_like_signoff(lowered) and intent != "farewell":
            return True
        if self._looks_like_gratitude_reply(lowered) and intent != "gratitude":
            return True
        if any(marker in lowered for marker in ["as an ai", "language model"]):
            return True

        if intent == "humor":
            return self._is_weak_humor(text, humor_topic=self._extract_humor_topic(message))

        if emotional_input:
            if word_count < 10:
                return True
            if any(marker in lowered for marker in ["just breathe and relax", "everything will be fine"]):
                return True
            return False

        message_terms = self._content_terms(message)
        if message_terms:
            overlap = len(message_terms.intersection(self._content_terms(text)))
            if overlap == 0 and word_count < 40:
                return True

        return False

    def _generate_quality_rescue(
        self,
        message: str,
        history: list[ChatTurn],
        intent: str,
        task_type: str,
        sentiment: str,
        humor_request: bool,
        humor_topic: str,
        aggressive: bool = False,
    ) -> str:
        rescue_messages: list[dict] = [
            {"role": "system", "content": self._system_prompt()},
            {
                "role": "system",
                "content": self._mode_prompt(
                    intent=intent,
                    sentiment=sentiment,
                    task_type=task_type,
                    explicit_distress=self._has_explicit_distress(message),
                    explicit_fun=humor_request,
                ),
            },
            {
                "role": "system",
                "content": (
                    "Quality pass: produce a high-quality response to the latest user message. "
                    "Be specific to the message, natural in tone, and avoid generic boilerplate."
                ),
            },
        ]
        if aggressive:
            rescue_messages.append(
                {
                    "role": "system",
                    "content": (
                        "Second pass: tighten relevance further, be more concrete, and avoid repeating earlier wording."
                    ),
                }
            )
        if humor_request:
            rescue_messages.append({"role": "system", "content": self._humor_prompt(topic=humor_topic, style=self._pick_humor_style())})

        for turn in history[-4:]:
            role = "assistant" if turn.role == "assistant" else "user"
            rescue_messages.append({"role": role, "content": turn.text})
        rescue_messages.append({"role": "user", "content": message})

        profile = GenerationProfile(
            max_new_tokens=190 if intent in {"sadness", "anxiety"} or task_type == "emotional_support" else 170,
            temperature=0.9 if aggressive else 0.78,
            top_p=0.95 if aggressive else 0.92,
            repetition_penalty=1.06,
            do_sample=True,
        )
        num_candidates = 2 if aggressive else 1
        if humor_request:
            num_candidates = min(max(num_candidates, self.humor_num_candidates), 4)

        reply = self._generate_from_messages(
            messages=rescue_messages,
            profile=profile,
            message=message,
            intent=intent,
            task_type=task_type,
            num_candidates=num_candidates,
            prefer_humor=humor_request,
            humor_topic=humor_topic,
        )
        if not reply:
            return ""
        if humor_request and self._is_weak_humor(reply, humor_topic=humor_topic):
            return ""
        return reply

    def _reroll_humor(
        self,
        message: str,
        history: list[ChatTurn],
        humor_topic: str,
        intent: str,
        task_type: str,
    ) -> str:
        best_reply = ""
        best_score = float("-inf")
        topic = humor_topic or self._extract_humor_topic(message)

        for _ in range(2):
            style = self._pick_humor_style()
            reroll_messages = [
                {"role": "system", "content": self._system_prompt()},
                {
                    "role": "system",
                    "content": (
                        "Mode: mood-lift humor. "
                        "Write one genuinely funny, original joke to lift the user's mood. "
                        "Use sharp misdirection, specific details, and a strong final punchline."
                    ),
                },
                {"role": "system", "content": self._humor_prompt(topic=topic, style=style)},
                {
                    "role": "system",
                    "content": (
                        "Output only the joke. "
                        "No explanation, no apology, no extra commentary before or after."
                    ),
                },
            ]
            for turn in history[-3:]:
                role = "assistant" if turn.role == "assistant" else "user"
                reroll_messages.append({"role": role, "content": turn.text})
            reroll_messages.append({"role": "user", "content": message})

            profile = GenerationProfile(
                max_new_tokens=165,
                temperature=1.14,
                top_p=0.98,
                repetition_penalty=1.03,
                do_sample=True,
            )
            candidate = self._generate_from_messages(
                messages=reroll_messages,
                profile=profile,
                message=message,
                intent=intent,
                task_type=task_type,
                num_candidates=min(max(3, self.humor_num_candidates), 4),
                prefer_humor=True,
                humor_topic=topic,
            )
            if not candidate:
                continue
            score = self._score_candidate(
                candidate,
                message=message,
                intent="humor",
                task_type="creative",
                prefer_humor=True,
                humor_topic=topic,
            )
            if score > best_score:
                best_score = score
                best_reply = candidate
            if not self._is_weak_humor(candidate, humor_topic=topic) and score >= 3.2:
                return candidate

        if best_reply and not self._is_weak_humor(best_reply, humor_topic=topic):
            return best_reply
        return ""

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
            "heartbreak",
            "heartbroken",
            "grief",
            "grieving",
            "breakup",
            "broke up",
            "betrayed",
            "lost someone",
            "loss",
        ]
        return any(cue in text for cue in cues)

    def _has_explicit_fun(self, message: str) -> bool:
        text = message.lower()
        cues = [
            "joke",
            "funny",
            "laugh",
            "roast",
            "meme",
            "banter",
            "fun mode",
            "make me laugh",
            "crack me up",
            "cheer me up",
            "lighten my mood",
            "lift my mood",
            "make me smile",
        ]
        return any(cue in text for cue in cues)

    def _extract_humor_topic(self, message: str) -> str:
        text = (message or "").strip()
        lowered = text.lower()
        patterns = [
            r"(?:joke|roast|funny)\s+(?:about|on|regarding)\s+(.+?)(?:[?.!]|$)",
            r"(?:cheer me up with|lighten my mood with|make me laugh with)\s+(.+?)(?:[?.!]|$)",
            r"(?:about|on|regarding)\s+(.+?)(?:[?.!]|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match:
                candidate = match.group(1).strip()
                candidate = re.sub(r"\b(please|pls|for me|right now|now)\b", "", candidate).strip()
                candidate = re.sub(r"[^a-z0-9'\s-]", " ", candidate)
                candidate = re.sub(r"\s+", " ", candidate).strip()
                if candidate:
                    return candidate[:80]

        stopwords = {
            "tell",
            "make",
            "give",
            "write",
            "joke",
            "funny",
            "laugh",
            "roast",
            "meme",
            "about",
            "regarding",
            "please",
            "something",
            "anything",
            "lighten",
            "mood",
            "cheer",
            "smile",
        }
        tokens = re.findall(r"[a-zA-Z]{3,}", lowered)
        topical = [token for token in tokens if token not in stopwords]
        if topical:
            return " ".join(topical[:4])
        return "everyday life"

    def _pick_humor_style(self) -> str:
        styles = (
            "observational with an absurd twist",
            "dry sarcasm with a playful punchline",
            "fast one-liner with smart wordplay",
            "mini-story escalation ending in a twist",
            "light roast tone without being mean",
            "deadpan build-up with chaotic final reveal",
            "relatable everyday scenario that spirals into absurdity",
            "self-aware witty banter with a sharp callback punchline",
        )
        return random.choice(styles)

    def _humor_prompt(self, topic: str, style: str) -> str:
        resolved_topic = topic or "everyday life"
        resolved_style = style or "observational with an absurd twist"
        return (
            "Humor constraints: "
            f"Create one fresh, original joke about '{resolved_topic}'. "
            f"Style: {resolved_style}. "
            "Use setup then punchline in 2-4 short lines. "
            "Keep it clean, specific, vivid, and surprising. "
            "Prefer misdirection, escalation, and a strong final punchline. "
            "Do not use recycled classics, apologies, or explanations."
        )

    def _humor_retry_prompt(self, topic: str) -> str:
        resolved_topic = topic or "everyday life"
        return (
            "Punch-up pass: rewrite the joke to be funnier. "
            f"Keep the topic '{resolved_topic}'. "
            "Increase surprise, sharpen the final punchline, and remove boring wording. "
            "Stay concise and output only the final joke."
        )

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
