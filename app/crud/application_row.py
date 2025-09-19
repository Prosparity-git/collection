from sqlalchemy.orm import Session, aliased, joinedload
from sqlalchemy import desc, func, or_, and_, case
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
from app.models.demand_calling import DemandCalling
from datetime import date, timedelta
from collections import defaultdict

def _combine_address(address_line1, address_line2, address_line3):
    """
    Combine three address lines into a single formatted address string
    """
    address_parts = []
    
    if address_line1 and address_line1.strip():
        address_parts.append(address_line1.strip())
    
    if address_line2 and address_line2.strip():
        address_parts.append(address_line2.strip())
    
    if address_line3 and address_line3.strip():
        address_parts.append(address_line3.strip())
    
    # Join with comma and space, return None if no address parts
    return ', '.join(address_parts) if address_parts else None

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
        LoanDetails.loan_application_id.label("loan_id"),
        PaymentDetails.demand_num.label("demand_num"),
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
        PaymentDetails.amount_collected.label("amount_collected"),
        PaymentDetails.id.label("payment_id"),
        LoanDetails.disbursal_amount.label("loan_amount"),
        LoanDetails.disbursal_date.label("disbursement_date"),
        OwnershipType.ownership_type_name.label("house_ownership"),
        ApplicantDetails.latitude.label("latitude"),
        ApplicantDetails.longitude.label("longitude"),
        ApplicantDetails.address_line1.label("address_line1"),
        ApplicantDetails.address_line2.label("address_line2"),
        ApplicantDetails.address_line3.label("address_line3")
    ]
    
    if emi_month:
        # Direct month filter - much faster than subquery
        query = (
            db.query(*base_fields)
            .select_from(LoanDetails)
            .join(ApplicantDetails, LoanDetails.applicant_id == ApplicantDetails.applicant_id)
            .join(
                PaymentDetails,
                (PaymentDetails.loan_application_id == LoanDetails.loan_application_id) &
                (func.date_format(PaymentDetails.demand_date, '%b-%y') == emi_month)
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
        # Optimized latest payment query using window function instead of subquery
        latest_payment_cte = (
            db.query(
                PaymentDetails.loan_application_id,
                PaymentDetails.id,
                PaymentDetails.demand_date,
                func.row_number().over(
                    partition_by=PaymentDetails.loan_application_id,
                    order_by=PaymentDetails.demand_date.desc()
                ).label('rn')
            )
            .subquery()
        )
        
        query = (
            db.query(*base_fields)
            .select_from(LoanDetails)
            .join(ApplicantDetails, LoanDetails.applicant_id == ApplicantDetails.applicant_id)
            .join(
                latest_payment_cte,
                LoanDetails.loan_application_id == latest_payment_cte.c.loan_application_id
            )
            .join(
                PaymentDetails,
                PaymentDetails.id == latest_payment_cte.c.id
            )
            .join(Branch, ApplicantDetails.branch_id == Branch.id)
            .join(Dealer, ApplicantDetails.dealer_id == Dealer.id)
            .join(Lender, LoanDetails.lenders_id == Lender.id)
            .join(OwnershipType, ApplicantDetails.ownership_type_id == OwnershipType.id)
            .join(RM, LoanDetails.Collection_relationship_manager_id == RM.id)
            .outerjoin(CurrentTL, LoanDetails.current_team_lead_id == CurrentTL.id)
            .join(RepaymentStatus, PaymentDetails.repayment_status_id == RepaymentStatus.id)
            .filter(latest_payment_cte.c.rn == 1)
        )

    # Apply filters efficiently
    if loan_id:
        loan_list = [l.strip() for l in loan_id.split(',') if l.strip()]
        if loan_list:
            try:
                loan_ids = [int(l) for l in loan_list]
                query = query.filter(LoanDetails.loan_application_id.in_(loan_ids))
            except ValueError:
                pass
    
    if search:
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
        branch_list = [b.strip() for b in branch.split(',') if b.strip()]
        if branch_list:
            query = query.filter(Branch.name.in_(branch_list))
    
    if dealer:
        dealer_list = [d.strip() for d in dealer.split(',') if d.strip()]
        if dealer_list:
            query = query.filter(Dealer.name.in_(dealer_list))
    
    if lender:
        lender_list = [l.strip() for l in lender.split(',') if l.strip()]
        if lender_list:
            query = query.filter(Lender.name.in_(lender_list))
    
    if status:
        status_list = [s.strip() for s in status.split(',') if s.strip()]
        if status_list:
            # Handle "Overdue Paid" as a special case
            if "Overdue Paid" in status_list:
                # Remove "Overdue Paid" from the list for regular status filtering
                regular_statuses = [s for s in status_list if s != "Overdue Paid"]
                
                # Create conditions for overdue paid: repayment_status_id = 3 AND payment_date > demand_date
                overdue_paid_condition = and_(
                    PaymentDetails.repayment_status_id == 3,  # Paid status
                    PaymentDetails.payment_date.isnot(None),
                    func.date(PaymentDetails.payment_date) > func.date(PaymentDetails.demand_date)
                )
                
                if regular_statuses:
                    # Combine regular statuses with overdue paid condition
                    query = query.filter(
                        or_(
                            RepaymentStatus.repayment_status.in_(regular_statuses),
                            overdue_paid_condition
                        )
                    )
                else:
                    # Only overdue paid condition
                    query = query.filter(overdue_paid_condition)
            else:
                # Regular status filtering
                query = query.filter(RepaymentStatus.repayment_status.in_(status_list))
    
    if rm_name:
        rm_list = [r.strip() for r in rm_name.split(',') if r.strip()]
        if rm_list:
            query = query.filter(RM.name.in_(rm_list))
    
    if tl_name:
        tl_list = [t.strip() for t in tl_name.split(',') if t.strip()]
        if tl_list:
            query = query.filter(CurrentTL.name.in_(tl_list))
    
    if repayment_id:
        repayment_list = [r.strip() for r in repayment_id.split(',') if r.strip()]
        if repayment_list:
            try:
                repayment_ids = [int(r) for r in repayment_list]
                query = query.filter(PaymentDetails.id.in_(repayment_ids))
            except ValueError:
                pass
    
    if demand_num:
        demand_list = [d.strip() for d in demand_num.split(',') if d.strip()]
        if demand_list:
            try:
                demand_nums = [int(d) for d in demand_list]
                query = query.filter(PaymentDetails.demand_num.in_(demand_nums))
            except ValueError:
                pass
    
    if ptp_date_filter:
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
    
    # Order by applicant name
    query = query.order_by(ApplicantDetails.first_name.asc(), ApplicantDetails.last_name.asc())
    
    # Get total count efficiently
    total = query.with_entities(PaymentDetails.id).count()
    
    # Get paginated results
    rows = query.offset(offset).limit(limit).all()
    
    if not rows:
        return {"total": total, "results": []}
    
    # Extract payment IDs for batch queries
    payment_ids = [str(row.payment_id) for row in rows]
    
    # Batch fetch comments - eliminates N+1 queries
    comments_query = (
        db.query(Comments.repayment_id, Comments.comment)
        .filter(
            and_(
                Comments.repayment_id.in_(payment_ids),
                Comments.comment_type == 1
            )
        )
        .order_by(Comments.repayment_id, Comments.commented_at.desc())
        .all()
    )
    
    # Group comments by repayment_id
    comments_by_payment = defaultdict(list)
    for comment in comments_query:
        comments_by_payment[comment.repayment_id].append(comment.comment)
    
    # Batch fetch calling statuses - eliminates N+1 queries
    calling_query = (
        db.query(
            Calling.repayment_id,
            Calling.contact_type,
            ContactCalling.contact_calling_status
        )
        .join(ContactCalling, Calling.status_id == ContactCalling.id)
        .filter(
            and_(
                Calling.repayment_id.in_(payment_ids),
                Calling.Calling_id == 1,  # Contact calling only
                Calling.contact_type.in_([1, 2, 3, 4])
            )
        )
        .order_by(Calling.repayment_id, Calling.contact_type, Calling.created_at.desc())
        .all()
    )
    
    # Group calling statuses by repayment_id and contact_type
    calling_by_payment = defaultdict(lambda: {
        "applicant": "Not Called",
        "co_applicant": "Not Called", 
        "guarantor": "Not Called",
        "reference": "Not Called"
    })
    
    # Track latest status for each contact type per payment
    seen_combinations = set()
    for calling in calling_query:
        key = (calling.repayment_id, calling.contact_type)
        if key not in seen_combinations:
            seen_combinations.add(key)
            if calling.contact_type == 1:
                calling_by_payment[calling.repayment_id]["applicant"] = calling.contact_calling_status
            elif calling.contact_type == 2:
                calling_by_payment[calling.repayment_id]["co_applicant"] = calling.contact_calling_status
            elif calling.contact_type == 3:
                calling_by_payment[calling.repayment_id]["guarantor"] = calling.contact_calling_status
            elif calling.contact_type == 4:
                calling_by_payment[calling.repayment_id]["reference"] = calling.contact_calling_status
    
    # Batch fetch demand calling statuses
    demand_calling_query = (
        db.query(
            Calling.repayment_id,
            DemandCalling.demand_calling_status
        )
        .join(DemandCalling, Calling.status_id == DemandCalling.id)
        .filter(
            and_(
                Calling.repayment_id.in_(payment_ids),
                Calling.Calling_id == 2,  # Demand calling
                Calling.contact_type == 1
            )
        )
        .order_by(Calling.repayment_id, Calling.created_at.desc())
        .all()
    )
    
    # Group demand calling statuses by repayment_id
    demand_calling_by_payment = {}
    seen_demand = set()
    for demand in demand_calling_query:
        if demand.repayment_id not in seen_demand:
            seen_demand.add(demand.repayment_id)
            demand_calling_by_payment[demand.repayment_id] = demand.demand_calling_status
    
    # Build results efficiently
    results = []
    for row in rows:
        payment_id_str = str(row.payment_id)
        
        results.append({
            "application_id": str(row.application_id),
            "loan_id": row.loan_id,
            "payment_id": row.payment_id,
            "demand_num": str(row.demand_num) if row.demand_num else None,
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
            "calling_statuses": calling_by_payment[payment_id_str],
            "demand_calling_status": demand_calling_by_payment.get(payment_id_str),
            "payment_mode": row.payment_mode,
            "amount_collected": float(row.amount_collected) if row.amount_collected else None,
            "loan_amount": float(row.loan_amount) if row.loan_amount else None,
            "disbursement_date": row.disbursement_date.strftime('%Y-%m-%d') if row.disbursement_date else None,
            "house_ownership": row.house_ownership,
            "latitude": float(row.latitude) if row.latitude else None,
            "longitude": float(row.longitude) if row.longitude else None,
            "address": _combine_address(row.address_line1, row.address_line2, row.address_line3),
            "comments": comments_by_payment[payment_id_str]
        })

    return {
        "total": total,
        "results": results
    }
