from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.schemas.status_management import StatusManagementUpdate, StatusManagementResponse
from app.crud.status_management import update_status_management
from app.models.payment_details import PaymentDetails
from app.models.repayment_status import RepaymentStatus
from app.models.demand_calling import DemandCalling
from app.models.contact_calling import ContactCalling
from app.models.calling import Calling
from app.models.payment_mode import PaymentMode
from sqlalchemy import and_
from typing import Optional

router = APIRouter()

@router.put("/{loan_id}", response_model=StatusManagementResponse)
def update_application_status(
    loan_id: str,
    status_update: StatusManagementUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update multiple status fields for an application in a single API call.
    
    Updates can include:
    - Demand Calling Status (creates calling record with calling_id=2)
    - Contact Calling Status (creates calling record with calling_id=1)
    - Repayment Status (payment_details.Repayment_status_id)
    - PTP Date (payment_details.ptp_date)
    - Amount Collected (payment_details.amount_collected)
    
    Only the fields provided will be updated.
    """
    try:
        # Update status management
        result = update_status_management(
            db=db,
            loan_id=loan_id,
            status_data=status_update,
            user_id=current_user["id"]
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid data: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update status: {str(e)}")

@router.get("/{loan_id}")
def get_application_status(
    loan_id: str,
    repayment_id: str = Query(..., description="Repayment ID (payment details ID) to get status for"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get current status for an application by repayment_id"""
    try:
        # Convert loan_id to integer
        try:
            loan_id_int = int(loan_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid loan_id: {loan_id}. Must be a valid integer.")
        
        # Convert repayment_id to integer
        try:
            repayment_id_int = int(repayment_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid repayment_id: {repayment_id}. Must be a valid integer.")
        
        # Get payment details by repayment_id
        payment_details = db.query(PaymentDetails).filter(
            and_(
                PaymentDetails.id == repayment_id_int,
                PaymentDetails.loan_application_id == loan_id_int
            )
        ).first()
        
        if not payment_details:
            raise HTTPException(
                status_code=404, 
                detail=f"Payment details not found for loan_id: {loan_id_int} and repayment_id: {repayment_id}"
            )
        
        # Get repayment status name
        repayment_status_name = None
        if payment_details.repayment_status_id:
            repayment_status_record = db.query(RepaymentStatus).filter(
                RepaymentStatus.id == payment_details.repayment_status_id
            ).first()
            if repayment_status_record:
                repayment_status_name = repayment_status_record.repayment_status
        
        # Get latest calling records for this application
        latest_demand_calling = db.query(Calling).filter(
            and_(
                Calling.repayment_id == str(payment_details.id),
                Calling.Calling_id == 2  # Demand calling
            )
        ).order_by(Calling.created_at.desc()).first()
        
        latest_contact_calling = db.query(Calling).filter(
            and_(
                Calling.repayment_id == str(payment_details.id),
                Calling.Calling_id == 1  # Contact calling
            )
        ).order_by(Calling.created_at.desc()).first()
        
        # Get status names from calling records
        demand_calling_status = None
        if latest_demand_calling:
            demand_calling_record = db.query(DemandCalling).filter(
                DemandCalling.id == latest_demand_calling.status_id
            ).first()
            if demand_calling_record:
                demand_calling_status = demand_calling_record.demand_calling_status
        
        contact_calling_status = None
        if latest_contact_calling:
            contact_calling_record = db.query(ContactCalling).filter(
                ContactCalling.id == latest_contact_calling.status_id
            ).first()
            if contact_calling_record:
                contact_calling_status = contact_calling_record.contact_calling_status
        
        # 🎯 NEW! Get payment mode
        payment_mode_id = None
        payment_mode_name = None
        if payment_details.mode:
            try:
                payment_mode_id = int(payment_details.mode)
                payment_mode_record = db.query(PaymentMode).filter(
                    PaymentMode.id == payment_mode_id
                ).first()
                if payment_mode_record:
                    payment_mode_name = payment_mode_record.mode_name
            except (ValueError, TypeError):
                # If mode is not a valid integer, skip
                pass
        
        return {
            "loan_id": loan_id_int,
            "repayment_id": repayment_id,  # 🎯 ADDED! Return the repayment_id
            "demand_calling_status": demand_calling_status,
            "repayment_status": repayment_status_name,
            "ptp_date": payment_details.ptp_date.isoformat() if payment_details.ptp_date else None,
            "amount_collected": float(payment_details.amount_collected) if payment_details.amount_collected else None,
            "contact_calling_status": contact_calling_status,
            "payment_mode_id": payment_mode_id,  # 🎯 NEW!
            "payment_mode_name": payment_mode_name  # 🎯 NEW!
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        # Log the full error for debugging
        import traceback
        error_details = f"Unexpected error: {str(e)}\nTraceback: {traceback.format_exc()}"
        raise HTTPException(status_code=400, detail=f"Failed to get status: {error_details}")
