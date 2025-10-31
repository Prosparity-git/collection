from fastapi import APIRouter, Depends, Query, HTTPException
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
    branch_id: str = Query(None, description="Filter by branch ID(s), comma-separated (e.g., 1,2,3)"),
    dealer_id: str = Query(None, description="Filter by dealer ID(s), comma-separated (e.g., 1,2,3)"),
    lender_id: str = Query(None, description="Filter by lender ID(s), comma-separated (e.g., 1,2,3)"),
    tl_id: str = Query(None, description="Filter by current team lead ID(s), comma-separated (e.g., 1,2,3)"),
    rm_id: str = Query(None, description="Filter by current collection RM ID(s), comma-separated (e.g., 1,2,3)"),
    source_tl_id: str = Query(None, description="Filter by source team lead ID(s), comma-separated (e.g., 1,2,3)"),
    source_rm_id: str = Query(None, description="Filter by source RM ID(s), comma-separated (e.g., 1,2,3)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get cascading filter options for Branch, Dealer, Lender, Current Team Lead, Current RM,
    Source Team Lead, and Source RM. All fields cascade based on selected filters.
    Returns only valid combinations based on selected filters.
    Supports multiple comma-separated values for all parameters.
    """
    # Parse comma-separated string values to lists of integers with error handling
    try:
        branch_ids = [int(x.strip()) for x in branch_id.split(',')] if branch_id else None
        dealer_ids = [int(x.strip()) for x in dealer_id.split(',')] if dealer_id else None
        lender_ids = [int(x.strip()) for x in lender_id.split(',')] if lender_id else None
        tl_ids = [int(x.strip()) for x in tl_id.split(',')] if tl_id else None
        rm_ids = [int(x.strip()) for x in rm_id.split(',')] if rm_id else None
        source_tl_ids = [int(x.strip()) for x in source_tl_id.split(',')] if source_tl_id else None
        source_rm_ids = [int(x.strip()) for x in source_rm_id.split(',')] if source_rm_id else None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid ID format. All IDs must be integers. Error: {str(e)}")
    
    return cascading_options(db, branch_ids, dealer_ids, lender_ids, tl_ids, rm_ids, source_tl_ids, source_rm_ids)