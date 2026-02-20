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
def suggestions(db: Session = Depends(get_db)):
    return service.latest_suggestions(db)
