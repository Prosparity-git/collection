from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class DpdMonthlySnapshot(Base):
    __tablename__ = "dpd_monthly_snapshot"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(String(255), nullable=True, index=True)
    loan_application_id = Column(Integer, ForeignKey("loan_details.loan_application_id"), nullable=True, index=True)
    as_of_month = Column(Date, nullable=True)
    dpd_bucket_name = Column(String(50), nullable=True)
    received_at = Column(DateTime, nullable=True)

    # Relationship with LoanDetails
    loan_details = relationship("LoanDetails", back_populates="dpd_snapshots")
