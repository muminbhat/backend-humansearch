from typing import Optional, List, Dict, Any
from pydantic import BaseModel, HttpUrl, EmailStr
from .common import SourceMethod


class Provenance(BaseModel):
    source_name: str
    method: SourceMethod
    url: Optional[HttpUrl] = None
    captured_at: Optional[str] = None
    note: Optional[str] = None


class EvidenceItem(BaseModel):
    field: str
    value: Any
    confidence: float
    provenance: Provenance
    snippet: Optional[str] = None


class IdentityCandidate(BaseModel):
    display_name: Optional[str] = None
    emails: List[EmailStr] = []
    phones: List[str] = []
    usernames: List[str] = []
    locations: List[str] = []
    links: List[HttpUrl] = []
    score: float = 0.0
    top_evidence: List[EvidenceItem] = []


class PersonProfile(BaseModel):
    names: List[str] = []
    emails: List[EmailStr] = []
    phones: List[str] = []
    usernames: List[str] = []
    locations: List[str] = []
    employment: List[Dict[str, Any]] = []
    education: List[Dict[str, Any]] = []
    links: List[HttpUrl] = []
    bios: List[str] = []
    skills: List[str] = []
    organizations: List[str] = []
    websites: List[HttpUrl] = []
    evidences: List[EvidenceItem] = []
    overall_confidence: float = 0.0

