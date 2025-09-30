from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.visit_types import VisitType
from app.schemas.visit_types import VisitTypeCreate
from typing import List

def create_visit_type(db: Session, visit_type: VisitTypeCreate) -> VisitType:
    """Create a new visit type"""
    db_visit_type = VisitType(**visit_type.dict())
    db.add(db_visit_type)
    db.commit()
    db.refresh(db_visit_type)
    return db_visit_type

def get_all_visit_types(db: Session) -> List[VisitType]:
    """Get all active visit types"""
    return db.query(VisitType)\
        .filter(VisitType.is_active == True)\
        .order_by(VisitType.type_name)\
        .all()

def get_visit_type_by_id(db: Session, visit_type_id: int) -> VisitType:
    """Get visit type by ID"""
    return db.query(VisitType).filter(VisitType.id == visit_type_id).first()

def get_visit_type_by_name(db: Session, type_name: str) -> VisitType:
    """Get visit type by name"""
    return db.query(VisitType).filter(VisitType.type_name == type_name).first()
