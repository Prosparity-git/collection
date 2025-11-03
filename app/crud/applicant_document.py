from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.applicant_document import ApplicantDocument
from app.schemas.applicant_document import ApplicantDocumentCreate
from app.core.config import settings


def create_document(db: Session, data: ApplicantDocumentCreate, uploaded_by: int) -> ApplicantDocument:
    doc = ApplicantDocument(
        applicant_id=data.applicant_id,
        loan_application_id=data.loan_application_id,
        repayment_id=data.repayment_id,
        field_visit_location_id=data.field_visit_location_id,
        doc_category_id=data.doc_category_id,
        uploaded_by=uploaded_by,
        file_name=data.file_name,
        s3_key=data.s3_key,
        # optional fields not persisted in table but can be stored in future
        notes=data.notes,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def list_documents_by_loan(db: Session, loan_application_id: int):
    return db.query(ApplicantDocument) \
        .filter(ApplicantDocument.loan_application_id == loan_application_id) \
        .order_by(desc(ApplicantDocument.created_at)) \
        .all()


