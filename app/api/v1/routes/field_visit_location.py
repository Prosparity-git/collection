from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.deps import get_db, get_current_user
from app.crud.field_visit_location import (
    create_field_visit_location,
    get_field_visits_by_loan,
    get_all_field_visits,
    get_field_visits_by_type
)
from app.schemas.field_visit_location import (
    FieldVisitLocationCreate,
    FieldVisitLocationResponse,
    FieldVisitLocationList,
    FieldVisitLocationWithType
)

router = APIRouter()

@router.post("/", response_model=FieldVisitLocationResponse)
def create_field_visit(
    field_visit: FieldVisitLocationCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new field visit location record.
    This endpoint will be called from mobile app when agent visits a location.
    Agent ID is automatically set from the logged-in user for security.
    """
    try:
        # Override agent_id with current user's ID for security
        field_visit.agent_id = current_user['id']
        return create_field_visit_location(db=db, field_visit=field_visit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating field visit: {str(e)}")

@router.get("/", response_model=List[FieldVisitLocationWithType])
def get_all_visits(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all field visit locations with visit type information"""
    return get_all_field_visits(db=db)

@router.get("/filter", response_model=List[FieldVisitLocationWithType])
def get_visits_by_loan_and_payment(
    loan_application_id: Optional[int] = Query(None, description="Filter by loan application ID"),
    payment_details_id: Optional[int] = Query(None, description="Filter by payment details ID"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get field visits filtered by loan_application_id and/or payment_details_id"""
    return get_field_visits_by_loan(db=db, loan_application_id=loan_application_id, payment_details_id=payment_details_id)

@router.get("/by-type/{visit_type_id}", response_model=List[FieldVisitLocationWithType])
def get_visits_by_type(
    visit_type_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get field visits by visit type"""
    return get_field_visits_by_type(db=db, visit_type_id=visit_type_id)