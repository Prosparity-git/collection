from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from app.models.audit_payment_details import AuditPaymentDetails
from app.models.repayment_status import RepaymentStatus
from app.models.user import User
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
    Get recent activity for the 4 main things:
    1. Repayment Status changes
    2. Demand Calling Status changes  
    3. PTP Date changes
    4. Amount Collected changes
    """
    activities = []
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    # Query audit payment details
    query = db.query(AuditPaymentDetails).filter(
        AuditPaymentDetails.action_timestamp >= cutoff_date
    )
    
    if loan_id:
        # loan_application_id is the loan_id in the audit table
        query = query.filter(AuditPaymentDetails.loan_application_id == loan_id)
    
    if repayment_id:
        # Filter by payment_id directly
        query = query.filter(AuditPaymentDetails.payment_id == repayment_id)
    
    audits = query.order_by(desc(AuditPaymentDetails.action_timestamp)).limit(limit * 2).all()
    
    for audit in audits:
        if audit.old_data and audit.new_data:
            # 1. Check Repayment Status changes
            old_status_id = audit.old_data.get('Repayment_status_id')
            new_status_id = audit.new_data.get('Repayment_status_id')
            
            if old_status_id != new_status_id:
                old_status = get_repayment_status_name(db, old_status_id)
                new_status = get_repayment_status_name(db, new_status_id)
                
                activities.append(RecentActivityItem(
                    id=audit.audit_id,
                    activity_type=ActivityTypeEnum.repayment_status,
                    from_value=old_status,
                    to_value=new_status,
                    changed_by=get_user_name(db, audit.changed_by),
                    timestamp=audit.action_timestamp,
                    loan_id=audit.loan_application_id,
                    repayment_id=audit.payment_id
                ))
            
            # 2. Check PTP Date changes
            old_ptp_date = audit.old_data.get('ptp_date')
            new_ptp_date = audit.new_data.get('ptp_date')
            
            if old_ptp_date != new_ptp_date:
                activities.append(RecentActivityItem(
                    id=audit.audit_id,
                    activity_type=ActivityTypeEnum.ptp_date,
                    from_value=old_ptp_date,
                    to_value=new_ptp_date,
                    changed_by=get_user_name(db, audit.changed_by),
                    timestamp=audit.action_timestamp,
                    loan_id=audit.loan_application_id,
                    repayment_id=audit.payment_id
                ))
            
            # 3. Check Amount Collected changes
            old_amount = audit.old_data.get('amount_collected')
            new_amount = audit.new_data.get('amount_collected')
            
            if old_amount != new_amount:
                activities.append(RecentActivityItem(
                    id=audit.audit_id,
                    activity_type=ActivityTypeEnum.amount_collected,
                    from_value=str(old_amount) if old_amount else None,
                    to_value=str(new_amount) if new_amount else None,
                    changed_by=get_user_name(db, audit.changed_by),
                    timestamp=audit.action_timestamp,
                    loan_id=audit.loan_application_id,
                    repayment_id=audit.payment_id
                ))
    
    # Sort by timestamp and return top results
    activities.sort(key=lambda x: x.timestamp, reverse=True)
    return activities[:limit]

def get_repayment_status_name(db: Session, status_id: Optional[int]) -> Optional[str]:
    """Get repayment status name by ID"""
    if not status_id:
        return None
    
    status = db.query(RepaymentStatus).filter(RepaymentStatus.id == status_id).first()
    return status.repayment_status if status else None

def get_user_name(db: Session, changed_by: Optional[str]) -> str:
    """Get user name by ID or return the changed_by value if it's already a name"""
    if not changed_by:
        return "System"
    
    # If changed_by is already a name (not a number), return it
    if not changed_by.isdigit():
        return changed_by
    
    # If changed_by is a number (user ID), look up the user
    try:
        user_id = int(changed_by)
        user = db.query(User).filter(User.id == user_id).first()
        return user.name if user else f"User_{user_id}"
    except ValueError:
        return changed_by


