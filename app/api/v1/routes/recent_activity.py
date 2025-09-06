from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.crud.recent_activity import get_recent_activity
from app.schemas.recent_activity import RecentActivityResponse
from typing import Optional

router = APIRouter()

@router.get("/", response_model=RecentActivityResponse)
def get_recent_activity_endpoint(
    loan_id: Optional[int] = Query(None, description="Filter by loan ID"),
    repayment_id: Optional[int] = Query(None, description="Filter by repayment ID (payment ID)"),
    limit: int = Query(50, description="Maximum number of activities to return"),
    days_back: int = Query(30, description="Number of days to look back"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get recent activity for status management changes.
    
    Returns only 4 types of changes:
    1. Repayment Status changes (Paid, Unpaid, Partially Paid, etc.)
    2. PTP Date changes
    3. Amount Collected changes
    4. Demand Calling Status changes (from calling records)
    """
    try:
        activities = get_recent_activity(
            db=db,
            loan_id=loan_id,
            repayment_id=repayment_id,
            limit=limit,
            days_back=days_back
        )
        
        return RecentActivityResponse(
            activities=activities,
            total_count=len(activities)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch recent activity: {str(e)}"
        )

@router.get("/loan/{loan_id}", response_model=RecentActivityResponse)
def get_loan_recent_activity(
    loan_id: int,
    limit: int = Query(50, description="Maximum number of activities to return"),
    days_back: int = Query(30, description="Number of days to look back"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get recent activity for a specific loan.
    """
    try:
        activities = get_recent_activity(
            db=db,
            loan_id=loan_id,
            repayment_id=None,
            limit=limit,
            days_back=days_back
        )
        
        return RecentActivityResponse(
            activities=activities,
            total_count=len(activities)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch recent activity for loan {loan_id}: {str(e)}"
        )
