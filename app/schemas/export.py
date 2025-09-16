from pydantic import BaseModel
from typing import Optional, List
from datetime import date

class ExportCollectionDataRequest(BaseModel):
    demand_month: int
    demand_year: int
    format: str = "excel"

class ExportCollectionDataResponse(BaseModel):
    applicant_id: str
    collection_rm: Optional[str]
    collection_tl: Optional[str]
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
