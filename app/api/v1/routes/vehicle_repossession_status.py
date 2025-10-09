from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.deps import get_db, get_current_user
from app.crud.vehicle_repossession_status import (
    get_all_vehicle_repossession_statuses,
    get_vehicle_repossession_statuses_by_filters
)
from app.schemas.vehicle_repossession_status import VehicleRepossessionStatusResponse

router = APIRouter()


@router.get("/", response_model=List[VehicleRepossessionStatusResponse])
def get_all_vehicle_repossession_status_records(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all vehicle repossession status records with vehicle status information.
    Returns all records ordered by creation date (newest first).
    """
    return get_all_vehicle_repossession_statuses(db=db)


@router.get("/filter", response_model=List[VehicleRepossessionStatusResponse])
def get_vehicle_repossession_statuses_filtered(
    loan_application_id: Optional[int] = Query(None, description="Filter by loan application ID"),
    repayment_id: Optional[int] = Query(None, description="Filter by repayment ID"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get vehicle repossession statuses filtered by loan_application_id and/or repayment_id.
    
    You can filter by:
    - loan_application_id only
    - repayment_id only
    - Both loan_application_id and repayment_id
    
    Returns vehicle repossession status records with vehicle status information ordered by creation date.
    """
    return get_vehicle_repossession_statuses_by_filters(
        db=db, 
        loan_application_id=loan_application_id, 
        repayment_id=repayment_id
    )

