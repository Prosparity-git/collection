from pydantic import BaseModel
from typing import Optional, List

class ApplicationItem(BaseModel):
    application_id: str
    loan_id: int  # Added loan_id field
    payment_id: int  # 🎯 ADDED! This is the repayment_id for comments
    demand_num: Optional[str] = None  # 🎯 ADDED! Repayment Number from demand_num
    applicant_name: str
    mobile: Optional[str] = None
    emi_amount: Optional[float]
    status: Optional[str]
    emi_month: Optional[str]
    branch: Optional[str]
    rm_name: Optional[str]
    tl_name: Optional[str]
    dealer: Optional[str]
    lender: Optional[str]
    ptp_date: Optional[str]
    demand_calling_status: Optional[str] = None  # 🎯 ADDED! Demand calling status
    payment_mode: Optional[str] = None  # Payment mode (UPI, Cash, etc.)
    amount_collected: Optional[float] = None  # 🎯 ADDED! Amount collected from payment_details
    loan_amount: Optional[float] = None  # 🎯 ADDED! Loan Amount
    disbursement_date: Optional[str] = None  # 🎯 ADDED! Disbursement Date  
    house_ownership: Optional[str] = None  # 🎯 ADDED! House Ownership
    latitude: Optional[float] = None  # 🎯 ADDED! Latitude coordinate
    longitude: Optional[float] = None  # 🎯 ADDED! Longitude coordinate
    address: Optional[str] = None  # 🎯 ADDED! Combined address field
    vehicle_status_name: Optional[str] = None  # 🎯 ADDED! Vehicle status (Repossessed, Need to repossess, etc.)
    repossession_date: Optional[str] = None  # 🎯 ADDED! Date when vehicle was repossessed
    repossession_sale_date: Optional[str] = None  # 🎯 ADDED! Date when repossessed vehicle was sold
    repossession_sale_amount: Optional[float] = None  # 🎯 ADDED! Sale amount of repossessed vehicle
    current_dpd_bucket: Optional[str] = None  # 🎯 ADDED! Current DPD bucket from dpd_monthly_snapshot
    total_overdue_amount: Optional[int] = None  # 🎯 ADDED! Total overdue amount from LMS
    current_overdue_amount: Optional[float] = None  # 🎯 ADDED! Calculated current overdue amount
    nach_status: Optional[str] = None  # 🎯 ADDED! NACH status from nach_status master
    reason: Optional[str] = None  # 🎯 ADDED! NACH reason from nach_status master

class ApplicationFilters(BaseModel):
    emi_month: Optional[str] = ""
    search: Optional[str] = ""
    branch: Optional[str] = ""
    dealer: Optional[str] = ""
    lender: Optional[str] = ""
    status: Optional[str] = ""
    rm_name: Optional[str] = ""
    tl_name: Optional[str] = ""
    ptp_date_filter: Optional[str] = ""
    repayment_id: Optional[str] = ""  # 🎯 ADDED! Filter by repayment_id
    current_dpd_bucket: Optional[str] = ""  # 🎯 ADDED! Filter by current DPD bucket
    offset: Optional[int] = 0
    limit: Optional[int] = 20

class AppplicationFilterResponse(BaseModel):
    total: int
    results: List[ApplicationItem]
    