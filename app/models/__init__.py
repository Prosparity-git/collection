from .applicant_details import ApplicantDetails
from .ownership_type import OwnershipType
from .branch import Branch
from .dealer import Dealer
from .lenders import Lender
from .loan_details import LoanDetails
from .payment_details import PaymentDetails
from .repayment_status import RepaymentStatus
from .user import User
from .comments import Comments
from .calling import Calling
from .contact_calling import ContactCalling
from .demand_calling import DemandCalling
from .co_applicant import CoApplicant
from .guarantor import Guarantor
from .reference import Reference
from .audit_applicant_details import AuditApplicantDetails
from .audit_payment_details import AuditPaymentDetails
from .vehicle_status import VehicleStatus
from .field_types import FieldTypes
from .activity_log import ActivityLog

# Import Base for database operations
from app.db.base import Base 