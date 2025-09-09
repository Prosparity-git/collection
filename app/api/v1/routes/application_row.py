from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.schemas.application_row import AppplicationFilterResponse
from app.crud.application_row import get_filtered_applications

router = APIRouter()

@router.get("/", response_model=AppplicationFilterResponse)
def filter_applications(
    loan_id: str = Query("", description="Filter by specific loan ID (comma-separated for multiple values)"),  # 🎯 ADDED! Filter by loan_id
    emi_month: str = Query("", description="EMI month in format 'Jul-25'"),
    search: str = Query("", description="Search in applicant name or application ID (comma-separated for multiple terms)"),
    branch: str = Query("", description="Filter by branch name (comma-separated for multiple values)"),
    dealer: str = Query("", description="Filter by dealer name (comma-separated for multiple values)"),
    lender: str = Query("", description="Filter by lender name (comma-separated for multiple values)"),
    status: str = Query("", description="Filter by repayment status (comma-separated for multiple values)"),
    rm_name: str = Query("", description="Filter by RM name (comma-separated for multiple values)"),
    tl_name: str = Query("", description="Filter by Team Lead name (comma-separated for multiple values)"),
    ptp_date_filter: str = Query("", description="Filter by PTP date: 'overdue', 'today', 'tomorrow', 'future', 'no_ptp' (comma-separated for multiple values)"),
    repayment_id: str = Query("", description="Filter by repayment ID (payment details ID) (comma-separated for multiple values)"),  # 🎯 ADDED! Filter by repayment_id
    demand_num: str = Query("", description="Filter by demand number (comma-separated for multiple values)"),  # 🎯 ADDED! Filter by demand_num
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get filtered applications with essential filtering options.
    
    Supports filtering by:
    - EMI month
    - Search in applicant name/ID (comma-separated for multiple terms)
    - Branch, Dealer, Lender (comma-separated for multiple values)
    - Status, RM, Team Lead (comma-separated for multiple values)
    - PTP date categories (comma-separated for multiple values)
    - Demand number (comma-separated for multiple values)
    - Loan ID (comma-separated for multiple values)
    - Repayment ID (comma-separated for multiple values)
    
    All string filters now support multiple comma-separated values.
    Example: branch=Mumbai,Delhi,Bangalore
    """
    return get_filtered_applications(
        db=db,
        loan_id=loan_id,  # 🎯 ADDED! Pass loan_id parameter
        emi_month=emi_month,
        search=search,
        branch=branch,
        dealer=dealer,
        lender=lender,
        status=status,
        rm_name=rm_name,
        tl_name=tl_name,
        ptp_date_filter=ptp_date_filter,
        repayment_id=repayment_id,  # 🎯 ADDED! Pass repayment_id parameter
        demand_num=demand_num,  # 🎯 ADDED! Pass demand_num parameter
        offset=offset,
        limit=limit
    )