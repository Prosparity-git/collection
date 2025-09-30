from sqlalchemy import Column, Integer, DECIMAL, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.base import Base

class FieldVisitLocation(Base):
    __tablename__ = "field_visit_locations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    loan_application_id = Column(Integer, ForeignKey("loan_details.loan_application_id"), nullable=False)
    payment_details_id = Column(Integer, ForeignKey("payment_details.id"), nullable=True)
    agent_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    visit_type_id = Column(Integer, ForeignKey("visit_types.id"), nullable=False, default=1)
    latitude = Column(DECIMAL(10, 8), nullable=False)
    longitude = Column(DECIMAL(11, 8), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    loan_details = relationship("LoanDetails", back_populates="field_visits")
    payment_details = relationship("PaymentDetails", back_populates="field_visits")
    agent = relationship("User", back_populates="field_visits")
    visit_type = relationship("VisitType", back_populates="field_visits")
