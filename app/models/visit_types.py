from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, func
from sqlalchemy.orm import relationship
from app.db.base import Base

class VisitType(Base):
    __tablename__ = "visit_types"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    type_name = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    field_visits = relationship("FieldVisitLocation", back_populates="visit_type")
