from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.deps import get_db
from app.crud.visit_types import (
    create_visit_type,
    get_all_visit_types,
    get_visit_type_by_id
)
from app.schemas.visit_types import (
    VisitTypeCreate,
    VisitTypeResponse,
    VisitTypeList
)

router = APIRouter()

@router.post("/", response_model=VisitTypeResponse)
def create_visit_type_endpoint(
    visit_type: VisitTypeCreate,
    db: Session = Depends(get_db)
):
    """Create a new visit type"""
    try:
        return create_visit_type(db=db, visit_type=visit_type)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating visit type: {str(e)}")

@router.get("/", response_model=List[VisitTypeList])
def get_all_visit_types_endpoint(
    db: Session = Depends(get_db)
):
    """Get all active visit types"""
    return get_all_visit_types(db=db)

@router.get("/{visit_type_id}", response_model=VisitTypeResponse)
def get_visit_type_by_id_endpoint(
    visit_type_id: int,
    db: Session = Depends(get_db)
):
    """Get visit type by ID"""
    visit_type = get_visit_type_by_id(db=db, visit_type_id=visit_type_id)
    if not visit_type:
        raise HTTPException(status_code=404, detail="Visit type not found")
    return visit_type
