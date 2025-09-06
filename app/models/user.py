from sqlalchemy import Column, Integer, String, TIMESTAMP, func, Enum, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    user_name = Column(String(100), nullable=False)  # 🎯 ADDED! Required field from DB
    password = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    mobile = Column(String(15), nullable=True)  # 🎯 ADDED! From DB schema
    role = Column(String(50), nullable=True)
    status = Column(Enum('active', 'inactive'), default='active', nullable=True)  # 🎯 ADDED! From DB schema
    # 🎯 NEW COLUMNS FOR LOGIN/LOGOUT TRACKING
    last_login_time = Column(DateTime, nullable=True)
    last_logout_time = Column(DateTime, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    comments = relationship("Comments", back_populates="user")
    calls = relationship("Calling", back_populates="caller") 