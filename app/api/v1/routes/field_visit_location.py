from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.deps import get_db
from app.crud.field_visit_location import (
    create_field_visit_location,
    get_field_visits_by_loan,
    get_all_field_visits
)
from app.schemas.field_visit_location import (
    FieldVisitLocationCreate,
    FieldVisitLocationResponse,
    FieldVisitLocationList
)

router = APIRouter()

@router.post("/", response_model=FieldVisitLocationResponse)
def create_field_visit(
    field_visit: FieldVisitLocationCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new field visit location record.
    This endpoint will be called from mobile app when agent visits a location.
    """
    try:
        return create_field_visit_location(db=db, field_visit=field_visit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating field visit: {str(e)}")

@router.get("/", response_model=List[FieldVisitLocationList])
def get_all_visits(
    db: Session = Depends(get_db)
):
    """Get all field visit locations"""
    return get_all_field_visits(db=db)

@router.get("/filter", response_model=List[FieldVisitLocationList])
def get_visits_by_loan_and_payment(
    loan_application_id: Optional[int] = Query(None, description="Filter by loan application ID"),
    payment_details_id: Optional[int] = Query(None, description="Filter by payment details ID"),
    db: Session = Depends(get_db)
):
    """Get field visits filtered by loan_application_id and/or payment_details_id"""
    return get_field_visits_by_loan(db=db, loan_application_id=loan_application_id, payment_details_id=payment_details_id)
