from sqlalchemy import Column, Integer, String, TIMESTAMP, func
from sqlalchemy.orm import relationship
from app.db.base import Base

class Relationship(Base):
    __tablename__ = "relationship"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    relationship_name = Column(String(50), nullable=False, unique=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    co_applicants = relationship("CoApplicant", back_populates="relationship")

