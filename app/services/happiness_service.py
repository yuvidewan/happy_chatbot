from datetime import datetime
import json

from sqlalchemy.orm import Session

from app.models.models import ChatMessage, SuggestionSnapshot
from app.services.context_suggestion_service import ContextSuggestionService
from app.services.llama_service import ChatTurn, FineTunedLlamaModel


class HappinessService:
    def __init__(self):
        self.model = None
        self.context_service = ContextSuggestionService()

    def _ensure_model(self):
        if self.model is None:
            self.model = FineTunedLlamaModel()

    def run_chat(self, db: Session, message: str):
        self._ensure_model()
        history = self._load_recent_history(db)
        reply, sentiment, intent = self.model.generate_reply(message, history)
        context = self.context_service.detect_context(message, history, fallback_intent=intent)
        suggestions = self.context_service.build_suggestions(context=context, sentiment=sentiment, message=message)

        db.add(ChatMessage(role="user", message=message, sentiment=sentiment))
        db.add(ChatMessage(role="assistant", message=reply, sentiment=sentiment))
        db.add(SuggestionSnapshot(suggestions=json.dumps(suggestions), context=context))
        db.commit()

        current_datetime = datetime.now()
        #current_time = current_datetime.strftime("%H:%M:%S")
        return {
            "reply": reply,
            "sentiment": sentiment,
            "context": context,
            "suggestions": suggestions,
            "timestamp": current_datetime,
        }

    def latest_suggestions(self, db: Session):
        current_datetime = datetime.now()
        #current_time = current_datetime.strftime("%H:%M:%S")
        snap = db.query(SuggestionSnapshot).order_by(SuggestionSnapshot.id.desc()).first()
        if not snap:
            return {
                "context": "general",
                "suggestions": self.context_service.build_suggestions(context="general", sentiment="neutral"),
                "timestamp": current_datetime,
            }
        saved_suggestions = json.loads(snap.suggestions)
        if not any("youtube.com" in str(item).lower() for item in saved_suggestions):
            saved_suggestions = self.context_service.build_suggestions(
                context=snap.context,
                sentiment="neutral",
            )

        return {
            "context": snap.context,
            "suggestions": saved_suggestions,
            "timestamp": snap.created_at,
        }

    def suggestions_for_context(self, context: str | None, sentiment: str = "neutral", message: str | None = None):
        current_datetime = datetime.now()
 
        normalized_context = self.context_service.normalize_context(context or "general")
        normalized_sentiment = (sentiment or "neutral").strip().lower()
        if message and message.strip():
            normalized_context = self.context_service.detect_context(
                message=message,
                history=[],
                fallback_intent=normalized_context,
            )
        return {
            "context": normalized_context,
            "suggestions": self.context_service.build_suggestions(
                context=normalized_context,
                sentiment=normalized_sentiment,
                message=message or "",
            ),
            "timestamp": current_datetime,
        }

    def _load_recent_history(self, db: Session):
        rows = db.query(ChatMessage).order_by(ChatMessage.id.desc()).limit(10).all()
        rows.reverse()
        return [ChatTurn(role=r.role, text=r.message) for r in rows]
