from sqlalchemy import Column, Integer, Text, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.base import Base

class ActivityLog(Base):
    __tablename__ = "activity_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    loan_application_id = Column(Integer, ForeignKey("loan_details.loan_application_id"), nullable=False)
    payment_id = Column(Integer, ForeignKey("payment_details.id"), nullable=True)
    field_type_id = Column(Integer, ForeignKey("field_types.id"), nullable=False)
    
    # Values (storing IDs)
    previous_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    
    # Metadata
    changed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    loan_details = relationship("LoanDetails")
    payment_details = relationship("PaymentDetails")
    changed_by_user = relationship("User")
    field_type = relationship("FieldTypes")
