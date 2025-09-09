from sqlalchemy.orm import Session, aliased
from sqlalchemy import desc, func, or_, and_
from app.models.loan_details import LoanDetails
from app.models.applicant_details import ApplicantDetails
from app.models.payment_details import PaymentDetails
from app.models.branch import Branch
from app.models.dealer import Dealer
from app.models.lenders import Lender
from app.models.comments import Comments
from app.models.user import User
from app.models.repayment_status import RepaymentStatus
from app.models.calling import Calling
from app.models.contact_calling import ContactCalling
from app.models.ownership_type import OwnershipType  # 🎯 ADDED! For House Ownership
from datetime import date, timedelta

def get_filtered_applications(
    db: Session,
    loan_id: str = "",  # 🎯 ADDED! Filter by specific loan ID
    emi_month: str = "", 
    search: str = "",
    branch: str = "",
    dealer: str = "",
    lender: str = "",
    status: str = "",
    rm_name: str = "",
    tl_name: str = "",
    ptp_date_filter: str = "",
    repayment_id: str = "",  # 🎯 ADDED! Filter by repayment_id (same as payment_id)
    demand_num: str = "",  # 🎯 ADDED! Filter by demand number
    offset: int = 0, 
    limit: int = 20
):
    RM = aliased(User)
    CurrentTL = aliased(User)

    # Create base query fields
    base_fields = [
        ApplicantDetails.applicant_id.label("application_id"),
        LoanDetails.loan_application_id.label("loan_id"),  # Added loan_id
        PaymentDetails.demand_num.label("demand_num"),  # 🎯 ADDED! Repayment Number
        ApplicantDetails.first_name,
        ApplicantDetails.last_name,
        ApplicantDetails.mobile,
        PaymentDetails.demand_amount.label("emi_amount"),
        RepaymentStatus.repayment_status.label("status"),
        PaymentDetails.demand_date.label('emi_month'),
        Branch.name.label("branch"),
        RM.name.label("rm_name"),
        CurrentTL.name.label("tl_name"),
        Dealer.name.label("dealer"),
        Lender.name.label("lender"),
        PaymentDetails.ptp_date.label("ptp_date"),
        PaymentDetails.mode.label("payment_mode"),
        PaymentDetails.amount_collected.label("amount_collected"),  # 🎯 ADDED! Amount collected
        PaymentDetails.id.label("payment_id"),
        LoanDetails.disbursal_amount.label("loan_amount"),  # 🎯 ADDED! Loan Amount
        LoanDetails.disbursal_date.label("disbursement_date"),  # 🎯 ADDED! Disbursement Date
        OwnershipType.ownership_type_name.label("house_ownership")  # 🎯 ADDED! House Ownership
    ]
    
    if emi_month:
        # 🎯 FIXED! If emi_month is provided, get that specific month's payment
        query = (
            db.query(*base_fields)
            .select_from(LoanDetails)
            .join(ApplicantDetails, LoanDetails.applicant_id == ApplicantDetails.applicant_id)
            .join(
                PaymentDetails,
                (PaymentDetails.loan_application_id == LoanDetails.loan_application_id) &
                (func.date_format(PaymentDetails.demand_date, '%b-%y') == emi_month)  # 🎯 Direct month filter
            )
            .join(Branch, ApplicantDetails.branch_id == Branch.id)
            .join(Dealer, ApplicantDetails.dealer_id == Dealer.id)
            .join(Lender, LoanDetails.lenders_id == Lender.id)
            .join(OwnershipType, ApplicantDetails.ownership_type_id == OwnershipType.id)
            .join(RM, LoanDetails.Collection_relationship_manager_id == RM.id)
            .outerjoin(CurrentTL, LoanDetails.current_team_lead_id == CurrentTL.id)
            .join(RepaymentStatus, PaymentDetails.repayment_status_id == RepaymentStatus.id)
        )
    else:
        # If no emi_month, use current logic (latest payment)
        latest_payment_subq = (
            db.query(
                PaymentDetails.loan_application_id,
                func.max(PaymentDetails.demand_date).label("max_demand_date")
            )
            .group_by(PaymentDetails.loan_application_id)
            .subquery()
        )
        
        query = (
            db.query(*base_fields)
            .select_from(LoanDetails)
            .join(ApplicantDetails, LoanDetails.applicant_id == ApplicantDetails.applicant_id)
            .join(
                latest_payment_subq,
                LoanDetails.loan_application_id == latest_payment_subq.c.loan_application_id
            )
            .join(
                PaymentDetails,
                (PaymentDetails.loan_application_id == latest_payment_subq.c.loan_application_id) &
                (PaymentDetails.demand_date == latest_payment_subq.c.max_demand_date)
            )
            .join(Branch, ApplicantDetails.branch_id == Branch.id)
            .join(Dealer, ApplicantDetails.dealer_id == Dealer.id)
            .join(Lender, LoanDetails.lenders_id == Lender.id)
            .join(OwnershipType, ApplicantDetails.ownership_type_id == OwnershipType.id)
            .join(RM, LoanDetails.Collection_relationship_manager_id == RM.id)
            .outerjoin(CurrentTL, LoanDetails.current_team_lead_id == CurrentTL.id)
            .join(RepaymentStatus, PaymentDetails.repayment_status_id == RepaymentStatus.id)
        )

    # Apply essential filters only
    if loan_id:
        # Support multiple comma-separated loan IDs
        loan_list = [l.strip() for l in loan_id.split(',') if l.strip()]
        if loan_list:
            try:
                loan_ids = [int(l) for l in loan_list]
                query = query.filter(LoanDetails.loan_application_id.in_(loan_ids))
            except ValueError:
                # If any value is not a valid integer, skip this filter
                pass
    
    if search:
        # Support multiple comma-separated search terms
        search_terms = [s.strip() for s in search.split(',') if s.strip()]
        if search_terms:
            search_conditions = []
            for term in search_terms:
                search_conditions.append(or_(
                    func.concat(ApplicantDetails.first_name, ' ', ApplicantDetails.last_name).ilike(f'%{term}%'),
                    ApplicantDetails.first_name.ilike(f'%{term}%'),
                    ApplicantDetails.last_name.ilike(f'%{term}%'),
                    ApplicantDetails.applicant_id.ilike(f'%{term}%')
                ))
            query = query.filter(or_(*search_conditions))
    
    if branch:
        # Support multiple comma-separated branch names
        branch_list = [b.strip() for b in branch.split(',') if b.strip()]
        if branch_list:
            query = query.filter(Branch.name.in_(branch_list))
    
    if dealer:
        # Support multiple comma-separated dealer names
        dealer_list = [d.strip() for d in dealer.split(',') if d.strip()]
        if dealer_list:
            query = query.filter(Dealer.name.in_(dealer_list))
    
    if lender:
        # Support multiple comma-separated lender names
        lender_list = [l.strip() for l in lender.split(',') if l.strip()]
        if lender_list:
            query = query.filter(Lender.name.in_(lender_list))
    
    if status:
        # Support multiple comma-separated status values
        status_list = [s.strip() for s in status.split(',') if s.strip()]
        if status_list:
            query = query.filter(RepaymentStatus.repayment_status.in_(status_list))
    
    if rm_name:
        # Support multiple comma-separated RM names
        rm_list = [r.strip() for r in rm_name.split(',') if r.strip()]
        if rm_list:
            query = query.filter(RM.name.in_(rm_list))
    
    if tl_name:
        # Support multiple comma-separated TL names
        tl_list = [t.strip() for t in tl_name.split(',') if t.strip()]
        if tl_list:
            query = query.filter(CurrentTL.name.in_(tl_list))
    
    # Repayment ID filtering
    if repayment_id:
        # Support multiple comma-separated repayment IDs
        repayment_list = [r.strip() for r in repayment_id.split(',') if r.strip()]
        if repayment_list:
            try:
                repayment_ids = [int(r) for r in repayment_list]
                query = query.filter(PaymentDetails.id.in_(repayment_ids))
            except ValueError:
                # If any value is not a valid integer, skip this filter
                pass
    
    # Demand Number filtering
    if demand_num:
        # Support multiple comma-separated demand numbers
        demand_list = [d.strip() for d in demand_num.split(',') if d.strip()]
        if demand_list:
            try:
                demand_nums = [int(d) for d in demand_list]
                query = query.filter(PaymentDetails.demand_num.in_(demand_nums))
            except ValueError:
                # If any value is not a valid integer, skip this filter
                pass
    
    # PTP date filtering
    if ptp_date_filter:
        # Support multiple comma-separated PTP date filters
        ptp_list = [p.strip() for p in ptp_date_filter.split(',') if p.strip()]
        if ptp_list:
            today = date.today()
            tomorrow = today + timedelta(days=1)
            
            ptp_conditions = []
            for ptp_filter in ptp_list:
                if ptp_filter == "overdue":
                    ptp_conditions.append(PaymentDetails.ptp_date < today)
                elif ptp_filter == "today":
                    ptp_conditions.append(func.date(PaymentDetails.ptp_date) == today)
                elif ptp_filter == "tomorrow":
                    ptp_conditions.append(func.date(PaymentDetails.ptp_date) == tomorrow)
                elif ptp_filter == "future":
                    ptp_conditions.append(PaymentDetails.ptp_date > tomorrow)
                elif ptp_filter == "no_ptp":
                    ptp_conditions.append(PaymentDetails.ptp_date.is_(None))
            
            if ptp_conditions:
                query = query.filter(or_(*ptp_conditions))
    
    # 🎯 ADDED! Alphabetical ordering by Applicant Name (First Name, then Last Name)
    query = query.order_by(ApplicantDetails.first_name.asc(), ApplicantDetails.last_name.asc())
    
    # FIXED: Count payment records instead of loan records
    total = query.with_entities(PaymentDetails.id).count()
    results = []

    for row in query.offset(offset).limit(limit).all():
        # Get comments for this payment (only application details comments, comment_type = 1)
        comments = db.query(Comments).filter(
            and_(
                Comments.repayment_id == row.payment_id,
                Comments.comment_type == 1  # Only application details comments, not paid pending
            )
        ).order_by(Comments.commented_at.desc()).all()
        comment_list = [c.comment for c in comments]

        # Get calling status for ALL 4 contact types (1=applicant, 2=co-applicant, 3=guarantor, 4=reference)
        calling_statuses = {
            "applicant": "Not Called",      # contact_type = 1
            "co_applicant": "Not Called",   # contact_type = 2
            "guarantor": "Not Called",      # contact_type = 3
            "reference": "Not Called"       # contact_type = 4
        }
        
        # Get latest calling records for each contact type for this payment (repayment_id)
        for contact_type in range(1, 5):  # 1 to 4
            latest_calling = db.query(Calling).filter(
                and_(
                    Calling.repayment_id == str(row.payment_id),
                    Calling.Calling_id == 1,  # Only contact calling, not demand calling
                    Calling.contact_type == contact_type
                )
            ).order_by(Calling.created_at.desc()).first()
            
            if latest_calling:
                # Get contact calling status
                contact_status = db.query(ContactCalling).filter(
                    ContactCalling.id == latest_calling.status_id
                ).first()
                if contact_status:
                    # Map contact_type number to string key
                    if contact_type == 1:
                        calling_statuses["applicant"] = contact_status.contact_calling_status
                    elif contact_type == 2:
                        calling_statuses["co_applicant"] = contact_status.contact_calling_status
                    elif contact_type == 3:
                        calling_statuses["guarantor"] = contact_status.contact_calling_status
                    elif contact_type == 4:
                        calling_statuses["reference"] = contact_status.contact_calling_status

        # Get demand calling status for this payment (repayment_id)
        demand_calling_status = None  # Default value
        latest_demand_calling = db.query(Calling).filter(
            and_(
                Calling.repayment_id == str(row.payment_id),
                Calling.Calling_id == 2,  # Demand calling (not contact calling)
                Calling.contact_type == 1  # For applicant only
            )
        ).order_by(Calling.created_at.desc()).first()
        
        if latest_demand_calling:
            # Get demand calling status from demand_calling table (not contact_calling)
            from app.models.demand_calling import DemandCalling
            demand_status = db.query(DemandCalling).filter(
                DemandCalling.id == latest_demand_calling.status_id
            ).first()
            if demand_status:
                demand_calling_status = demand_status.demand_calling_status

        results.append({
            "application_id": str(row.application_id),
            "loan_id": row.loan_id, # Added loan_id to response
            "payment_id": row.payment_id,  # 🎯 ADDED! This is the repayment_id for comments
            "demand_num": str(row.demand_num) if row.demand_num else None,  # 🎯 ADDED! Repayment Number (converted to string)
            "applicant_name": f"{row.first_name or ''} {row.last_name or ''}".strip(),
            "mobile": str(row.mobile) if row.mobile else None,
            "emi_amount": float(row.emi_amount) if row.emi_amount else None,
            "status": row.status,
            "emi_month": row.emi_month.strftime('%b-%y') if row.emi_month else None,
            "branch": row.branch,
            "rm_name": row.rm_name if row.rm_name else None,
            "tl_name": row.tl_name if row.tl_name else None,
            "dealer": row.dealer,
            "lender": row.lender,
            "ptp_date": row.ptp_date.strftime('%y-%m-%d') if row.ptp_date else None,
            "calling_statuses": calling_statuses,  # All 4 contact types calling status
            "demand_calling_status": demand_calling_status,  # 🎯 ADDED! Demand calling status
            "payment_mode": row.payment_mode,      # Payment mode separate
            "amount_collected": float(row.amount_collected) if row.amount_collected else None,  # 🎯 ADDED! Amount collected
            "loan_amount": float(row.loan_amount) if row.loan_amount else None,  # 🎯 ADDED! Loan Amount
            "disbursement_date": row.disbursement_date.strftime('%Y-%m-%d') if row.disbursement_date else None,  # 🎯 ADDED! Disbursement Date
            "house_ownership": row.house_ownership,  # 🎯 ADDED! House Ownership
            "comments": comment_list
        })

    return {
        "total": total,
        "results": results
    }
