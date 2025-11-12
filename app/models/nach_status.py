from sqlalchemy import Column, Integer, String
from app.db.base import Base


class NachStatus(Base):
    __tablename__ = "nach_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nach_reason = Column(String(255), nullable=True)



