from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, and_
from app.models.field_visit_location import FieldVisitLocation
from app.models.loan_details import LoanDetails
from app.models.applicant_details import ApplicantDetails
from app.schemas.field_visit_location import FieldVisitLocationCreate
from app.utils.distance import is_within_radius
from typing import List, Optional
from fastapi import HTTPException

def create_field_visit_location(db: Session, field_visit: FieldVisitLocationCreate) -> FieldVisitLocation:
    """Create a new field visit location record with location validation"""
    
    # Check if it's a customer visit (visit_type_id = 1)
    if field_visit.visit_type_id == 1:  # customer_visit
        # Get loan details to find applicant
        loan_details = db.query(LoanDetails).filter(
            LoanDetails.loan_application_id == field_visit.loan_application_id
        ).first()
        
        if not loan_details:
            raise HTTPException(status_code=404, detail="Loan application not found")
        
        # Get applicant details for home location
        applicant = db.query(ApplicantDetails).filter(
            ApplicantDetails.applicant_id == loan_details.applicant_id
        ).first()
        
        if not applicant:
            raise HTTPException(status_code=404, detail="Applicant details not found")
        
        if not applicant.latitude or not applicant.longitude:
            raise HTTPException(
                status_code=400, 
                detail="Applicant home location not available. Cannot validate customer visit."
            )
        
        # Check if visit location is within 100 meters of applicant's home
        is_within_range, actual_distance = is_within_radius(
            point1_lat=float(applicant.latitude),
            point1_lon=float(applicant.longitude),
            point2_lat=float(field_visit.latitude),
            point2_lon=float(field_visit.longitude),
            radius_meters=100
        )
        
        if not is_within_range:
            raise HTTPException(
                status_code=400,
                detail=f"आप ग्राहक के घर की लोकेशन से बहुत दूर हैं। दूरी: {actual_distance:.0f} मीटर। कृपया ग्राहक के घर के 100 मीटर के दायरे में जाएं।"
            )
    
    # Create the field visit record
    db_field_visit = FieldVisitLocation(**field_visit.dict())
    db.add(db_field_visit)
    db.commit()
    db.refresh(db_field_visit)
    
    # Load agent relationship to include agent name in response
    db.refresh(db_field_visit, attribute_names=['agent'])
    
    return db_field_visit

def get_all_field_visits(db: Session) -> List[FieldVisitLocation]:
    """Get all field visit locations with visit type and agent"""
    return db.query(FieldVisitLocation)\
        .options(
            joinedload(FieldVisitLocation.visit_type),
            joinedload(FieldVisitLocation.agent)
        )\
        .order_by(desc(FieldVisitLocation.created_at))\
        .all()

def get_field_visits_by_loan(db: Session, loan_application_id: Optional[int] = None, payment_details_id: Optional[int] = None) -> List[FieldVisitLocation]:
    """Get field visits filtered by loan_application_id and/or payment_details_id with visit type and agent"""
    query = db.query(FieldVisitLocation).options(
        joinedload(FieldVisitLocation.visit_type),
        joinedload(FieldVisitLocation.agent)
    )
    
    filters = []
    if loan_application_id is not None:
        filters.append(FieldVisitLocation.loan_application_id == loan_application_id)
    if payment_details_id is not None:
        filters.append(FieldVisitLocation.payment_details_id == payment_details_id)
    
    if filters:
        query = query.filter(and_(*filters))
    
    return query.order_by(desc(FieldVisitLocation.created_at)).all()

def get_field_visits_by_type(db: Session, visit_type_id: int) -> List[FieldVisitLocation]:
    """Get field visits by visit type with agent"""
    return db.query(FieldVisitLocation)\
        .options(
            joinedload(FieldVisitLocation.visit_type),
            joinedload(FieldVisitLocation.agent)
        )\
        .filter(FieldVisitLocation.visit_type_id == visit_type_id)\
        .order_by(desc(FieldVisitLocation.created_at))\
        .all()