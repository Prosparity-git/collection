from sqlalchemy.orm import Session, aliased, joinedload
from sqlalchemy import desc, func, or_, and_, case, outerjoin
from app.models.loan_details import LoanDetails
from app.models.applicant_details import ApplicantDetails
from app.models.payment_details import PaymentDetails
from app.models.branch import Branch
from app.models.dealer import Dealer
from app.models.lenders import Lender
from app.models.user import User
from app.models.repayment_status import RepaymentStatus
from app.models.calling import Calling
from app.models.ownership_type import OwnershipType  # 🎯 ADDED! For House Ownership
from app.models.demand_calling import DemandCalling
from app.models.vehicle_repossession_status import VehicleRepossessionStatus  # 🎯 ADDED! For vehicle repossession
from app.models.vehicle_status import VehicleStatus  # 🎯 ADDED! For vehicle status
from app.models.dpd_monthly_snapshot import DpdMonthlySnapshot  # 🎯 ADDED! For DPD bucket
from app.models.nach_status import NachStatus  # 🎯 ADDED! For NACH status
from app.crud.overdue_calculation import calculate_current_overdue_batch  # 🎯 ADDED! For batch overdue calculation
from datetime import date, timedelta, datetime
from collections import defaultdict
import calendar

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

def _emi_month_to_date_range(emi_month: str):
    """
    Convert emi_month string (e.g., 'oct-25') to date range tuple (start_date, end_date).
    This allows using direct date comparisons instead of date_format function for better index usage.
    """
    try:
        # Parse format like 'oct-25' or 'Oct-25'
        parts = emi_month.lower().split('-')
        if len(parts) != 2:
            return None, None
        
        month_str = parts[0].strip()
        year_str = parts[1].strip()
        
        # Convert month name to number
        month_map = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        
        month = month_map.get(month_str)
        if not month:
            return None, None
        
        # Convert year (assume 20xx for 2-digit years)
        if len(year_str) == 2:
            year = 2000 + int(year_str)
        else:
            year = int(year_str)
        
        # Get first and last day of month
        start_date = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_date = date(year, month, last_day)
        
        return start_date, end_date
    except (ValueError, AttributeError):
        return None, None

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
    source_rm_name: str = "",
    source_tl_name: str = "",
    ptp_date_filter: str = "",
    repayment_id: str = "",  # 🎯 ADDED! Filter by repayment_id (same as payment_id)
    demand_num: str = "",  # 🎯 ADDED! Filter by demand number
    current_dpd_bucket: str = "",  # 🎯 ADDED! Filter by current DPD bucket
    offset: int = 0, 
    limit: int = 20
):
    RM = aliased(User)
    CurrentTL = aliased(User)
    SourceRM = aliased(User)
    SourceTL = aliased(User)

    # Create subquery for latest DPD bucket for each loan_application_id (only if needed)
    # Only create if current_dpd_bucket filter is used or if we need the field
    latest_dpd_subquery = None
    if current_dpd_bucket or True:  # Always needed for base_fields
        latest_dpd_subquery = (
            db.query(
                DpdMonthlySnapshot.loan_application_id,
                DpdMonthlySnapshot.dpd_bucket_name,
                func.row_number().over(
                    partition_by=DpdMonthlySnapshot.loan_application_id,
                    order_by=DpdMonthlySnapshot.id.desc()
                ).label('rn')
            )
            .subquery()
        )

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
        SourceRM.name.label("source_rm_name"),
        SourceTL.name.label("source_tl_name"),
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
        ApplicantDetails.address_line3.label("address_line3"),
        VehicleStatus.vehicle_status.label("vehicle_status_name"),
        VehicleRepossessionStatus.repossession_date.label("repossession_date"),
        VehicleRepossessionStatus.repossession_sale_date.label("repossession_sale_date"),
        VehicleRepossessionStatus.repossession_sale_amount.label("repossession_sale_amount"),
        latest_dpd_subquery.c.dpd_bucket_name.label("current_dpd_bucket"),
        LoanDetails.total_overdue_amount.label("total_overdue_amount"),  # 🎯 ADDED! Total overdue amount from LMS
        LoanDetails.total_pos.label("total_pos"),  # 🎯 ADDED! Total POS amount
        PaymentDetails.payment_information.label("payment_information")  # 🎯 OPTIMIZED! Store ID for batch lookup
    ]
    
    if emi_month:
        # Convert emi_month to date range for index-friendly query
        start_date, end_date = _emi_month_to_date_range(emi_month)
        
        # Build join condition with date range filter (allows index usage)
        payment_join_condition = (
            PaymentDetails.loan_application_id == LoanDetails.loan_application_id
        )
        if start_date and end_date:
            payment_join_condition = payment_join_condition & (
                PaymentDetails.demand_date >= start_date
            ) & (
                PaymentDetails.demand_date <= end_date
            )
        
        # Direct month filter using date range - much faster with indexes
        query = (
            db.query(*base_fields)
            .select_from(LoanDetails)
            .join(ApplicantDetails, LoanDetails.applicant_id == ApplicantDetails.applicant_id)
            .join(PaymentDetails, payment_join_condition)
            .join(Branch, ApplicantDetails.branch_id == Branch.id)
            .join(Dealer, ApplicantDetails.dealer_id == Dealer.id)
            .join(Lender, LoanDetails.lenders_id == Lender.id)
            .join(OwnershipType, ApplicantDetails.ownership_type_id == OwnershipType.id)
            .join(RM, PaymentDetails.Collection_relationship_manager_id == RM.id)
            .outerjoin(CurrentTL, PaymentDetails.current_team_lead_id == CurrentTL.id)
            .outerjoin(SourceRM, LoanDetails.source_relationship_manager_id == SourceRM.id)
            .outerjoin(SourceTL, LoanDetails.source_team_lead_id == SourceTL.id)
            .join(RepaymentStatus, PaymentDetails.repayment_status_id == RepaymentStatus.id)
            .outerjoin(VehicleRepossessionStatus, VehicleRepossessionStatus.loan_application_id == LoanDetails.loan_application_id)
            .outerjoin(VehicleStatus, VehicleRepossessionStatus.vehicle_status == VehicleStatus.id)
            .outerjoin(
                latest_dpd_subquery,
                and_(
                    latest_dpd_subquery.c.loan_application_id == LoanDetails.loan_application_id,
                    latest_dpd_subquery.c.rn == 1
                )
            )
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
            .join(RM, PaymentDetails.Collection_relationship_manager_id == RM.id)
            .outerjoin(CurrentTL, PaymentDetails.current_team_lead_id == CurrentTL.id)
            .outerjoin(SourceRM, LoanDetails.source_relationship_manager_id == SourceRM.id)
            .outerjoin(SourceTL, LoanDetails.source_team_lead_id == SourceTL.id)
            .join(RepaymentStatus, PaymentDetails.repayment_status_id == RepaymentStatus.id)
            .outerjoin(VehicleRepossessionStatus, VehicleRepossessionStatus.loan_application_id == LoanDetails.loan_application_id)
            .outerjoin(VehicleStatus, VehicleRepossessionStatus.vehicle_status == VehicleStatus.id)
            .outerjoin(
                latest_dpd_subquery,
                and_(
                    latest_dpd_subquery.c.loan_application_id == LoanDetails.loan_application_id,
                    latest_dpd_subquery.c.rn == 1
                )
            )
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
     
    if source_rm_name:
        source_rm_list = [s.strip() for s in source_rm_name.split(',') if s.strip()]
        if source_rm_list:
            query = query.filter(SourceRM.name.in_(source_rm_list))
    
    if source_tl_name:
        source_tl_list = [s.strip() for s in source_tl_name.split(',') if s.strip()]
        if source_tl_list:
            query = query.filter(SourceTL.name.in_(source_tl_list))



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
    
    if current_dpd_bucket:
        dpd_list = [d.strip() for d in current_dpd_bucket.split(',') if d.strip()]
        if dpd_list:
            query = query.filter(latest_dpd_subquery.c.dpd_bucket_name.in_(dpd_list))
    
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
    
    # Get total count efficiently - count before ordering (faster)
    # Create a count query without ordering to optimize performance
    count_query = query.with_entities(PaymentDetails.id).distinct()
    total = count_query.count()
    
    # Order by applicant name (only for results, not for count)
    query = query.order_by(ApplicantDetails.first_name.asc(), ApplicantDetails.last_name.asc())
    
    # Get paginated results
    rows = query.offset(offset).limit(limit).all()
    
    if not rows:
        return {"total": total, "results": []}
    
    # Extract payment IDs for batch queries (keep as integers for better index usage)
    payment_ids = [row.payment_id for row in rows]
    payment_ids_str = [str(pid) for pid in payment_ids]  # For dictionary lookup
    
    # Batch fetch demand calling statuses (use integer IDs for better index usage)
    demand_calling_query = (
        db.query(
            Calling.repayment_id,
            DemandCalling.demand_calling_status
        )
        .join(DemandCalling, Calling.status_id == DemandCalling.id)
        .filter(
            and_(
                Calling.repayment_id.in_(payment_ids),  # Use integer IDs
                Calling.Calling_id == 2,  # Demand calling
                Calling.contact_type == 1
            )
        )
        .order_by(Calling.repayment_id, Calling.created_at.desc())
        .all()
    )
    
    # Group demand calling statuses by repayment_id (use string keys for lookup)
    demand_calling_by_payment = {}
    seen_demand = set()
    for demand in demand_calling_query:
        repayment_id_str = str(demand.repayment_id)
        if repayment_id_str not in seen_demand:
            seen_demand.add(repayment_id_str)
            demand_calling_by_payment[repayment_id_str] = demand.demand_calling_status
    
    # 🎯 OPTIMIZED! Batch fetch NACH status data only for IDs 2 and 3 (skip 1 - cleared status)
    nach_ids = list(set([row.payment_information for row in rows if row.payment_information is not None and row.payment_information != 1]))
    nach_status_by_id = {}
    if nach_ids:
        nach_status_query = (
            db.query(
                NachStatus.id,
                NachStatus.nach_reason
            )
            .filter(NachStatus.id.in_(nach_ids))
            .all()
        )
        for nach in nach_status_query:
            nach_status_by_id[nach.id] = {
                "nach_reason": nach.nach_reason
            }
    
    # 🎯 OPTIMIZED! Batch calculate current_overdue_amount for all loans (avoids N+1 queries)
    unique_loan_ids = list(set([row.loan_id for row in rows]))
    current_overdue_by_loan = calculate_current_overdue_batch(db, unique_loan_ids)
    
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
            "source_rm_name": row.source_rm_name if row.source_rm_name else None,
            "source_tl_name": row.source_tl_name if row.source_tl_name else None,
            "dealer": row.dealer,
            "lender": row.lender,
            "ptp_date": row.ptp_date.strftime('%y-%m-%d') if row.ptp_date else None,
            "demand_calling_status": demand_calling_by_payment.get(payment_id_str),
            "payment_mode": row.payment_mode,
            "amount_collected": float(row.amount_collected) if row.amount_collected else None,
            "loan_amount": float(row.loan_amount) if row.loan_amount else None,
            "disbursement_date": row.disbursement_date.strftime('%Y-%m-%d') if row.disbursement_date else None,
            "house_ownership": row.house_ownership,
            "latitude": float(row.latitude) if row.latitude else None,
            "longitude": float(row.longitude) if row.longitude else None,
            "address": _combine_address(row.address_line1, row.address_line2, row.address_line3),
            "vehicle_status_name": row.vehicle_status_name.value if row.vehicle_status_name else None,
            "repossession_date": row.repossession_date.strftime('%Y-%m-%d') if row.repossession_date else None,
            "repossession_sale_date": row.repossession_sale_date.strftime('%Y-%m-%d') if row.repossession_sale_date else None,
            "repossession_sale_amount": float(row.repossession_sale_amount) if row.repossession_sale_amount else None,
            "current_dpd_bucket": row.current_dpd_bucket,
            "total_overdue_amount": float(row.total_overdue_amount) if row.total_overdue_amount is not None else None,  # 🎯 ADDED! Total overdue from LMS
            "total_pos": float(row.total_pos) if row.total_pos is not None else None,  # 🎯 ADDED! Total POS amount
            "current_overdue_amount": current_overdue_by_loan.get(row.loan_id),  # 🎯 ADDED! Calculated current overdue
            "nach_status": "1" if row.payment_information == 1 else (str(row.payment_information) if row.payment_information else None),  # 🎯 "1" for cleared, id for others
            "reason": nach_status_by_id.get(row.payment_information, {}).get("nach_reason") if row.payment_information and row.payment_information != 1 else None  # 🎯 Only send reason if id is not 1
        })

    return {
        "total": total,
        "results": results
    }
