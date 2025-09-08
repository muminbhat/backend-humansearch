from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field, EmailStr, field_validator
from .common import JobStatus
from .profile import IdentityCandidate, PersonProfile


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

    @field_validator("email", mode="before")
    @classmethod
    def _empty_email_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator("name", "phone", "username", "location", "context_text", mode="before")
    @classmethod
    def _empty_strings_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v


class SearchStartResponse(BaseModel):
    job_id: str
    status: JobStatus


class SearchStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    questions: Optional[List[str]] = None


class ChooseCandidateRequest(BaseModel):
    index: int = Field(ge=0, description="Index of candidate to choose from result.candidates")


class AnswerInput(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    username: Optional[str] = None
    location: Optional[str] = None
    context_text: Optional[str] = None

    @field_validator("email", mode="before")
    @classmethod
    def _empty_email_to_none_answer(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

