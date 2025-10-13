from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.crud.summary_status import get_summary_status, get_summary_status_with_filters
from app.schemas.summary_status import SummaryStatusResponse

router = APIRouter()

@router.get('/summary', response_model=SummaryStatusResponse)
def summary_status_route(
    emi_month: str = Query(..., description="EMI month in format 'Jul-25'"),
    branch: str = Query(None, description="Filter by branch name (comma-separated for multiple values)"),
    dealer: str = Query(None, description="Filter by dealer name (comma-separated for multiple values)"),
    lender: str = Query(None, description="Filter by lender name (comma-separated for multiple values)"),
    status: str = Query(None, description="Filter by repayment status (comma-separated for multiple values)"),
    rm_name: str = Query(None, description="Filter by RM name (comma-separated for multiple values)"),
    tl_name: str = Query(None, description="Filter by TL name (comma-separated for multiple values)"),
    source_rm_name: str = Query(None, description="Filter by Source RM name (comma-separated for multiple values)"),  # 🎯 ADDED!
    source_tl_name: str = Query(None, description="Filter by Source Team Lead name (comma-separated for multiple values)"),  # 🎯 ADDED!
    ptp_date_filter: str = Query(None, description="Filter by PTP date category (comma-separated for multiple values)"),
    repayment_id: str = Query(None, description="Filter by repayment ID (comma-separated for multiple values)"),
    demand_num: str = Query(None, description="Filter by demand number (comma-separated for multiple values)"),
    current_dpd_bucket: str = Query(None, description="Filter by current DPD bucket (comma-separated for multiple values)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get summary status with optional filters applied.
    
    All string filters now support multiple comma-separated values.
    Example: branch=Mumbai,Delhi,Bangalore&status=Paid,Pending,Overdue
    
    Returns summary counts for:
    - total: Total number of records
    - future: Future payments
    - overdue: Overdue payments  
    - partially_paid: Partially paid
    - paid: Fully paid
    - foreclose: Foreclosed
    - paid_pending_approval: Paid but pending approval
    - paid_rejected: Paid but rejected
    - overdue_paid: Payments that were paid after demand date
    """
    return get_summary_status_with_filters(
        db=db,
        emi_month=emi_month,
        branch=branch,
        dealer=dealer,
        lender=lender,
        status=status,
        rm_name=rm_name,
        tl_name=tl_name,
        source_rm_name=source_rm_name,
        source_tl_name=source_tl_name,  # 🎯 ADDED!
        ptp_date_filter=ptp_date_filter,
        repayment_id=repayment_id,
        demand_num=demand_num,
        current_dpd_bucket=current_dpd_bucket
    ) 