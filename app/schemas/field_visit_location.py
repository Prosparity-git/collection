from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal
from typing import Optional

class FieldVisitLocationBase(BaseModel):
    loan_application_id: int
    payment_details_id: Optional[int] = None
    visit_type_id: int = 1  # Default to customer visit
    latitude: Decimal = Field(..., decimal_places=8, max_digits=10)
    longitude: Decimal = Field(..., decimal_places=8, max_digits=11)

class FieldVisitLocationCreate(FieldVisitLocationBase):
    agent_id: Optional[int] = None  # Optional for API, will be set by backend

class FieldVisitLocationResponse(FieldVisitLocationBase):
    id: int
    agent_id: int  # This will be populated by backend
    created_at: datetime
    
    class Config:
        from_attributes = True

class FieldVisitLocationWithType(FieldVisitLocationResponse):
    visit_type_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class FieldVisitLocationList(BaseModel):
    id: int
    loan_application_id: int
    agent_id: int
    visit_type_id: int
    visit_type_name: Optional[str] = None
    latitude: Decimal
    longitude: Decimal
    created_at: datetime
    
    class Config:
        from_attributes = True