from sqlalchemy import Column, Integer, BigInteger, String, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.base import Base


class DocCategory(Base):
    __tablename__ = "doc_category"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), unique=True, nullable=False)
    display_name = Column(String(128), nullable=False)
    is_required = Column(Integer, nullable=False, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())


class ApplicantDocument(Base):
    __tablename__ = "applicant_document"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    applicant_id = Column(String(100), nullable=False, index=True)
    loan_application_id = Column(Integer, nullable=False, index=True)
    repayment_id = Column(Integer, nullable=True, index=True)
    doc_category_id = Column(Integer, nullable=False, index=True)
    uploaded_by = Column(Integer, nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    s3_key = Column(String(512), nullable=False)
    notes = Column(String(512), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Optional relationships (FKs not declared at DB level in your schema)
    # You can wire relationships via primaryjoin when needed


