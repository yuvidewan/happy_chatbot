from __future__ import annotations

from dataclasses import dataclass
import os
import re

try:
    from huggingface_hub import InferenceClient
except ImportError:  # pragma: no cover - defensive for partial installs
    InferenceClient = None

from app.services.llama_service import ChatTurn


@dataclass
class HostedGenerationProfile:
    max_new_tokens: int
    temperature: float
    top_p: float
    repetition_penalty: float
    do_sample: bool = True


class HostedLlamaModel:
    def __init__(self):
        if InferenceClient is None:
            raise FileNotFoundError(
                "Hosted backend requires huggingface_hub. "
                "Install requirements-hosted.txt or requirements.txt."
            )

        token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
        if not token:
            raise FileNotFoundError(
                "Hosted backend requires HF_TOKEN (or HUGGINGFACEHUB_API_TOKEN)."
            )

        self.model_id = os.getenv("HAPPYBOT_HOSTED_MODEL_ID", "mistralai/Mistral-7B-Instruct-v0.2")
        timeout_seconds = self._env_int("HAPPYBOT_HOSTED_TIMEOUT_SECONDS", default=90, minimum=10)
        self.client = InferenceClient(model=self.model_id, token=token, timeout=timeout_seconds)
        self.max_reply_chars = self._env_int("HAPPYBOT_MAX_REPLY_CHARS", default=1800, minimum=400)
        self.max_input_chars = self._env_int("HAPPYBOT_HOSTED_MAX_INPUT_CHARS", default=5000, minimum=1000)

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
        if any(k in text for k in ["joke", "funny", "laugh", "meme", "roast", "cheer me up", "make me smile"]):
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

        messages = [
            {"role": "system", "content": self._system_prompt()},
            {"role": "system", "content": self._mode_prompt(intent=intent, sentiment=sentiment, task_type=task_type)},
        ]

        for turn in history[-6:]:
            role = "assistant" if turn.role == "assistant" else "user"
            messages.append({"role": role, "content": turn.text})
        messages.append({"role": "user", "content": message})

        profile = self._generation_profile(intent=intent, task_type=task_type)
        reply = self._generate_from_messages(messages=messages, profile=profile)
        if not reply:
            reply = self._fallback_reply(intent=intent, sentiment=sentiment)

        return reply[: self.max_reply_chars].strip(), sentiment, intent

    def _system_prompt(self) -> str:
        return (
            "You are HappyBot, a warm and practical assistant. "
            "Answer directly, stay relevant to the user message, and avoid generic filler. "
            "Do not claim to be a therapist; provide supportive, actionable guidance."
        )

    def _mode_prompt(self, intent: str, sentiment: str, task_type: str) -> str:
        if intent == "humor":
            return "Mode: humor. Give one original clean joke with setup and punchline."
        if intent in {"sadness", "anxiety"} or task_type == "emotional_support":
            return "Mode: emotional support. Acknowledge feelings and suggest 1-3 concrete next steps."
        if task_type == "technical":
            return "Mode: technical. Give precise step-by-step troubleshooting advice."
        if intent in {"greeting", "gratitude", "farewell"}:
            return "Mode: social. Reply naturally in 1-3 sentences."
        if sentiment == "low":
            return "Mode: grounded support. Keep tone calm and practical."
        return "Mode: balanced. Direct answer first, concise details next."

    def _generation_profile(self, intent: str, task_type: str) -> HostedGenerationProfile:
        if intent == "humor":
            return HostedGenerationProfile(
                max_new_tokens=165,
                temperature=1.0,
                top_p=0.96,
                repetition_penalty=1.04,
                do_sample=True,
            )
        if task_type in {"technical", "factual"}:
            return HostedGenerationProfile(
                max_new_tokens=180,
                temperature=0.6,
                top_p=0.9,
                repetition_penalty=1.1,
                do_sample=True,
            )
        return HostedGenerationProfile(
            max_new_tokens=185,
            temperature=0.78,
            top_p=0.93,
            repetition_penalty=1.07,
            do_sample=True,
        )

    def _generate_from_messages(self, messages: list[dict], profile: HostedGenerationProfile) -> str:
        prompt = self._build_prompt(messages)
        if len(prompt) > self.max_input_chars:
            prompt = prompt[-self.max_input_chars :]

        try:
            raw_reply = self.client.text_generation(
                prompt=prompt,
                max_new_tokens=profile.max_new_tokens,
                do_sample=profile.do_sample,
                temperature=profile.temperature,
                top_p=profile.top_p,
                repetition_penalty=profile.repetition_penalty,
                return_full_text=False,
                stop=["\nUSER:", "\nSYSTEM:", "\nASSISTANT:"],
            )
        except Exception as exc:
            raise RuntimeError(
                "Hosted inference request failed. Verify HF token/model/network and try again."
            ) from exc

        return self._postprocess_reply(str(raw_reply))

    def _fallback_reply(self, intent: str, sentiment: str) -> str:
        if intent == "humor":
            return "Quick mood boost: Why did the calendar get promoted? Because it had a lot of dates."
        if intent in {"sadness", "anxiety"} or sentiment == "low":
            return "I hear you. Start with one small grounding step: take 5 slow breaths, then do one 10-minute task you control."
        return "I can help with that. Share a bit more detail and I will give you a focused step-by-step plan."

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

        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        return cleaned

    def _build_prompt(self, messages: list[dict]) -> str:
        lines = []
        for msg in messages:
            role = msg["role"].upper()
            lines.append(f"{role}: {msg['content']}")
        lines.append("ASSISTANT:")
        return "\n".join(lines)
