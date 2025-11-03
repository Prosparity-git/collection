from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ApplicantDocumentPresignRequest(BaseModel):
    loan_application_id: int
    filename: str
    content_type: str


class ApplicantDocumentCreate(BaseModel):
    applicant_id: str
    loan_application_id: int
    repayment_id: Optional[int] = None
    field_visit_location_id: Optional[int] = None
    doc_category_id: int = 4
    file_name: str
    s3_key: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    notes: Optional[str] = None


class ApplicantDocumentResponse(BaseModel):
    id: int
    applicant_id: str
    loan_application_id: int
    repayment_id: Optional[int] = None
    field_visit_location_id: Optional[int] = None
    doc_category_id: int
    file_name: str
    s3_key: str
    url: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


