from sqlalchemy.orm import Session
from sqlalchemy import and_, func, text
from typing import Dict, Any, Optional
from datetime import date
from app.models.payment_details import PaymentDetails
from app.models.loan_details import LoanDetails
from app.models.calling import Calling
from app.models.contact_calling import ContactCalling
from app.models.repayment_status import RepaymentStatus
from app.schemas.status_management import StatusManagementUpdate, CallingTypeEnum
from app.schemas.contact_types import ContactTypeEnum
from app.crud.user import get_user_by_id
from app.models.payment_mode import PaymentMode
from app.models.activity_log import ActivityLog

def update_status_management(
    db: Session, 
    loan_id: str, 
    status_data: StatusManagementUpdate,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """Update status management for a loan application"""
    
    # Set user context before any database operations for audit trail
    if user_id:
        # Get user name for audit triggers
        user = get_user_by_id(db, user_id)
        user_name = user.name if user else f"User_{user_id}"
        # Escape single quotes in user name for SQL
        escaped_user_name = user_name.replace("'", "''")
        
        # Set @app_user for audit triggers (expects user name)
        db.execute(text(f"SET @app_user = '{escaped_user_name}'"))
        
        # Set @app_user_activity for activity triggers (expects user_id format)
        db.execute(text(f"SET @app_user_activity = 'user_id:{user_id}'"))
    
    # Find the payment record for this loan
    if status_data.repayment_id:
        # If specific repayment_id is provided, use that
        payment_record = db.query(PaymentDetails).filter(
            PaymentDetails.id == int(status_data.repayment_id)
        ).first()
        
        if not payment_record:
            raise ValueError(f"No payment record found for repayment ID: {status_data.repayment_id}")
        
        # Verify this payment belongs to the specified loan
        if str(payment_record.loan_application_id) != loan_id:
            raise ValueError(f"Repayment ID {status_data.repayment_id} does not belong to loan ID {loan_id}")
        
        repayment_id = str(payment_record.id)
    else:
        # Find the first payment record for this loan (existing behavior)
        payment_record = db.query(PaymentDetails).join(
            LoanDetails, PaymentDetails.loan_application_id == LoanDetails.loan_application_id
        ).filter(
            LoanDetails.loan_application_id == loan_id
        ).first()
        
        if not payment_record:
            raise ValueError(f"No payment record found for loan ID: {loan_id}")
        
        repayment_id = str(payment_record.id)
    updated_fields = []
    calling_records_created = []
    
    # Update payment_details fields
    if status_data.repayment_status is not None:
        payment_record.repayment_status_id = status_data.repayment_status
        updated_fields.append("repayment_status")
    
    # 🎯 MODIFIED! Handle PTP date with clear functionality
    if status_data.ptp_date is not None:
        if isinstance(status_data.ptp_date, str) and status_data.ptp_date.lower() == "clear":
            # Frontend explicitly wants to clear PTP date
            payment_record.ptp_date = None
            updated_fields.append("ptp_date_cleared")
        elif isinstance(status_data.ptp_date, date):
            # Frontend provided a valid date
            payment_record.ptp_date = status_data.ptp_date
            updated_fields.append("ptp_date")
        # If it's neither "clear" nor a valid date, ignore it
    
    if status_data.amount_collected is not None:
        # Get current amount from database (default to 0 if None)
        current_amount = float(payment_record.amount_collected or 0)
        
        # Add new amount to current amount
        new_total = current_amount + float(status_data.amount_collected)
        
        # Update database with total amount
        payment_record.amount_collected = new_total
        updated_fields.append("amount_collected")
    
    # 🎯 NEW! Update payment mode
    if status_data.payment_mode_id is not None:
        # Store previous value for activity log
        previous_payment_mode = payment_record.mode
        new_payment_mode = str(status_data.payment_mode_id)
        
        # Only update if value actually changed
        if previous_payment_mode != new_payment_mode:
            # Verify payment mode exists
            payment_mode = db.query(PaymentMode).filter(
                PaymentMode.id == status_data.payment_mode_id
            ).first()
            
            if not payment_mode:
                raise ValueError(f"Invalid payment mode ID: {status_data.payment_mode_id}")
            
            payment_record.mode = new_payment_mode
            updated_fields.append("payment_mode")
            
            # 🎯 Create activity log for payment mode change
            if user_id:
                activity_log = ActivityLog(
                    loan_application_id=int(loan_id),
                    payment_id=payment_record.id,
                    field_type_id=5,  # payment_mode field type
                    previous_value=previous_payment_mode or "",
                    new_value=new_payment_mode,
                    changed_by_user_id=user_id
                )
                db.add(activity_log)
    
    # Enforce business rule: if marking as Paid(Pending Approval) (ID=6),
    # then collected amount must be >= EMI/demand amount
    if status_data.repayment_status == 6:  # ID=6 for "Paid(Pending Approval)"
        # Use the updated amount_collected (which now includes the addition)
        current_amount_collected = float(payment_record.amount_collected or 0)
        emi_amount = float(payment_record.demand_amount or 0)
        if current_amount_collected < emi_amount:
            raise ValueError(
                f"Amount collected ({current_amount_collected}) must be >= EMI ({emi_amount}) for Paid(Pending Approval)"
            )
    
    # Handle calling status based on calling_type
    calling_type = status_data.calling_type or CallingTypeEnum.contact_calling
    
    if calling_type == CallingTypeEnum.demand_calling and status_data.demand_calling_status is not None:
        # Create calling record for demand calling
        calling_record = Calling(
            repayment_id=repayment_id,
            caller_user_id=1,  # Default caller, can be updated later
            Calling_id=2,  # 2 for demand calling
            status_id=status_data.demand_calling_status,
            contact_type=ContactTypeEnum.applicant.value,  # Default to applicant for demand calling
            call_date=func.now()
        )
        db.add(calling_record)
        calling_records_created.append("demand_calling")
        updated_fields.append("demand_calling_status")
    
    elif calling_type == CallingTypeEnum.contact_calling and status_data.contact_calling_status is not None:
        # Create calling record for contact calling
        contact_type_value = (status_data.contact_type or ContactTypeEnum.applicant).value
        calling_record = Calling(
            repayment_id=repayment_id,
            caller_user_id=1,  # Default caller, can be updated later
            Calling_id=1,  # 1 for contact calling
            status_id=status_data.contact_calling_status,
            contact_type=contact_type_value,
            call_date=func.now()
        )
        db.add(calling_record)
        calling_records_created.append("contact_calling")
        updated_fields.append("contact_calling_status")
    
    # Commit all changes
    db.commit()
    
    # Get existing calling statuses for response
    existing_demand_calling = db.query(Calling).filter(
        and_(
            Calling.repayment_id == repayment_id,
            Calling.Calling_id == 2  # Demand calling
        )
    ).order_by(Calling.created_at.desc()).first()
    
    existing_contact_calling = db.query(Calling).filter(
        and_(
            Calling.repayment_id == repayment_id,
            Calling.Calling_id == 1,  # Contact calling
            Calling.contact_type == (status_data.contact_type or ContactTypeEnum.applicant).value
        )
    ).order_by(Calling.created_at.desc()).first()
    
    # 🎯 MODIFIED! Handle PTP date in response
    response_ptp_date = None
    if status_data.ptp_date is not None:
        if isinstance(status_data.ptp_date, str) and status_data.ptp_date.lower() == "clear":
            response_ptp_date = None  # Cleared
        elif isinstance(status_data.ptp_date, date):
            response_ptp_date = status_data.ptp_date
    
    # 🎯 NEW! Get payment mode name for response
    payment_mode_name = None
    payment_mode_id = None
    if payment_record.mode:
        try:
            payment_mode_id = int(payment_record.mode)
            payment_mode = db.query(PaymentMode).filter(
                PaymentMode.id == payment_mode_id
            ).first()
            if payment_mode:
                payment_mode_name = payment_mode.mode_name
        except (ValueError, TypeError):
            # If mode is not a valid integer, skip
            pass
    
    return {
        "loan_id": loan_id,
        "repayment_id": repayment_id,  # 🎯 ADDED! Return the repayment_id that was updated
        "calling_type": calling_type.value,  # Return the calling type used
        "demand_calling_status": status_data.demand_calling_status or (existing_demand_calling.status_id if existing_demand_calling else None),
        "repayment_status": status_data.repayment_status,
        "ptp_date": response_ptp_date,  # 🎯 MODIFIED! Return processed PTP date
        "amount_collected": payment_record.amount_collected,  # Return the updated total amount
        "contact_calling_status": status_data.contact_calling_status or (existing_contact_calling.status_id if existing_contact_calling else None),
        "contact_type": (status_data.contact_type or ContactTypeEnum.applicant).value,
        "payment_mode_id": payment_mode_id,  # 🎯 NEW!
        "payment_mode_name": payment_mode_name,  # 🎯 NEW!
        "message": f"Updated: {', '.join(updated_fields)}. Calling records created: {', '.join(calling_records_created)}. Repayment ID: {repayment_id}",
        "updated_at": payment_record.updated_at.isoformat() if payment_record.updated_at else None
    }
