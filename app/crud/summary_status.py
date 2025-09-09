from sqlalchemy.orm import Session, aliased
from app.models.payment_details import PaymentDetails
from app.models.applicant_details import ApplicantDetails
from app.models.loan_details import LoanDetails
from app.models.branch import Branch
from app.models.dealer import Dealer
from app.models.lenders import Lender
from app.models.user import User
from app.models.repayment_status import RepaymentStatus
from sqlalchemy import func, text, and_, or_
from fastapi import HTTPException
from datetime import datetime, date, timedelta

def get_summary_status_with_filters(
    db: Session, 
    emi_month: str = None,
    branch: str = None,
    dealer: str = None,
    lender: str = None,
    status: str = None,
    rm_name: str = None,
    tl_name: str = None,
    ptp_date_filter: str = None,
    repayment_id: str = None,
    demand_num: str = None
) -> dict:
    """
    Get summary status with filters applied - same filters as application_row API
    """
    RM = aliased(User)
    TL = aliased(User)
    
    # Base query with joins - FIXED: Use current_team_lead_id instead of source_relationship_manager_id
    query = (
        db.query(PaymentDetails)
        .select_from(PaymentDetails)
        .join(LoanDetails, PaymentDetails.loan_application_id == LoanDetails.loan_application_id)
        .join(ApplicantDetails, LoanDetails.applicant_id == ApplicantDetails.applicant_id)
        .join(Branch, ApplicantDetails.branch_id == Branch.id)
        .join(Dealer, ApplicantDetails.dealer_id == Dealer.id)
        .join(Lender, LoanDetails.lenders_id == Lender.id)
        .join(RM, LoanDetails.Collection_relationship_manager_id == RM.id)
        .join(TL, LoanDetails.current_team_lead_id == TL.id)  # FIXED: Use current_team_lead_id
        .join(RepaymentStatus, PaymentDetails.repayment_status_id == RepaymentStatus.id)
    )
    
    # Apply filters (same logic as application_row API)
    if emi_month:
        try:
            dt = datetime.strptime(emi_month, '%b-%y')
            month, year = dt.month, dt.year
            query = query.filter(
                and_(
                    PaymentDetails.demand_month == month,
                    PaymentDetails.demand_year == year
                )
            )
        except:
            pass  # Invalid emi_month format
    
    if branch:
        query = query.filter(Branch.name == branch)
    
    if dealer:
        query = query.filter(Dealer.name == dealer)
    
    if lender:
        query = query.filter(Lender.name == lender)
    
    if status:
        query = query.filter(RepaymentStatus.repayment_status == status)
    
    if rm_name:
        query = query.filter(RM.name == rm_name)
    
    if tl_name:
        query = query.filter(TL.name == tl_name)
    
    if repayment_id:
        query = query.filter(PaymentDetails.id == int(repayment_id))
    
    if demand_num:
        query = query.filter(PaymentDetails.demand_num == demand_num)
    
    # PTP date filtering
    if ptp_date_filter:
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        if ptp_date_filter == "overdue":
            query = query.filter(PaymentDetails.ptp_date < today)
        elif ptp_date_filter == "today":
            query = query.filter(func.date(PaymentDetails.ptp_date) == today)
        elif ptp_date_filter == "tomorrow":
            query = query.filter(func.date(PaymentDetails.ptp_date) == tomorrow)
        elif ptp_date_filter == "future":
            query = query.filter(PaymentDetails.ptp_date > tomorrow)
        elif ptp_date_filter == "no_ptp":
            query = query.filter(PaymentDetails.ptp_date.is_(None))
    
    # Get filtered results
    results = (
        query.with_entities(PaymentDetails.repayment_status_id, func.count(PaymentDetails.id))
        .group_by(PaymentDetails.repayment_status_id)
        .all()
    )
    
    # Fixed summary with exact fields as per schema
    summary = {
        'total': 0,
        'future': 0,
        'overdue': 0,
        'partially_paid': 0,
        'paid': 0,
        'foreclose': 0,
        'paid_pending_approval': 0,
        'paid_rejected': 0
    }
    
    # Status mapping to exact fields
    status_map = {
        'Future': 'future',
        'Overdue': 'overdue',
        'Partially Paid': 'partially_paid',
        'Paid': 'paid',
        'Foreclose': 'foreclose',
        'Paid(Pending Approval)': 'paid_pending_approval',
        'Paid Rejected': 'paid_rejected'
    }
    
    for status_id, count in results:
        status_str = db.query(RepaymentStatus.repayment_status).filter(RepaymentStatus.id == status_id).scalar()
        if status_str:
            key = status_map.get(status_str)
            if key and key in summary:
                summary[key] += count
            summary['total'] += count
    
    return summary

def emi_month_to_month_year(emi_month: str):
    try:
        dt = datetime.strptime(emi_month, '%b-%y')
        return dt.month, dt.year
    except Exception:
        raise HTTPException(status_code=400, detail='Invalid emi_month format. Use e.g. Jul-25')

def get_summary_status(db: Session, emi_month: str) -> dict:
    return get_summary_status_with_filters(db, emi_month=emi_month) 