from sqlalchemy import Column, Integer, DECIMAL, DATE, DATETIME, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class VehicleRepossessionStatus(Base):
    __tablename__ = "vehicle_repossession_status"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    loan_application_id = Column(Integer, ForeignKey("loan_details.loan_application_id"), nullable=False)
    repayment_id = Column(Integer, ForeignKey("payment_details.id"), nullable=True)
    vehicle_status = Column(Integer, ForeignKey("vehicle_status.id"), nullable=True)
    repossession_date = Column(DATE, nullable=True)
    repossession_sale_date = Column(DATE, nullable=True)
    repossession_sale_amount = Column(DECIMAL(12, 2), nullable=True)
    created_at = Column(DATETIME, nullable=True)
    updated_at = Column(DATETIME, nullable=True)
    
    # Relationships
    loan_details = relationship("LoanDetails", back_populates="vehicle_repossession_statuses")
    payment_details = relationship("PaymentDetails", back_populates="vehicle_repossession_statuses")
    vehicle_status_rel = relationship("VehicleStatus", back_populates="vehicle_repossession_statuses")
