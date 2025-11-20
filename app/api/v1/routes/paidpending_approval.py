from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from app.core.deps import get_db, require_admin
from app.schemas.paidpending_approval import PaidPendingApprovalRequest, PaidPendingApprovalResponse
from app.crud.paidpending_approval import process_paidpending_approval
from app.models.payment_details import PaymentDetails
from app.models.repayment_status import RepaymentStatus
from app.models.loan_details import LoanDetails
from app.models.applicant_details import ApplicantDetails
from sqlalchemy import and_

router = APIRouter()

@router.get("/")
def get_paidpending_applications_list(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """
    Get all applications currently in "Paid(Pending Approval)" status
    
    Shows:
    - Loan ID
    - Applicant details
    - Current status
    - Amount collected
    - PTP date
    - Demand date
    """
    try:
        # Get the "Paid(Pending Approval)" status ID
        paid_pending_status = db.query(RepaymentStatus).filter(
            RepaymentStatus.repayment_status == "Paid(Pending Approval)"
        ).first()
        
        if not paid_pending_status:
            return {"message": "No 'Paid(Pending Approval)' status found", "applications": []}
        
        # Get all payment details with this status
        payment_records = db.query(PaymentDetails).filter(
            PaymentDetails.repayment_status_id == paid_pending_status.id
        ).all()
        
        applications = []
        
        for payment in payment_records:
            # Get loan details
            loan = db.query(LoanDetails).filter(
                LoanDetails.loan_application_id == payment.loan_application_id
            ).first()
            
            if loan:
                # Get applicant details
                applicant = db.query(ApplicantDetails).filter(
                    ApplicantDetails.applicant_id == loan.applicant_id
                ).first()
                
                # Get current status name
                current_status = db.query(RepaymentStatus).filter(
                    RepaymentStatus.id == payment.repayment_status_id
                ).first()
                
                application_data = {
                    "loan_id": payment.loan_application_id,
                    "repayment_id": str(payment.id),  # 🎯 ADDED! Repayment ID
                    "applicant_id": loan.applicant_id,
                    "applicant_name": f"{applicant.first_name or ''} {applicant.middle_name or ''} {applicant.last_name or ''}".strip().replace('  ', ' ') if applicant else "Unknown",
                    "current_status": current_status.repayment_status if current_status else "Unknown",
                    "amount_collected": float(payment.amount_collected) if payment.amount_collected else 0,
                    "ptp_date": payment.ptp_date.isoformat() if payment.ptp_date else None,
                    "demand_date": payment.demand_date.isoformat() if payment.demand_date else None,
                    "demand_amount": float(payment.demand_amount) if payment.demand_amount else 0,
                    "payment_date": payment.payment_date.isoformat() if payment.payment_date else None,
                    "updated_at": payment.updated_at.isoformat() if payment.updated_at else None
                }
                
                applications.append(application_data)
        
        return {
            "total_applications": len(applications),
            "status": "Paid(Pending Approval)",
            "applications": applications
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get paid pending applications: {str(e)}")

@router.get("/{loan_id}")
def get_paidpending_application_status(
    loan_id: str = Path(..., description="The loan ID to check for paid pending status"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """
    Get the current status of a specific application
    
    Shows:
    - Current status
    - Amount collected
    - PTP date
    - Demand date
    - Whether it's in "Paid(Pending Approval)" status
    """
    try:
        # Convert loan_id to integer
        try:
            loan_id_int = int(loan_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid loan_id: {loan_id}. Must be a valid integer.")
        
        # Get payment details for this loan
        payment_record = db.query(PaymentDetails).filter(
            PaymentDetails.loan_application_id == loan_id_int
        ).first()
        
        if not payment_record:
            raise HTTPException(
                status_code=404, 
                detail=f"No payment record found for loan_id: {loan_id_int}"
            )
        
        # Get current status name
        current_status = db.query(RepaymentStatus).filter(
            RepaymentStatus.id == payment_record.repayment_status_id
        ).first()
        
        # Check if it's in "Paid(Pending Approval)" status
        is_paid_pending = False
        if current_status:
            is_paid_pending = current_status.repayment_status == "Paid(Pending Approval)"
        
        # Get loan and applicant details
        loan = db.query(LoanDetails).filter(
            LoanDetails.loan_application_id == loan_id_int
        ).first()
        
        applicant = None
        if loan:
            applicant = db.query(ApplicantDetails).filter(
                ApplicantDetails.applicant_id == loan.applicant_id
            ).first()
        
        return {
            "loan_id": loan_id_int,
            "repayment_id": str(payment_record.id),  # 🎯 ADDED! Repayment ID
            "applicant_id": loan.applicant_id if loan else None,
            "applicant_name": f"{applicant.first_name or ''} {applicant.middle_name or ''} {applicant.last_name or ''}".strip().replace('  ', ' ') if applicant else "Unknown",
            "current_status": current_status.repayment_status if current_status else "Unknown",
            "status_id": payment_record.repayment_status_id,
            "is_paid_pending": is_paid_pending,
            "amount_collected": float(payment_record.amount_collected) if payment_record.amount_collected else 0,
            "ptp_date": payment_record.ptp_date.isoformat() if payment_record.ptp_date else None,
            "demand_date": payment_record.demand_date.isoformat() if payment_record.demand_date else None,
            "demand_amount": float(payment_record.demand_amount) if payment_record.demand_amount else 0,
            "payment_date": payment_record.payment_date.isoformat() if payment_record.payment_date else None,
            "updated_at": payment_record.updated_at.isoformat() if payment_record.updated_at else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get application status: {str(e)}")

@router.post("/approve")
def approve_reject_paidpending(
    approval_data: PaidPendingApprovalRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """
    Process paidpending approval - accept or reject
    
    Workflow:
    1. RM selects "paidpending" → Goes to approval
    2. Approver can Accept or Reject
    3. If Accept → Status becomes "Paid" and payment_date is set to current date
    4. If Reject → 
       - If amount exists → Status becomes "Partially Paid"
       - If no amount → Status becomes "Paid Rejected"
    """
    try:
        result = process_paidpending_approval(
            db=db, 
            approval_data=approval_data,
            current_user_id=current_user["id"]  # Pass current logged-in user ID
        )
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process approval: {str(e)}")
