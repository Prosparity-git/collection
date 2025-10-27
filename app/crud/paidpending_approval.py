from sqlalchemy.orm import Session
from sqlalchemy import and_, text, desc
from typing import Optional
from datetime import date
from app.models.payment_details import PaymentDetails
from app.models.repayment_status import RepaymentStatus
from app.models.activity_log import ActivityLog
from app.models.field_types import FieldTypes
from app.schemas.paidpending_approval import PaidPendingApprovalRequest
from app.crud.user import get_user_by_id

def process_paidpending_approval(
    db: Session,
    approval_data: PaidPendingApprovalRequest,
    current_user_id: Optional[int] = None
) -> dict:
    """Process paidpending approval - accept or reject"""
    
    # Set user context for audit trail
    if current_user_id:
        # Get user name for audit triggers
        user = get_user_by_id(db, current_user_id)
        user_name = user.name if user else f"User_{current_user_id}"
        # Escape single quotes in user name for SQL
        escaped_user_name = user_name.replace("'", "''")
        
        # Set @app_user for audit triggers (expects user name)
        db.execute(text(f"SET @app_user = '{escaped_user_name}'"))
        
        # Set @app_user_activity for activity triggers (expects user_id format)
        db.execute(text(f"SET @app_user_activity = 'user_id:{current_user_id}'"))
    
    # First, get the payment_details record for this application and repayment_id
    payment_record = db.query(PaymentDetails).filter(
        and_(
            PaymentDetails.loan_application_id == approval_data.loan_id,
            PaymentDetails.id == int(approval_data.repayment_id)
        )
    ).first()
    
    if not payment_record:
        raise ValueError(f"No payment record found for application {approval_data.loan_id} and repayment_id {approval_data.repayment_id}")
    
    # Get current repayment status name BEFORE updating (this is the previous status)
    previous_status_name = None
    if payment_record.repayment_status_id:
        current_status_record = db.query(RepaymentStatus).filter(
            RepaymentStatus.id == payment_record.repayment_status_id
        ).first()
        if current_status_record:
            previous_status_name = current_status_record.repayment_status
    
    # Check if current status is "Paid(Pending Approval)" (we need to find the ID for this)
    paid_pending_approval_status = db.query(RepaymentStatus).filter(
        RepaymentStatus.repayment_status == "Paid(Pending Approval)"
    ).first()
    
    if not paid_pending_approval_status:
        raise ValueError("'Paid(Pending Approval)' status not found in repayment_status table")
    
    if payment_record.repayment_status_id != paid_pending_approval_status.id:
        raise ValueError(f"Current status is '{previous_status_name}', not 'Paid(Pending Approval)'. Cannot process approval.")
    
    # Process based on action
    if approval_data.action == "accept":
        # ACCEPT: Change to "Paid" and set payment_date to current date
        paid_status = db.query(RepaymentStatus).filter(
            RepaymentStatus.repayment_status == "Paid"
        ).first()
        
        if not paid_status:
            raise ValueError("'Paid' status not found in repayment_status table")
        
        payment_record.repayment_status_id = paid_status.id
        payment_record.payment_date = date.today()  # Set payment_date to current date
        new_status_name = "Paid"
        message = "Payment approved successfully. Status changed to Paid and payment_date set to today."
        
    elif approval_data.action == "reject":
        # REJECT: Go back to previous status from Activity Log
        # Get the repayment_status field type ID
        repayment_status_field = db.query(FieldTypes).filter(
            FieldTypes.field_name == "repayment_status"
        ).first()
        
        if not repayment_status_field:
            raise ValueError("'repayment_status' field type not found in field_types table")
        
        # Find the most recent activity log entry where status changed TO Paid(Pending Approval)
        previous_status_id = None
        
        activity_log = db.query(ActivityLog).filter(
            and_(
                ActivityLog.payment_id == payment_record.id,
                ActivityLog.field_type_id == repayment_status_field.id,
                ActivityLog.new_value == str(paid_pending_approval_status.id)  # Changed TO Paid(Pending Approval)
            )
        ).order_by(desc(ActivityLog.created_at)).first()
        
        if activity_log and activity_log.previous_value:
            # Found the previous status ID
            previous_status_id = int(activity_log.previous_value)
            
            # Get the previous status
            previous_status = db.query(RepaymentStatus).filter(
                RepaymentStatus.id == previous_status_id
            ).first()
            
            if previous_status:
                payment_record.repayment_status_id = previous_status_id
                new_status_name = previous_status.repayment_status
                message = f"Payment rejected. Status reverted to previous status: {new_status_name}"
            else:
                # Fallback: Status ID found but status doesn't exist
                overdue_status = db.query(RepaymentStatus).filter(
                    RepaymentStatus.repayment_status == "Overdue"
                ).first()
                if overdue_status:
                    payment_record.repayment_status_id = overdue_status.id
                    new_status_name = "Overdue"
                    message = "Payment rejected. Previous status not found, defaulting to Overdue."
        else:
            # No activity log found - fallback to Overdue
            overdue_status = db.query(RepaymentStatus).filter(
                RepaymentStatus.repayment_status == "Overdue"
            ).first()
            
            if not overdue_status:
                raise ValueError("'Overdue' status not found in repayment_status table")
            
            payment_record.repayment_status_id = overdue_status.id
            new_status_name = "Overdue"
            message = "Payment rejected. No previous status found in activity log, defaulting to Overdue."
    
    # Commit changes
    db.commit()
    db.refresh(payment_record)
    
    return {
        "loan_id": str(approval_data.loan_id),
        "repayment_id": approval_data.repayment_id,  # 🎯 CHANGED! From demand_date to repayment_id
        "action": approval_data.action,
        "previous_status": previous_status_name or "Unknown",
        "new_status": new_status_name,
        "message": message,
        "updated_at": payment_record.updated_at.isoformat() if payment_record.updated_at else None,
        "comments": approval_data.comments
    }
