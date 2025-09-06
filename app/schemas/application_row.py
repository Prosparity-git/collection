from pydantic import BaseModel
from typing import Optional, List, Dict

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
    calling_statuses: Dict[str, str] = {  # All 4 contact types calling status
        "applicant": "Not Called",
        "co_applicant": "Not Called", 
        "guarantor": "Not Called",
        "reference": "Not Called"
    }
    demand_calling_status: Optional[str] = None  # 🎯 ADDED! Demand calling status
    payment_mode: Optional[str] = None  # Payment mode (UPI, Cash, etc.)
    amount_collected: Optional[float] = None  # 🎯 ADDED! Amount collected from payment_details
    loan_amount: Optional[float] = None  # 🎯 ADDED! Loan Amount
    disbursement_date: Optional[str] = None  # 🎯 ADDED! Disbursement Date  
    house_ownership: Optional[str] = None  # 🎯 ADDED! House Ownership
    comments: List[str] = []

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
    offset: Optional[int] = 0
    limit: Optional[int] = 20

class AppplicationFilterResponse(BaseModel):
    total: int
    results: List[ApplicationItem]
    