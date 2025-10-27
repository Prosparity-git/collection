from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import aliased
from typing import List, Dict, Any
from app.models.payment_details import PaymentDetails
from app.models.loan_details import LoanDetails
from app.models.applicant_details import ApplicantDetails
from app.models.branch import Branch
from app.models.dealer import Dealer
from app.models.lenders import Lender
from app.models.user import User
from app.models.comments import Comments
from app.models.repayment_status import RepaymentStatus

def get_paid_pending_applications(
    db: Session,
    skip: int = 0,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Get all applications that are in 'Paid(Pending Approval)' status"""
    
    # Get the Paid(Pending Approval) status ID
    paid_pending_approval_status = db.query(RepaymentStatus).filter(
        RepaymentStatus.repayment_status == "Paid(Pending Approval)"
    ).first()
    
    if not paid_pending_approval_status:
        return []
    
    # Create aliases for User table (RM and TL)
    RM = aliased(User)
    TL = aliased(User)
    
    # Query for paid pending approval applications
    query = (
        db.query(
            ApplicantDetails.applicant_id.label("loan_id"),
            ApplicantDetails.first_name,
            ApplicantDetails.last_name,
            PaymentDetails.demand_amount.label("emi_amount"),
            PaymentDetails.id.label("repayment_id"),  # 🎯 CHANGED! From demand_date to repayment_id
            PaymentDetails.ptp_date.label("ptp_date"),
            PaymentDetails.amount_collected.label("amount_collected"),
            Branch.name.label("branch"),
            RM.name.label("rm_name"),
            TL.name.label("tl_name"),
            Dealer.name.label("dealer"),
            Lender.name.label("lender"),
            PaymentDetails.id.label("payment_id")
        )
        .select_from(PaymentDetails)
        .join(LoanDetails, PaymentDetails.loan_application_id == LoanDetails.loan_application_id)
        .join(ApplicantDetails, LoanDetails.applicant_id == ApplicantDetails.applicant_id)
        .join(Branch, ApplicantDetails.branch_id == Branch.id)
        .join(Dealer, ApplicantDetails.dealer_id == Dealer.id)
        .join(Lender, LoanDetails.lenders_id == Lender.id)
        .join(RM, PaymentDetails.Collection_relationship_manager_id == RM.id)
        .join(TL, LoanDetails.source_relationship_manager_id == TL.id)
        .filter(PaymentDetails.repayment_status_id == paid_pending_approval_status.id)
        .order_by(desc(PaymentDetails.demand_date))
    )
    
    total = query.count()
    results = []
    
    for row in query.offset(skip).limit(limit).all():
        # Get comments for this payment (type 2 - paid pending comments)
        comments = db.query(Comments).filter(
            and_(
                Comments.repayment_id == str(row.payment_id),
                Comments.comment_type == 2  # Paid pending comments
            )
        ).order_by(desc(Comments.commented_at)).all()
        
        comment_list = [c.comment for c in comments]
        
        results.append({
            "loan_id": str(row.loan_id),
            "applicant_name": f"{row.first_name or ''} {row.last_name or ''}".strip(),
            "emi_amount": float(row.emi_amount) if row.emi_amount else None,
            "repayment_id": str(row.repayment_id),  # 🎯 CHANGED! From demand_date to repayment_id
            "ptp_date": row.ptp_date.strftime('%Y-%m-%d') if row.ptp_date else None,
            "amount_collected": float(row.amount_collected) if row.amount_collected else None,
            "branch": row.branch,
            "rm_name": row.rm_name,
            "tl_name": row.tl_name,
            "dealer": row.dealer,
            "lender": row.lender,
            "comments": comment_list
        })
    
    return results
