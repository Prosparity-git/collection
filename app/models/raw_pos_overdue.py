from sqlalchemy import Column, BigInteger, String, Integer, Date, Float, Text, TIMESTAMP, func
from sqlalchemy.orm import relationship
from app.db.base import Base

class RawPosOverdue(Base):
    __tablename__ = "raw_pos_overdue"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    applicant_id = Column(String(64), nullable=False, index=True)
    loan_application_id = Column(Integer, nullable=True, index=True)
    pos_date = Column(Date, nullable=False)
    pos = Column(Float, nullable=True)
    overdue_date = Column(String(40), nullable=False)
    overdue = Column(Float, nullable=True)
    nach_months = Column(Date, nullable=True)
    nach_reason = Column(Text, nullable=True)
    create_date = Column(TIMESTAMP, nullable=False, server_default=func.now())










