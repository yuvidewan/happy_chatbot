from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    reply: str
    sentiment: str
    context: str
    suggestions: List[str]
    timestamp: datetime


class SuggestionResponse(BaseModel):
    context: str
    suggestions: List[str]
    timestamp: datetime
