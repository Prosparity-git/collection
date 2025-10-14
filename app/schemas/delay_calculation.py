from pydantic import BaseModel
from typing import List, Optional


class DelayCalculationItem(BaseModel):
    payment_id: int
    loan_id: int 
    demand_num: Optional[int] = None  # EMI number (1, 2, 3, etc.)
    demand_date: Optional[str] = None
    payment_date: Optional[str] = None
    delay_days: Optional[int] = None  # Positive = overdue/late, Negative = paid early, None = no demand date
    overdue_amount: Optional[float] = None  # max(0, demand_amount - amount_collected)
    status: Optional[str] = None  # Repayment status from database (e.g., "Overdue", "Paid", "Partially Paid")


class DelayCalculationResponse(BaseModel):
    loan_id: int
    total_repayments: int
    results: List[DelayCalculationItem]