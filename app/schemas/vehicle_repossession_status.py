from pydantic import BaseModel
from datetime import datetime, date
from decimal import Decimal
from typing import Optional


class VehicleRepossessionStatusBase(BaseModel):
    id: int
    loan_application_id: int
    repayment_id: Optional[int] = None
    vehicle_status: Optional[int] = None
    repossession_date: Optional[date] = None
    repossession_sale_date: Optional[date] = None
    repossession_sale_amount: Optional[Decimal] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class VehicleRepossessionStatusResponse(VehicleRepossessionStatusBase):
    vehicle_status_name: Optional[str] = None
    
    class Config:
        from_attributes = True

