from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.schemas.filters_main import FiltersOptionsResponse, CascadingOptionsResponse
from app.crud.filter_main import filter_options, cascading_options

router = APIRouter()

@router.get("/options", response_model=FiltersOptionsResponse)
def get_filter_options(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return filter_options(db)


@router.get("/cascading", response_model=CascadingOptionsResponse)
def get_cascading_options(
    branch_id: int = Query(None, description="Filter by branch ID"),
    dealer_id: int = Query(None, description="Filter by dealer ID"),
    lender_id: int = Query(None, description="Filter by lender ID"),
    tl_id: int = Query(None, description="Filter by current team lead ID"),
    rm_id: int = Query(None, description="Filter by current collection RM ID"),
    source_tl_id: int = Query(None, description="Filter by source team lead ID (from loan_details)"),
    source_rm_id: int = Query(None, description="Filter by source RM ID (from loan_details)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get cascading filter options for Branch, Dealer, Lender, Current Team Lead, Current RM,
    Source Team Lead, and Source RM. All fields cascade based on selected filters.
    Returns only valid combinations based on selected filters.
    """
    return cascading_options(db, branch_id, dealer_id, lender_id, tl_id, rm_id, source_tl_id, source_rm_id)