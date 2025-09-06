from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ActivityTypeEnum(str, Enum):
    repayment_status = "Status"
    demand_calling_status = "Calling Status" 
    ptp_date = "PTP Date"
    amount_collected = "Amount Collected"

class RecentActivityItem(BaseModel):
    id: int
    activity_type: ActivityTypeEnum
    from_value: Optional[str] = None
    to_value: Optional[str] = None
    changed_by: str
    timestamp: datetime
    loan_id: Optional[int] = None
    repayment_id: Optional[int] = None

class RecentActivityResponse(BaseModel):
    activities: List[RecentActivityItem]
    total_count: int
