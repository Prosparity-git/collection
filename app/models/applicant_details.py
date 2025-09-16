from sqlalchemy import Column, String, Integer, Text, TIMESTAMP, ForeignKey, func, DECIMAL
from sqlalchemy.orm import relationship
from app.db.base import Base
#NEW MODELS WITHOUT FOREIGN KEYS
class ApplicantDetails(Base):
    __tablename__ = "applicant_details"
    id = Column(Integer, primary_key=True, autoincrement=True)
    applicant_id = Column(String(100), unique=True, index=True)
    first_name = Column(String(100))
    middle_name = Column(String(100))
    last_name = Column(String(100))
    mobile = Column(String(15))
    address_line1 = Column(Text)
    address_line2 = Column(Text)
    address_line3 = Column(Text)
    city = Column(Text)
    state = Column(Text)
    pincode = Column(Integer)
    ownership_type_id = Column(Integer, ForeignKey("ownership_type.id"))
    branch_id = Column(Integer, ForeignKey("branch.id"))
    dealer_id = Column(Integer, ForeignKey("dealer.id"))
    fi_loaction = Column(Text)  # Fixed to match database column name
    latitude = Column(DECIMAL(10, 8), nullable=True)
    longitude = Column(DECIMAL(11, 8), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships - now properly defined with foreign keys
    ownership_type = relationship("OwnershipType", back_populates="applicants")
    branch = relationship("Branch", back_populates="applicants")
    dealer = relationship("Dealer", back_populates="applicants")
    loan_details = relationship("LoanDetails", back_populates="applicant") 