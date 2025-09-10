from sqlalchemy import Column, Integer, String, TIMESTAMP, func
from app.db.base import Base

class FieldTypes(Base):
    __tablename__ = "field_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    field_name = Column(String(50), unique=True, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
