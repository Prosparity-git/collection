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
        # Support multiple comma-separated branch names
        branch_list = [b.strip() for b in branch.split(',') if b.strip()]
        if branch_list:
            query = query.filter(Branch.name.in_(branch_list))
    
    if dealer:
        # Support multiple comma-separated dealer names
        dealer_list = [d.strip() for d in dealer.split(',') if d.strip()]
        if dealer_list:
            query = query.filter(Dealer.name.in_(dealer_list))
    
    if lender:
        # Support multiple comma-separated lender names
        lender_list = [l.strip() for l in lender.split(',') if l.strip()]
        if lender_list:
            query = query.filter(Lender.name.in_(lender_list))
    
    if status:
        # Support multiple comma-separated status values
        status_list = [s.strip() for s in status.split(',') if s.strip()]
        if status_list:
            query = query.filter(RepaymentStatus.repayment_status.in_(status_list))
    
    if rm_name:
        # Support multiple comma-separated RM names
        rm_list = [r.strip() for r in rm_name.split(',') if r.strip()]
        if rm_list:
            query = query.filter(RM.name.in_(rm_list))
    
    if tl_name:
        # Support multiple comma-separated TL names
        tl_list = [t.strip() for t in tl_name.split(',') if t.strip()]
        if tl_list:
            query = query.filter(TL.name.in_(tl_list))
    
    if repayment_id:
        # Support multiple comma-separated repayment IDs
        repayment_list = [r.strip() for r in repayment_id.split(',') if r.strip()]
        if repayment_list:
            try:
                repayment_ids = [int(r) for r in repayment_list]
                query = query.filter(PaymentDetails.id.in_(repayment_ids))
            except ValueError:
                # If any value is not a valid integer, skip this filter
                pass
    
    if demand_num:
        # Support multiple comma-separated demand numbers
        demand_list = [d.strip() for d in demand_num.split(',') if d.strip()]
        if demand_list:
            try:
                demand_nums = [int(d) for d in demand_list]
                query = query.filter(PaymentDetails.demand_num.in_(demand_nums))
            except ValueError:
                # If any value is not a valid integer, skip this filter
                pass
    
    # PTP date filtering
    if ptp_date_filter:
        # Support multiple comma-separated PTP date filters
        ptp_list = [p.strip() for p in ptp_date_filter.split(',') if p.strip()]
        if ptp_list:
            today = date.today()
            tomorrow = today + timedelta(days=1)
            
            ptp_conditions = []
            for ptp_filter in ptp_list:
                if ptp_filter == "overdue":
                    ptp_conditions.append(PaymentDetails.ptp_date < today)
                elif ptp_filter == "today":
                    ptp_conditions.append(func.date(PaymentDetails.ptp_date) == today)
                elif ptp_filter == "tomorrow":
                    ptp_conditions.append(func.date(PaymentDetails.ptp_date) == tomorrow)
                elif ptp_filter == "future":
                    ptp_conditions.append(PaymentDetails.ptp_date > tomorrow)
                elif ptp_filter == "no_ptp":
                    ptp_conditions.append(PaymentDetails.ptp_date.is_(None))
            
            if ptp_conditions:
                query = query.filter(or_(*ptp_conditions))
    
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