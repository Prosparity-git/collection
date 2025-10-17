from sqlalchemy import Column, Integer, String, TIMESTAMP, func
from app.db.base import Base

class PaymentMode(Base):
    __tablename__ = "payment_mode"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    mode_name = Column(String(50), nullable=False)
    create_at = Column(TIMESTAMP, server_default=func.now())


