from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal
from typing import Optional

class FieldVisitLocationBase(BaseModel):
    loan_application_id: int
    payment_details_id: Optional[int] = None
    agent_id: int
    latitude: Decimal = Field(..., decimal_places=8, max_digits=10)
    longitude: Decimal = Field(..., decimal_places=8, max_digits=11)

class FieldVisitLocationCreate(FieldVisitLocationBase):
    pass

class FieldVisitLocationResponse(FieldVisitLocationBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class FieldVisitLocationList(BaseModel):
    id: int
    loan_application_id: int
    agent_id: int
    latitude: Decimal
    longitude: Decimal
    created_at: datetime
    
    class Config:
        from_attributes = True
