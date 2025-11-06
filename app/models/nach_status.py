from sqlalchemy import Column, Integer, String
from app.db.base import Base


class NachStatus(Base):
    __tablename__ = "nach_status"

    id = Column(Integer, primary_key=True, index=True)
    nach_status = Column(String(50), nullable=False, unique=True)
    reason = Column(String(255), nullable=True)


