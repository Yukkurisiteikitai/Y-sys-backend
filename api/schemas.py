import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class SessionRequest(BaseModel):
    user_id: Optional[str] = None
    metadata: Dict[str, Any]

class SessionResponse(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    thread_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime = Field(default_factory=lambda: datetime.now() + timedelta(hours=24))

class MessageRequest(BaseModel):
    message: str
    sensitivity_level: str # "low|medium|high"

# Phase 1: Abstract Recognition
class AbstractRecognitionResult(BaseModel):
    emotional_state: List[str]
    cognitive_pattern: str
    value_alignment: List[str]
    decision_context: str
    relevant_tags: List[str]
    confidence: float

# Phase 2: Concrete Understanding
class Episode(BaseModel):
    episode_id: str
    text_snippet: str
    relevance_score: float
    tags: List[str]
    source_metadata: Optional[Dict[str, str]] = None

class ConcreteUnderstandingResult(BaseModel):
    related_episodes: List[Episode]
    total_retrieved: int

# Phase 3: Response Generation
class ThoughtProcess(BaseModel):
    inferred_decision: str
    inferred_action: str
    key_considerations: List[str]
    emotional_tone: str

# Phase 4: Final Response
class FinalResponseData(BaseModel):
    nuance: str
    dialogue: str
    behavior: str

class FinalResponse(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    response: FinalResponseData
    metadata: Dict[str, Any]
