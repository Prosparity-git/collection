from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.schemas.otp import SendOTPRequest, SendOTPResponse, VerifyOTPRequest, VerifyOTPResponse
from app.services.msg91_service import msg91_service
from app.models.loan_details import LoanDetails
from app.models.applicant_details import ApplicantDetails
from app.models.co_applicant import CoApplicant
from app.models.communication_template import CommunicationTemplate
from app.models.communication import Communication
from app.models.communication_log import CommunicationLog
from app.crud.status_management import update_status_management
from app.schemas.status_management import StatusManagementUpdate
from datetime import datetime
import redis
import json
from app.core.config import settings

router = APIRouter()

# Redis connection (optional - fallback if Redis not available)
try:
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client.ping()  # Test connection
except:
    redis_client = None

def get_contact_details(db: Session, loan_id: int, contact_type: str):
    """Get contact details based on contact type and loan_id"""
    if contact_type == "applicant":
        # Get applicant details
        loan_details = db.query(LoanDetails).filter(
            LoanDetails.loan_application_id == loan_id
        ).first()
        
        if not loan_details:
            return None, None, "Loan not found"
        
        applicant = db.query(ApplicantDetails).filter(
            ApplicantDetails.applicant_id == loan_details.applicant_id
        ).first()
        
        if not applicant or not applicant.mobile:
            return None, None, "Applicant mobile number not found"
        
        return applicant.mobile, applicant.applicant_id, None
    
    elif contact_type == "co_applicant":
        # Get co-applicant details
        co_applicant = db.query(CoApplicant).filter(
            CoApplicant.loan_application_id == loan_id
        ).first()
        
        if not co_applicant or not co_applicant.mobile:
            return None, None, "Co-applicant mobile number not found"
        
        return co_applicant.mobile, f"co_app_{co_applicant.id}", None
    
    else:
        return None, None, f"Invalid contact type: {contact_type}. Only 'applicant' and 'co_applicant' are supported."

@router.post("/send-otp-payment", response_model=SendOTPResponse)
def send_otp_payment(
    request: SendOTPRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Send OTP for payment verification"""
    try:
        # 1. Get contact details based on contact type
        mobile_number, contact_id, error_msg = get_contact_details(
            db, request.loan_id, request.contact_type.value
        )
        
        if error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 2. Get OTP template by ID (default to ID=1 for OTP_SEND)
        template_id = request.template_key if request.template_key.isdigit() else "1"
        template = db.query(CommunicationTemplate).filter(
            CommunicationTemplate.id == int(template_id),
            CommunicationTemplate.status == "ACTIVE"
        ).first()
        
        if not template:
            raise HTTPException(status_code=400, detail=f"OTP template not found for ID: {template_id}")
        
        # 3. Generate OTP
        otp_code = msg91_service.generate_otp()
        
        # 4. Send OTP via MSG91
        success, result = msg91_service.send_otp(
            mobile_number=mobile_number,
            otp=otp_code,
            template_id=template.template_id
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=result["message"])
        
        # 5. Create communication record
        communication = Communication(
            loan_id=request.loan_id,
            applicant_id=contact_id,  # This will be the contact ID (applicant_id, co_app_1, ref_1, guar_1)
            repayment_id=request.repayment_id,
            template_id=template.template_id,
            send_by=current_user["id"],
            message_id=result.get("request_id"),
            delivery_status_id=1 if success else 2,
            delivered_date=datetime.utcnow() if success else None
        )
        db.add(communication)
        db.flush()  # Get communication_id
        
        # 6. Log communication event
        log_event = CommunicationLog(
            communication_id=communication.communication_id,
            event_type="api_success" if success else "api_failed",
            meta_data=json.dumps(result)
        )
        db.add(log_event)
        
        # 7. Store OTP in Redis (5 min TTL)
        if redis_client:
            redis_key = f"otp:{request.loan_id}:{request.repayment_id}:{mobile_number}"
            redis_client.setex(redis_key, 300, otp_code)  # 5 minutes = 300 seconds
        
        db.commit()
        
        # 8. Return response
        masked_mobile = mobile_number[:3] + "****" + mobile_number[-2:]
        return SendOTPResponse(
            success=True,
            message=f"OTP sent successfully to {request.contact_type.value}",
            mobile_number=masked_mobile,
            communication_id=communication.communication_id,
            expires_in_minutes=settings.MSG91_OTP_EXPIRE_MINUTES
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to send OTP: {str(e)}")

@router.post("/verify-otp-payment", response_model=VerifyOTPResponse)
def verify_otp_payment(
    request: VerifyOTPRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Verify OTP and update payment status"""
    try:
        # 1. Get contact details based on contact type
        mobile_number, contact_id, error_msg = get_contact_details(
            db, request.loan_id, request.contact_type.value
        )
        
        if error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 2. Check if OTP exists in Redis (optional check)
        if redis_client:
            redis_key = f"otp:{request.loan_id}:{request.repayment_id}:{mobile_number}"
            if not redis_client.exists(redis_key):
                raise HTTPException(status_code=400, detail="OTP not found or expired")
        
        # 3. Verify OTP with MSG91
        success, result = msg91_service.verify_otp(
            mobile_number=mobile_number,
            otp=request.otp_code
        )
        
        # 3. Find communication record for logging
        communication = db.query(Communication).filter(
            Communication.loan_id == request.loan_id,
            Communication.repayment_id == request.repayment_id
        ).order_by(Communication.created_at.desc()).first()
        
        # 4. Log verification event
        if communication:
            log_event = CommunicationLog(
                communication_id=communication.communication_id,
                event_type="verify_success" if success else "verify_failed",
                meta_data=json.dumps(result)
            )
            db.add(log_event)
        
        if not success:
            raise HTTPException(status_code=400, detail=result["message"])
        
        # 5. Delete OTP from Redis (one-time use)
        if redis_client:
            redis_key = f"otp:{request.loan_id}:{request.repayment_id}:{mobile_number}"
            redis_client.delete(redis_key)
        
        # 6. Update payment status (this will be called by frontend separately)
        # For now, just return success - frontend will call status update API
        
        db.commit()
        
        return VerifyOTPResponse(
            success=True,
            message=f"OTP verified successfully for {request.contact_type.value}",
            mobile_number=mobile_number,
            verified_at=datetime.utcnow(),
            payment_status_updated=False  # Frontend will handle status update
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to verify OTP: {str(e)}")

@router.post("/verify-otp-and-update-status")
def verify_otp_and_update_status(
    request: VerifyOTPRequest,
    status_update: StatusManagementUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Verify OTP and immediately update payment status"""
    try:
        # 1. Verify OTP first
        verify_response = verify_otp_payment(request, db, current_user)
        
        if not verify_response.success:
            return verify_response
        
        # 2. Update payment status
        result = update_status_management(
            db=db,
            loan_id=str(request.loan_id),
            status_data=status_update,
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "message": "OTP verified and payment status updated successfully",
            "mobile_number": verify_response.mobile_number,
            "verified_at": verify_response.verified_at,
            "payment_status": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to verify OTP and update status: {str(e)}")
