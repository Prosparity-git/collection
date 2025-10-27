from sqlalchemy import Column, Integer, String, TIMESTAMP, func
from app.db.base import Base

class RelationshipWithApplicant(Base):
    __tablename__ = "relationship_with_applicant"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    relationship_name = Column(String(50), nullable=False, unique=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
