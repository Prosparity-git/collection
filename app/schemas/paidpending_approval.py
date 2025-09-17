from pydantic import BaseModel
from typing import Optional
from enum import Enum

class ApprovalActionEnum(str, Enum):
    accept = "accept"
    reject = "reject"

class PaidPendingApprovalRequest(BaseModel):
    loan_id: str
    repayment_id: str  # 🎯 CHANGED! From demand_date to repayment_id
    action: ApprovalActionEnum  # accept or reject
    comments: Optional[str] = None  # Optional comments for rejection

class PaidPendingApprovalResponse(BaseModel):
    loan_id: str
    repayment_id: str  # 🎯 CHANGED! From demand_date to repayment_id
    action: str
    previous_status: str
    new_status: str
    message: str
    updated_at: str
    comments: Optional[str] = None
