from datetime import datetime
import json

from sqlalchemy.orm import Session

from app.models.models import ChatMessage, SuggestionSnapshot
from app.services.llama_service import ChatTurn, FineTunedLlamaModel


class HappinessService:
    def __init__(self):
        self.model = None

    def _ensure_model(self):
        if self.model is None:
            self.model = FineTunedLlamaModel()

    def run_chat(self, db: Session, message: str):
        self._ensure_model()
        history = self._load_recent_history(db)
        reply, sentiment, intent = self.model.generate_reply(message, history)
        suggestions = self._build_suggestions(intent, sentiment)

        db.add(ChatMessage(role="user", message=message, sentiment=sentiment))
        db.add(ChatMessage(role="assistant", message=reply, sentiment=sentiment))
        db.add(SuggestionSnapshot(suggestions=json.dumps(suggestions), context=intent))
        db.commit()

        return {
            "reply": reply,
            "sentiment": sentiment,
            "context": intent,
            "suggestions": suggestions,
            "timestamp": datetime.utcnow(),
        }

    def latest_suggestions(self, db: Session):
        snap = db.query(SuggestionSnapshot).order_by(SuggestionSnapshot.id.desc()).first()
        if not snap:
            return {
                "context": "general",
                "suggestions": [
                    "Take a 2-minute breathing pause",
                    "Write one win from today",
                    "Send one supportive message to someone",
                ],
                "timestamp": datetime.utcnow(),
            }
        return {
            "context": snap.context,
            "suggestions": json.loads(snap.suggestions),
            "timestamp": snap.created_at,
        }

    def _load_recent_history(self, db: Session):
        rows = db.query(ChatMessage).order_by(ChatMessage.id.desc()).limit(10).all()
        rows.reverse()
        return [ChatTurn(role=r.role, text=r.message) for r in rows]

    def _build_suggestions(self, intent: str, sentiment: str):
        by_intent = {
            "humor": [
                "Take a 2-minute humor break",
                "Share one funny memory with someone",
                "List one absurd thing that happened today",
            ],
            "anxiety": [
                "Try 4-7-8 breathing for 2 rounds",
                "Write what is in your control right now",
                "Pick one 10-minute action and start",
            ],
            "sadness": [
                "Name what you feel in one honest sentence",
                "Open a window and take 5 slow breaths",
                "Do one kind thing for yourself in the next hour",
            ],
            "motivation": [
                "Define one tiny goal for the next 30 minutes",
                "Remove one distraction from your workspace",
                "Start a 5-minute focus sprint",
            ],
            "general": [
                "Drink water and relax your shoulders",
                "Write one priority for today",
                "Take a short walk break if possible",
            ],
        }
        suggestions = by_intent.get(intent, by_intent["general"])[:]
        if sentiment == "low" and intent not in ["anxiety", "sadness"]:
            suggestions[0] = "Pause for 5 deep breaths and unclench your jaw"
        return suggestions
