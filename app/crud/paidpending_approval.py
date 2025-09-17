from sqlalchemy.orm import Session
from sqlalchemy import and_, text
from typing import Optional
from datetime import date
from app.models.payment_details import PaymentDetails
from app.models.repayment_status import RepaymentStatus
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
        # REJECT: Check amount and decide status
        if payment_record.amount_collected and float(payment_record.amount_collected) > 0:
            # Has amount → "Partially Paid"
            partially_paid_status = db.query(RepaymentStatus).filter(
                RepaymentStatus.repayment_status == "Partially Paid"
            ).first()
            
            if not partially_paid_status:
                raise ValueError("'Partially Paid' status not found in repayment_status table")
            
            payment_record.repayment_status_id = partially_paid_status.id
            new_status_name = "Partially Paid"
            message = f"Payment rejected. Status changed to Partially Paid due to existing amount: {payment_record.amount_collected}"
        else:
            # No amount → "Paid Rejected"
            paid_rejected_status = db.query(RepaymentStatus).filter(
                RepaymentStatus.repayment_status == "Paid Rejected"
            ).first()
            
            if not paid_rejected_status:
                raise ValueError("'Paid Rejected' status not found in repayment_status table")
            
            payment_record.repayment_status_id = paid_rejected_status.id
            new_status_name = "Paid Rejected"
            message = "Payment rejected. Status changed to Paid Rejected due to no amount collected."
    
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
