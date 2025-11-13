from fastapi import APIRouter, Depends, HTTPException, Form, Query
from sqlalchemy.orm import Session
from typing import List

from app.core.deps import get_db, get_current_user
from app.schemas.applicant_document import (
    ApplicantDocumentPresignRequest,
    ApplicantDocumentCreate,
    ApplicantDocumentResponse,
)
from app.crud.applicant_document import create_document
from app.services.s3 import presign_put, presign_post, make_key_for_document, presign_get


router = APIRouter()


@router.post("/presign")
def get_presigned_url(
    loan_application_id: int = Form(...),
    filename: str = Form(...),
    content_type: str = Form(...),
    visit_type: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if not content_type.startswith(("image/")):
        raise HTTPException(status_code=400, detail="Only image uploads are allowed")
    key = make_key_for_document(loan_application_id, current_user["id"], filename, visit_type)
    # Prefer POST; clients that only support PUT can switch key below
    post = presign_post(key, content_type)
    return {"method": "POST", "upload_url": post["url"], "fields": post["fields"], "s3_key": key}


@router.post("/", response_model=ApplicantDocumentResponse)
def finalize_upload(
    payload: ApplicantDocumentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # For field visit SELFIE, caller should set doc_category_id to category ID for 'SELFIE'
    doc = create_document(db, payload, uploaded_by=current_user["id"])
    return ApplicantDocumentResponse(
        id=doc.id,
        applicant_id=doc.applicant_id,
        loan_application_id=doc.loan_application_id,
        repayment_id=doc.repayment_id,
        field_visit_location_id=doc.field_visit_location_id,
        doc_category_id=doc.doc_category_id,
        file_name=doc.file_name,
        s3_key=doc.s3_key,
        # PRIVATE: return a signed GET URL for the uploaded object
        url=presign_get(doc.s3_key),
        notes=doc.notes,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.get("/by-loan", response_model=List[ApplicantDocumentResponse])
def list_by_loan(
    loan_application_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.models.applicant_document import ApplicantDocument
    items = db.query(ApplicantDocument).filter(ApplicantDocument.loan_application_id == loan_application_id).order_by(ApplicantDocument.created_at.desc()).all()
    return [
        ApplicantDocumentResponse(
            id=doc.id,
            applicant_id=doc.applicant_id,
            loan_application_id=doc.loan_application_id,
            repayment_id=doc.repayment_id,
            field_visit_location_id=doc.field_visit_location_id,
            doc_category_id=doc.doc_category_id,
            file_name=doc.file_name,
            s3_key=doc.s3_key,
            # PRIVATE: return a signed GET URL for each object
            url=presign_get(doc.s3_key),
            notes=doc.notes,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )
        for doc in items
    ]


@router.get("/by-category", response_model=List[ApplicantDocumentResponse])
def get_documents_by_category(
    loan_application_id: int = Query(..., description="Loan application ID"),
    doc_category_id: int = Query(..., description="Document category ID (e.g., 11 for FI docs, other IDs for images, etc.)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get documents by loan_application_id and doc_category_id.
    - doc_category_id = 11 → Returns FI PDFs
    - doc_category_id = <image_category_id> → Returns images
    - doc_category_id = <any_category_id> → Returns that category's documents
    """
    from app.models.applicant_document import ApplicantDocument
    
    items = db.query(ApplicantDocument)\
        .filter(
            ApplicantDocument.loan_application_id == loan_application_id,
            ApplicantDocument.doc_category_id == doc_category_id
        )\
        .order_by(ApplicantDocument.created_at.desc())\
        .all()
    
    return [
        ApplicantDocumentResponse(
            id=doc.id,
            applicant_id=doc.applicant_id,
            loan_application_id=doc.loan_application_id,
            repayment_id=doc.repayment_id,
            field_visit_location_id=doc.field_visit_location_id,
            doc_category_id=doc.doc_category_id,
            file_name=doc.file_name,
            s3_key=doc.s3_key,
            url=presign_get(doc.s3_key),
            notes=doc.notes,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )
        for doc in items
    ]


