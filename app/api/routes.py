from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.schemas import ChatRequest, ChatResponse, SuggestionResponse
from app.services.happiness_service import HappinessService

router = APIRouter(prefix="/api", tags=["happiness"])
service = HappinessService()


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    try:
        return service.run_chat(db, payload.message)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/suggestions", response_model=SuggestionResponse)
def suggestions(
    context: str | None = None,
    sentiment: str = "neutral",
    message: str | None = None,
    db: Session = Depends(get_db),
):
    if context or message:
        return service.suggestions_for_context(context=context, sentiment=sentiment, message=message)
    return service.latest_suggestions(db)
