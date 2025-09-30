from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, and_
from app.models.field_visit_location import FieldVisitLocation
from app.schemas.field_visit_location import FieldVisitLocationCreate
from typing import List, Optional

def create_field_visit_location(db: Session, field_visit: FieldVisitLocationCreate) -> FieldVisitLocation:
    """Create a new field visit location record"""
    db_field_visit = FieldVisitLocation(**field_visit.dict())
    db.add(db_field_visit)
    db.commit()
    db.refresh(db_field_visit)
    return db_field_visit

def get_all_field_visits(db: Session) -> List[FieldVisitLocation]:
    """Get all field visit locations with visit type"""
    return db.query(FieldVisitLocation)\
        .options(joinedload(FieldVisitLocation.visit_type))\
        .order_by(desc(FieldVisitLocation.created_at))\
        .all()

def get_field_visits_by_loan(db: Session, loan_application_id: Optional[int] = None, payment_details_id: Optional[int] = None) -> List[FieldVisitLocation]:
    """Get field visits filtered by loan_application_id and/or payment_details_id"""
    query = db.query(FieldVisitLocation).options(joinedload(FieldVisitLocation.visit_type))
    
    filters = []
    if loan_application_id is not None:
        filters.append(FieldVisitLocation.loan_application_id == loan_application_id)
    if payment_details_id is not None:
        filters.append(FieldVisitLocation.payment_details_id == payment_details_id)
    
    if filters:
        query = query.filter(and_(*filters))
    
    return query.order_by(desc(FieldVisitLocation.created_at)).all()

def get_field_visits_by_type(db: Session, visit_type_id: int) -> List[FieldVisitLocation]:
    """Get field visits by visit type"""
    return db.query(FieldVisitLocation)\
        .options(joinedload(FieldVisitLocation.visit_type))\
        .filter(FieldVisitLocation.visit_type_id == visit_type_id)\
        .order_by(desc(FieldVisitLocation.created_at))\
        .all()
