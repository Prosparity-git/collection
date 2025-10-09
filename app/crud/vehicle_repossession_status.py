from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, and_
from app.models.vehicle_repossession_status import VehicleRepossessionStatus
from app.models.vehicle_status import VehicleStatus
from typing import List, Optional


def get_all_vehicle_repossession_statuses(db: Session) -> List[dict]:
    """Get all vehicle repossession statuses with vehicle status information"""
    vehicle_repossession_statuses = db.query(VehicleRepossessionStatus)\
        .options(joinedload(VehicleRepossessionStatus.vehicle_status_rel))\
        .order_by(desc(VehicleRepossessionStatus.created_at))\
        .all()
    
    results = []
    for vrs in vehicle_repossession_statuses:
        result = {
            "id": vrs.id,
            "loan_application_id": vrs.loan_application_id,
            "repayment_id": vrs.repayment_id,
            "vehicle_status": vrs.vehicle_status,
            "repossession_date": vrs.repossession_date,
            "repossession_sale_date": vrs.repossession_sale_date,
            "repossession_sale_amount": vrs.repossession_sale_amount,
            "created_at": vrs.created_at,
            "updated_at": vrs.updated_at,
            "vehicle_status_name": vrs.vehicle_status_rel.vehicle_status.value if vrs.vehicle_status_rel else None
        }
        results.append(result)
    
    return results


def get_vehicle_repossession_statuses_by_filters(
    db: Session, 
    loan_application_id: Optional[int] = None, 
    repayment_id: Optional[int] = None
) -> List[dict]:
    """Get vehicle repossession statuses filtered by loan_application_id and/or repayment_id"""
    query = db.query(VehicleRepossessionStatus).options(joinedload(VehicleRepossessionStatus.vehicle_status_rel))
    
    filters = []
    if loan_application_id is not None:
        filters.append(VehicleRepossessionStatus.loan_application_id == loan_application_id)
    if repayment_id is not None:
        filters.append(VehicleRepossessionStatus.repayment_id == repayment_id)
    
    if filters:
        query = query.filter(and_(*filters))
    
    vehicle_repossession_statuses = query.order_by(desc(VehicleRepossessionStatus.created_at)).all()
    
    results = []
    for vrs in vehicle_repossession_statuses:
        result = {
            "id": vrs.id,
            "loan_application_id": vrs.loan_application_id,
            "repayment_id": vrs.repayment_id,
            "vehicle_status": vrs.vehicle_status,
            "repossession_date": vrs.repossession_date,
            "repossession_sale_date": vrs.repossession_sale_date,
            "repossession_sale_amount": vrs.repossession_sale_amount,
            "created_at": vrs.created_at,
            "updated_at": vrs.updated_at,
            "vehicle_status_name": vrs.vehicle_status_rel.vehicle_status.value if vrs.vehicle_status_rel else None
        }
        results.append(result)
    
    return results

