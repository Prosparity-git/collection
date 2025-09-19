from pydantic import BaseModel
from typing import Optional

class SummaryStatusRequest(BaseModel):
    emi_month: Optional[str] = None
    branch: Optional[str] = None
    dealer: Optional[str] = None
    lender: Optional[str] = None
    status: Optional[str] = None
    rm_name: Optional[str] = None
    tl_name: Optional[str] = None
    ptp_date_filter: Optional[str] = None
    repayment_id: Optional[str] = None
    demand_num: Optional[str] = None  # 🎯 ADDED! Filter by demand number

class SummaryStatusResponse(BaseModel):
    total: int
    future: int
    overdue: int
    partially_paid: int
    paid: int
    foreclose: int
    paid_pending_approval: int
    paid_rejected: int
    overdue_paid: int 