from pydantic import BaseModel, validator
from typing import Optional, Union
from datetime import date
from enum import Enum
from app.schemas.contact_types import ContactTypeEnum

class RepaymentStatusEnum(str, Enum):
    Future = "Future"
    Partially_Paid = "Partially Paid"
    Paid = "Paid"
    Overdue = "Overdue"
    Foreclose = "Foreclose"
    Paid_Pending_Approval = "Paid(Pending Approval)"
    paidpending = "paidpending"
    Paid_Rejected = "Paid Rejected"

class CallingTypeEnum(int, Enum):
    """Calling types for status management"""
    contact_calling = 1    # Contact calling (answered, not answered, not called)
    demand_calling = 2     # Demand calling (deposited in bank, cash collected, PTP taken, no response)

class StatusManagementUpdate(BaseModel):
    loan_id: str
    repayment_id: Optional[str] = None  # 🎯 ADDED! Specific payment/repayment to update
    calling_type: Optional[CallingTypeEnum] = CallingTypeEnum.contact_calling  # 1=contact, 2=demand
    demand_calling_status: Optional[int] = None  # ID from demand_calling table
    repayment_status: Optional[int] = None  # ID from repayment_status table
    ptp_date: Optional[Union[date, str]] = None  # 🎯 MODIFIED! Can be date or "clear" string
    amount_collected: Optional[float] = None
    contact_calling_status: Optional[int] = None  # ID from contact_calling table
    contact_type: Optional[ContactTypeEnum] = ContactTypeEnum.applicant  # Default to applicant
    
    @validator('ptp_date', pre=True)
    def parse_ptp_date(cls, v):
        """Convert string date to date object if needed"""
        if v is None:
            return None
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            if v.lower() == "clear":
                return "clear"  # Keep as string for clearing
            try:
                # Try to parse ISO date format (YYYY-MM-DD)
                return date.fromisoformat(v)
            except ValueError:
                # If parsing fails, raise validation error
                raise ValueError(f"Invalid date format: {v}. Expected YYYY-MM-DD format or 'clear'")
        return v

class StatusManagementResponse(BaseModel):
    loan_id: str
    repayment_id: Optional[str] = None  # 🎯 ADDED! Specific payment/repayment that was updated
    calling_type: Optional[int] = None  # 1=contact, 2=demand
    demand_calling_status: Optional[int] = None
    repayment_status: Optional[int] = None
    ptp_date: Optional[date] = None
    amount_collected: Optional[float] = None
    contact_calling_status: Optional[int] = None
    contact_type: Optional[int] = None
    message: str
    updated_at: str
