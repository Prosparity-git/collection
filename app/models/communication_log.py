from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.base import Base

class CommunicationLog(Base):
    __tablename__ = "communication_log"
    
    event_id = Column(Integer, primary_key=True, autoincrement=True)
    communication_id = Column(Integer, ForeignKey("communication.communication_id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # api_success, send, delivered, failed, verify_success, verify_failed, read, click
    event_time = Column(DateTime, server_default=func.now())
    meta_data = Column(Text, nullable=True)
    
    # Relationships
    communication = relationship("Communication", back_populates="logs")
