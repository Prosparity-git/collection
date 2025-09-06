from sqlalchemy import Column, Integer, String, Enum, TIMESTAMP, JSON, func
from app.db.base import Base
import enum

class AuditActionEnum(str, enum.Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"

class AuditPaymentDetails(Base):
    __tablename__ = "payment_details_audit"
    audit_id = Column(Integer, primary_key=True, autoincrement=True)
    payment_id = Column(Integer)
    loan_application_id = Column(Integer)
    action_type = Column(Enum(AuditActionEnum))
    old_data = Column(JSON)
    new_data = Column(JSON)
    changed_by = Column(String(45))
    action_timestamp = Column(TIMESTAMP, server_default=func.now()) 