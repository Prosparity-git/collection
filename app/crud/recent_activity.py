from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from app.models.activity_log import ActivityLog
from app.models.field_types import FieldTypes
from app.models.repayment_status import RepaymentStatus
from app.models.demand_calling import DemandCalling
from app.models.user import User
from app.models.payment_mode import PaymentMode
from app.schemas.recent_activity import RecentActivityItem, ActivityTypeEnum
from datetime import datetime, timedelta

def get_recent_activity(
    db: Session,
    loan_id: Optional[int] = None,
    repayment_id: Optional[int] = None,
    limit: int = 50,
    days_back: int = 30
) -> List[RecentActivityItem]:
    """
    Get recent activity from activity_log table for the 4 main things:
    1. Repayment Status changes
    2. Demand Calling Status changes  
    3. PTP Date changes
    4. Amount Collected changes
    """
    activities = []
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    # Query activity_log table with field_types join
    query = db.query(
        ActivityLog,
        FieldTypes.field_name
    ).join(
        FieldTypes, ActivityLog.field_type_id == FieldTypes.id
    ).filter(
        ActivityLog.created_at >= cutoff_date,
        ActivityLog.is_delete == 0  # Only show non-deleted records
    )
    
    if loan_id:
        query = query.filter(ActivityLog.loan_application_id == loan_id)
    
    if repayment_id:
        query = query.filter(ActivityLog.payment_id == repayment_id)
    
    # Get recent activities
    results = query.order_by(desc(ActivityLog.created_at)).limit(limit).all()
    
    for log, field_name in results:
        # Get actual status names based on field type
        old_value, new_value = get_status_names(db, field_name, log.previous_value, log.new_value)
        
        activities.append(RecentActivityItem(
            id=log.id,
            activity_type=map_field_name_to_activity_type(field_name),
            from_value=old_value,
            to_value=new_value,
            changed_by=get_user_name(db, log.changed_by_user_id),
            timestamp=log.created_at,
            loan_id=log.loan_application_id,
            repayment_id=log.payment_id
        ))
    
    return activities

def get_status_names(db: Session, field_name: str, old_id: str, new_id: str) -> tuple:
    """Get actual status names from IDs"""
    if field_name == 'repayment_status':
        old_status = db.query(RepaymentStatus).filter(RepaymentStatus.id == int(old_id)).first() if old_id else None
        new_status = db.query(RepaymentStatus).filter(RepaymentStatus.id == int(new_id)).first() if new_id else None
        return (old_status.repayment_status if old_status else old_id, 
                new_status.repayment_status if new_status else new_id)
    
    elif field_name == 'demand_calling_status':
        old_status = db.query(DemandCalling).filter(DemandCalling.id == int(old_id)).first() if old_id else None
        new_status = db.query(DemandCalling).filter(DemandCalling.id == int(new_id)).first() if new_id else None
        return (old_status.demand_calling_status if old_status else old_id,
                new_status.demand_calling_status if new_status else new_id)
    
    elif field_name == "payment_mode":
        # Get payment mode names
        old_mode = None
        new_mode = None
        
        if old_id and old_id.strip():
            try:
                old_mode_obj = db.query(PaymentMode).filter(PaymentMode.id == int(old_id)).first()
                old_mode = old_mode_obj.mode_name if old_mode_obj else old_id
            except (ValueError, TypeError):
                old_mode = old_id
        
        if new_id and new_id.strip():
            try:
                new_mode_obj = db.query(PaymentMode).filter(PaymentMode.id == int(new_id)).first()
                new_mode = new_mode_obj.mode_name if new_mode_obj else new_id
            except (ValueError, TypeError):
                new_mode = new_id
        
        return old_mode, new_mode
    
    else:
        # For other fields, return as is
        return (old_id, new_id)

def map_field_name_to_activity_type(field_name: str) -> Optional[ActivityTypeEnum]:
    """Map field_name to ActivityTypeEnum"""
    mapping = {
        'repayment_status': ActivityTypeEnum.repayment_status,
        'amount_collected': ActivityTypeEnum.amount_collected,
        'ptp_date': ActivityTypeEnum.ptp_date,
        'demand_calling_status': ActivityTypeEnum.demand_calling_status,
        'payment_mode': ActivityTypeEnum.payment_mode,
    }
    return mapping.get(field_name)

def get_user_name(db: Session, user_id: Optional[int]) -> str:
    """Get user name by ID"""
    if not user_id:
        return "System"
    
    user = db.query(User).filter(User.id == user_id).first()
    return user.name if user else f"User_{user_id}"


