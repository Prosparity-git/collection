from sqlalchemy import Column, Integer, Enum, TIMESTAMP, func
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum

class VehicleStatusEnum(str, enum.Enum):
    Repossessed = "Repossessed"
    Need_to_repossess = "Need to repossess"
    Third_party = "Third party"
    None_ = "none"

class VehicleStatus(Base):
    __tablename__ = "vehicle_status"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_status = Column(
        Enum(VehicleStatusEnum, values_callable=lambda x: [e.value for e in x]), unique=True
    )
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    vehicle_repossession_statuses = relationship("VehicleRepossessionStatus", back_populates="vehicle_status_rel") 