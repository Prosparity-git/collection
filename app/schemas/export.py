from pydantic import BaseModel
from typing import Optional, List
from datetime import date

class ExportCollectionDataRequest(BaseModel):
    demand_month: int
    demand_year: int
    format: str = "excel"

class ExportCollectionDataResponse(BaseModel):
    applicant_id: str
    full_name: Optional[str]
    collection_rm: Optional[str]
    collection_tl: Optional[str]
    source_rm: Optional[str]
    source_tl: Optional[str]
    branch: Optional[str]
    dealer: Optional[str]
    lender: Optional[str]
    borrower_mobile: Optional[str]
    co_borrower_mobile: Optional[str]
    guarantor_mobile: Optional[str]
    reference_mobile: Optional[str]
    disbursal_date: Optional[date]
    disbursal_amount: Optional[float]
    demand_amount: Optional[float]
    demand_date: Optional[date]
    principal_amount: Optional[float]
    interest: Optional[float]
    demand_num: Optional[int]
    latest_ptp_date: Optional[date]
    amount_collected: Optional[float]
    collection_status: Optional[str]
    last_3_comments: Optional[str]
    paid_date: Optional[date]
    dpd_bucket_name: Optional[str]
    customer_visits_count: Optional[int]
    customer_first_visit_at: Optional[date]
    customer_last_visit_at: Optional[date]
    followup_visits_count: Optional[int]
    followup_first_visit_at: Optional[date]
    followup_last_visit_at: Optional[date]
    total_visits: Optional[int]
    first_visit_at: Optional[date]
    last_visit_at: Optional[date]
