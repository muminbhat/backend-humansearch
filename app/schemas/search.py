from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field, EmailStr


class NormalizedQuery(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    username: Optional[str] = None
    location: Optional[str] = None
    context_text: Optional[str] = None


class SearchInput(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    username: Optional[str] = None
    location: Optional[str] = None
    context_text: Optional[str] = Field(None, description="Free-text context from user")


class SearchStartResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]


class SearchStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

