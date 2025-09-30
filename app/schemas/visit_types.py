from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class VisitTypeBase(BaseModel):
    type_name: str
    description: Optional[str] = None
    is_active: bool = True

class VisitTypeCreate(VisitTypeBase):
    pass

class VisitTypeResponse(VisitTypeBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class VisitTypeList(BaseModel):
    id: int
    type_name: str
    description: Optional[str] = None
    
    class Config:
        from_attributes = True
