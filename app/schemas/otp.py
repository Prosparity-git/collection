from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
from enum import Enum

class ContactTypeEnum(str, Enum):
    applicant = "applicant"
    co_applicant = "co_applicant"

class SendOTPRequest(BaseModel):
    loan_id: int
    repayment_id: int
    template_key: Optional[str] = "1"  # Database ID of the template
    contact_type: Optional[ContactTypeEnum] = ContactTypeEnum.applicant  # Who to send OTP to
    amount: Optional[float] = None  # Optional override for amount to send in SMS
    
    @validator('loan_id')
    def validate_loan_id(cls, v):
        if v <= 0:
            raise ValueError('Loan ID must be positive')
        return v
    
    @validator('repayment_id')
    def validate_repayment_id(cls, v):
        if v <= 0:
            raise ValueError('Repayment ID must be positive')
        return v

class SendOTPResponse(BaseModel):
    success: bool
    message: str
    mobile_number: str  # masked
    communication_id: int
    expires_in_minutes: int

class VerifyOTPRequest(BaseModel):
    loan_id: int
    repayment_id: int
    otp_code: str
    contact_type: Optional[ContactTypeEnum] = ContactTypeEnum.applicant  # Who verified the OTP
    
    @validator('loan_id')
    def validate_loan_id(cls, v):
        if v <= 0:
            raise ValueError('Loan ID must be positive')
        return v
    
    @validator('repayment_id')
    def validate_repayment_id(cls, v):
        if v <= 0:
            raise ValueError('Repayment ID must be positive')
        return v
    
    @validator('otp_code')
    def validate_otp_code(cls, v):
        if not v.isdigit():
            raise ValueError('OTP must contain only digits')
        if len(v) != 4:  # Changed to 4 digits
            raise ValueError('OTP must be exactly 4 digits')
        return v

class VerifyOTPResponse(BaseModel):
    success: bool
    message: str
    mobile_number: str
    verified_at: Optional[datetime] = None
    payment_status_updated: Optional[bool] = False

class ResendOTPRequest(BaseModel):
    loan_id: int
    repayment_id: int
    contact_type: Optional[ContactTypeEnum] = ContactTypeEnum.applicant
    retry_type: Optional[str] = "text"  # 'text' or 'voice'
    
    @validator('loan_id')
    def validate_loan_id(cls, v):
        if v <= 0:
            raise ValueError('Loan ID must be positive')
        return v
    
    @validator('repayment_id')
    def validate_repayment_id(cls, v):
        if v <= 0:
            raise ValueError('Repayment ID must be positive')
        return v

class ResendOTPResponse(BaseModel):
    success: bool
    message: str
    mobile_number: str  # masked
