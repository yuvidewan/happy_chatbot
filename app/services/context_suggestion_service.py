from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import quote_plus

from app.services.llama_service import ChatTurn


@dataclass(frozen=True)
class ContextProfile:
    key: str
    keywords: tuple[str, ...]
    suggestions: tuple[str, str, str]
    youtube_query: str


class ContextSuggestionService:
    def __init__(self):
        self._profiles: dict[str, ContextProfile] = {
            "anxiety": ContextProfile(
                key="anxiety",
                keywords=(
                    "anxious",
                    "anxiety",
                    "stress",
                    "stressed",
                    "overwhelmed",
                    "panic",
                    "nervous",
                    "worry",
                    "worried",
                    "burnout",
                ),
                suggestions=(
                    "Try 4-7-8 breathing for 2 rounds.",
                    "Write 3 things you can control in the next hour.",
                    "Start one 10-minute calming action right now.",
                ),
                youtube_query="4 7 8 breathing exercise guided",
            ),
            "sadness": ContextProfile(
                key="sadness",
                keywords=(
                    "sad",
                    "down",
                    "depressed",
                    "lonely",
                    "hopeless",
                    "empty",
                    "cry",
                    "crying",
                    "heartbroken",
                ),
                suggestions=(
                    "Name what you feel in one honest sentence.",
                    "Take 5 slow breaths and relax your jaw and shoulders.",
                    "Do one kind thing for yourself in the next hour.",
                ),
                youtube_query="10 minute grounding meditation for sadness",
            ),
            "motivation": ContextProfile(
                key="motivation",
                keywords=(
                    "motivate",
                    "motivation",
                    "discipline",
                    "procrastinate",
                    "procrastination",
                    "goal",
                    "focus",
                    "productive",
                    "productivity",
                ),
                suggestions=(
                    "Pick one tiny task you can finish in 10 minutes.",
                    "Set a 25-minute focus timer and remove one distraction.",
                    "Write your next 3 concrete steps in order.",
                ),
                youtube_query="pomodoro focus timer 25 minutes",
            ),
            "study": ContextProfile(
                key="study",
                keywords=(
                    "study",
                    "exam",
                    "revision",
                    "assignment",
                    "college",
                    "school",
                    "syllabus",
                    "chapter",
                ),
                suggestions=(
                    "Use a 25/5 study sprint for your next session.",
                    "List high-yield topics and start with the hardest one.",
                    "Teach one concept aloud to test recall.",
                ),
                youtube_query="study with me pomodoro no distractions",
            ),
            "technical": ContextProfile(
                key="technical",
                keywords=(
                    "code",
                    "coding",
                    "python",
                    "javascript",
                    "typescript",
                    "bug",
                    "error",
                    "debug",
                    "api",
                    "database",
                    "stack trace",
                    "backend",
                    "frontend",
                ),
                suggestions=(
                    "Reproduce the issue with the smallest possible input first.",
                    "Check logs/tracebacks and isolate the exact failing layer.",
                    "Patch one thing at a time and re-test after each change.",
                ),
                youtube_query="debugging workflow software engineering practical",
            ),
            "career": ContextProfile(
                key="career",
                keywords=(
                    "job",
                    "interview",
                    "resume",
                    "cv",
                    "career",
                    "manager",
                    "office",
                    "promotion",
                    "salary",
                ),
                suggestions=(
                    "Define the exact outcome you want from this career step.",
                    "Prepare 3 proof points of impact from your past work.",
                    "Draft one high-signal message or application today.",
                ),
                youtube_query="job interview preparation tips 2026",
            ),
            "relationship": ContextProfile(
                key="relationship",
                keywords=(
                    "relationship",
                    "partner",
                    "friend",
                    "family",
                    "breakup",
                    "argument",
                    "conflict",
                    "communication",
                ),
                suggestions=(
                    "State your feeling and need in one calm sentence.",
                    "Use 'I feel... when... because...' instead of blame.",
                    "Ask one clarifying question before reacting.",
                ),
                youtube_query="healthy communication relationship conflict resolution",
            ),
            "sleep": ContextProfile(
                key="sleep",
                keywords=(
                    "sleep",
                    "insomnia",
                    "cant sleep",
                    "can't sleep",
                    "bedtime",
                    "night routine",
                    "wake up",
                    "tired",
                ),
                suggestions=(
                    "Set a no-screen wind-down for the next 30 minutes.",
                    "Try a slow breathing cycle for 5 minutes in bed.",
                    "Keep your wake-up time fixed tomorrow morning.",
                ),
                youtube_query="sleep meditation 10 minutes",
            ),
            "fitness": ContextProfile(
                key="fitness",
                keywords=(
                    "workout",
                    "exercise",
                    "gym",
                    "running",
                    "weight",
                    "diet",
                    "nutrition",
                    "fat loss",
                    "muscle",
                ),
                suggestions=(
                    "Start with a short, repeatable 20-minute routine.",
                    "Track one metric this week: steps, sleep, or protein.",
                    "Plan tomorrow's workout time now to avoid skipping.",
                ),
                youtube_query="full body beginner workout no equipment",
            ),
            "humor": ContextProfile(
                key="humor",
                keywords=("joke", "funny", "laugh", "meme", "roast", "banter"),
                suggestions=(
                    "Take a 2-minute humor break.",
                    "Share one funny memory with someone today.",
                    "Write one absurd thing that happened recently.",
                ),
                youtube_query="clean stand up comedy set",
            ),
            "greeting": ContextProfile(
                key="greeting",
                keywords=("hi", "hello", "hey", "good morning", "good evening"),
                suggestions=(
                    "Tell me your top priority and I will help you with it.",
                    "If you want support, describe how you are feeling right now.",
                    "If you want fun, ask for a joke or playful roast.",
                ),
                youtube_query="positive morning motivation short",
            ),
            "gratitude": ContextProfile(
                key="gratitude",
                keywords=("thanks", "thank you", "thx", "appreciate"),
                suggestions=(
                    "Want a quick summary of what we covered?",
                    "Ask me for a concrete next-step checklist.",
                    "Start a new topic whenever you are ready.",
                ),
                youtube_query="gratitude meditation 5 minutes",
            ),
            "farewell": ContextProfile(
                key="farewell",
                keywords=("bye", "goodbye", "see you", "take care"),
                suggestions=(
                    "Take care and come back anytime.",
                    "Next time, send your top problem in one line.",
                    "Ask for a one-message action plan when you return.",
                ),
                youtube_query="end of day reflection routine",
            ),
            "general": ContextProfile(
                key="general",
                keywords=(),
                suggestions=(
                    "Break your problem into one immediate next step.",
                    "Write one clear goal for the next 30 minutes.",
                    "If stuck, ask for a plan with exact steps.",
                ),
                youtube_query="how to stay focused and calm",
            ),
        }
        self._intent_to_context = {
            "anxiety": "anxiety",
            "sadness": "sadness",
            "motivation": "motivation",
            "technical": "technical",
            "humor": "humor",
            "greeting": "greeting",
            "gratitude": "gratitude",
            "farewell": "farewell",
        }
        self._priority = [
            "anxiety",
            "sadness",
            "technical",
            "study",
            "career",
            "relationship",
            "sleep",
            "fitness",
            "motivation",
            "humor",
            "greeting",
            "gratitude",
            "farewell",
            "general",
        ]

    def detect_context(self, message: str, history: list[ChatTurn], fallback_intent: str = "general") -> str:
        fallback = self.normalize_context(fallback_intent)
        if fallback in {"greeting", "gratitude", "farewell"}:
            return fallback

        combined_text = self._compose_text(message, history)
        best_context = "general"
        best_score = 0
        for context in self._priority:
            profile = self._profiles[context]
            score = self._score_context(combined_text, profile.keywords)
            if score > best_score:
                best_context = context
                best_score = score

        if best_score > 0:
            return best_context

        mapped = self._intent_to_context.get((fallback_intent or "").strip().lower())
        if mapped:
            return mapped
        return "general"

    def normalize_context(self, context: str) -> str:
        normalized = self._normalize(context or "")
        if normalized in self._profiles:
            return normalized
        for key, profile in self._profiles.items():
            if any(self._contains_phrase(normalized, kw) for kw in profile.keywords):
                return key
        return self._intent_to_context.get(normalized, "general")

    def build_suggestions(self, context: str, sentiment: str = "neutral", message: str = "") -> list[str]:
        context_key = self.normalize_context(context)
        profile = self._profiles.get(context_key, self._profiles["general"])
        suggestions = list(profile.suggestions)

        if (sentiment or "").strip().lower() == "low" and context_key not in {"anxiety", "sadness"}:
            suggestions[0] = "Pause for 5 deep breaths, relax your shoulders, and pick one tiny next step."

        suggestions.append(self._youtube_suggestion(context_key, message))
        return suggestions

    def _compose_text(self, message: str, history: list[ChatTurn]) -> str:
        pieces: list[str] = []
        for turn in history[-8:]:
            role = (turn.role or "").strip().lower()
            if role in {"user", "human"}:
                normalized = self._normalize(turn.text)
                if normalized:
                    pieces.append(normalized)
        current = self._normalize(message)
        if current:
            pieces.append(current)
        return " ".join(pieces[-4:])

    def _score_context(self, text: str, keywords: tuple[str, ...]) -> int:
        score = 0
        for keyword in keywords:
            if self._contains_phrase(text, keyword):
                score += 2 if " " in keyword else 1
        return score

    def _contains_phrase(self, text: str, keyword: str) -> bool:
        phrase = self._normalize(keyword)
        if not phrase:
            return False
        pattern = rf"\b{re.escape(phrase)}\b"
        return bool(re.search(pattern, text))

    def _normalize(self, text: str) -> str:
        lowered = (text or "").lower().strip()
        cleaned = re.sub(r"[^a-z0-9'\s]", " ", lowered)
        return re.sub(r"\s+", " ", cleaned).strip()

    def _youtube_suggestion(self, context: str, message: str) -> str:
        profile = self._profiles.get(context, self._profiles["general"])
        focus_terms = self._extract_focus_terms(message, limit=3)
        query = profile.youtube_query
        if focus_terms:
            query = f"{query} {' '.join(focus_terms)}"
        url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        return f"YouTube resource: {url}"

    def _extract_focus_terms(self, message: str, limit: int = 3) -> list[str]:
        tokens = re.findall(r"[a-zA-Z]{4,}", message or "")
        if not tokens:
            return []
        stopwords = {
            "this",
            "that",
            "with",
            "from",
            "have",
            "what",
            "when",
            "where",
            "your",
            "about",
            "into",
            "need",
            "help",
            "please",
            "want",
            "just",
            "really",
            "very",
            "like",
            "would",
            "should",
            "could",
            "also",
        }
        picked: list[str] = []
        for token in tokens:
            normalized = token.lower()
            if normalized in stopwords:
                continue
            if normalized in picked:
                continue
            picked.append(normalized)
            if len(picked) >= limit:
                break
        return picked
