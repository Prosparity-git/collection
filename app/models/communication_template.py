from sqlalchemy import Column, Integer, String, Text, DateTime, func, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base

class CommunicationTemplate(Base):
    __tablename__ = "communication_template"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(String(255), nullable=False, unique=True, index=True)
    template_name = Column(String(100), nullable=False)
    channel_type = Column(Integer, nullable=False)  # 1=SMS, 2=WhatsApp, 3=Email
    content = Column(Text, nullable=True)
    subject = Column(String(255), nullable=True)
    dlt_id = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default='ACTIVE')
    variables = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    communications = relationship("Communication", back_populates="template")
