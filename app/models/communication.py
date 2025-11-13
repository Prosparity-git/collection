from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Communication(Base):
    __tablename__ = "communication"
    
    communication_id = Column(Integer, primary_key=True, autoincrement=True)
    loan_id = Column(Integer, nullable=False, index=True)
    applicant_id = Column(String(100), nullable=False, index=True)  # Always the main applicant's ID
    contact_type = Column(Integer, nullable=True)  # 1=applicant, 2=co_applicant
    repayment_id = Column(Integer, nullable=True)
    template_id = Column(String(255), ForeignKey("communication_template.template_id"), nullable=False, index=True)
    delivery_status_id = Column(Integer, nullable=False, default=0)  # 0=pending, 1=delivered, 2=failed
    message_id = Column(String(100), nullable=True, index=True)
    sent_date = Column(DateTime, server_default=func.now())
    delivered_date = Column(DateTime, nullable=True)
    read_date = Column(DateTime, nullable=True)
    clicked_date = Column(DateTime, nullable=True)
    send_by = Column(Integer, nullable=True)  # user_id
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    template = relationship("CommunicationTemplate", back_populates="communications")
    logs = relationship("CommunicationLog", back_populates="communication")
