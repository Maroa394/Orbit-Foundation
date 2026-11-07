from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class RegisterIn(BaseModel):
    organisation_name: str = Field(min_length=2, max_length=180)
    full_name: str = Field(min_length=2, max_length=180)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class DepartmentIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)

class WorkIn(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    description: str = ""
    status: str = "open"
    priority: str = "medium"
    due_date: Optional[str] = None
    department_id: Optional[int] = None

class RiskIn(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    description: str = ""
    category: str = "Operational"
    likelihood: int = Field(default=3, ge=1, le=5)
    impact: int = Field(default=3, ge=1, le=5)
    status: str = "identified"
    mitigation: str = ""

class WatchIn(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    source: str = "Manual"
    severity: str = "medium"
    details: str = ""

class EvidenceIn(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    evidence_type: str = "Document"
    reference: str = ""
    review_date: Optional[str] = None
    notes: str = ""

class ApprovalIn(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    request_details: str = ""

class DecisionIn(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    decision_note: str = ""
