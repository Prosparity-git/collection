from sqlalchemy.orm import Session, aliased
from sqlalchemy import distinct, select
from app.models.branch import Branch
from app.models.dealer import Dealer
from app.models.lenders import Lender
from app.models.repayment_status import RepaymentStatus
from app.models.vehicle_status import VehicleStatus
from app.models.payment_details import PaymentDetails
from app.models.user import User
from app.models.loan_details import LoanDetails
from app.models.applicant_details import ApplicantDetails
from app.models.dpd_monthly_snapshot import DpdMonthlySnapshot
from datetime import date, timedelta



def filter_options(db: Session):
    today = date.today()
    tomorrow = today + timedelta(days=1)


    emi_months = sorted(list(set([
    row[0].strftime("%Y-%m") 
    for row in db.query(PaymentDetails.demand_date.distinct()).all() 
    if row[0]
])))
    
    # FIXED: Use ptp_date for PTP filtering, not payment_date
    raw_dates = [
        row[0] for row in db.query(PaymentDetails.ptp_date)
        .filter(PaymentDetails.ptp_date != None)
        .all()
    ]
    
    ptp_categories = {
        "Overdue PTP": 0,
        "Today's PTP": 0,
        "Tomorrow's PTP": 0,
        "Future PTP": 0,
        "No PTP": 0
    }

    # FIXED: Calculate PTP categories based on ptp_date
    for ptp_date in raw_dates:
        if hasattr(ptp_date, 'date'):
            ptp_date = ptp_date.date()
        if ptp_date < today:
            ptp_categories["Overdue PTP"] += 1
        elif ptp_date == today:
            ptp_categories["Today's PTP"] += 1
        elif ptp_date == tomorrow:
            ptp_categories["Tomorrow's PTP"] += 1
        elif ptp_date > tomorrow:
            ptp_categories["Future PTP"] += 1

    # FIXED: Count records with no PTP date (ptp_date is NULL)
    no_ptp_count = db.query(PaymentDetails).filter(PaymentDetails.ptp_date.is_(None)).count()
    ptp_categories["No PTP"] = no_ptp_count

    



    branches =  [b.name for b in db.query(Branch).all()]
    dealers = [d.name for d in db.query(Dealer).all()]
    lenders = [l.name for l in db.query(Lender).all()]
    statuses = [r.repayment_status for r in db.query(RepaymentStatus).all()]
    statuses.append("Overdue Paid")
    vehicle_statuses = [v.vehicle_status for v in db.query(VehicleStatus).all()]
    # Get distinct TL and RM IDs from payment_details table
    team_lead_ids = [row[0] for row in db.query(PaymentDetails.current_team_lead_id.distinct()).filter(PaymentDetails.current_team_lead_id != None).all()]
    rm_ids = [row[0] for row in db.query(PaymentDetails.Collection_relationship_manager_id.distinct()).filter(PaymentDetails.Collection_relationship_manager_id != None).all()]
    source_rms_ids = [row[0] for row in db.query(LoanDetails.source_relationship_manager_id.distinct()).filter(LoanDetails.source_relationship_manager_id != None).all()]
    source_team_leads_ids = [row[0] for row in db.query(LoanDetails.source_team_lead_id.distinct()).filter(LoanDetails.source_team_lead_id != None).all()]
    # Get names from users table based on the IDs
    team_leads = [u.name for u in db.query(User).filter(User.id.in_(team_lead_ids))]
    rms = [u.name for u in db.query(User).filter(User.id.in_(rm_ids))]
    source_rms = [u.name for u in db.query(User).filter(User.id.in_(source_rms_ids))]
    source_team_leads = [u.name for u in db.query(User).filter(User.id.in_(source_team_leads_ids))]
    demand_num = [str(row[0]) for row in db.query(PaymentDetails.demand_num.distinct()).filter(PaymentDetails.demand_num != None).all()]  # 🎯 ADDED! Unique demand numbers
    dpd_buckets = [row[0] for row in db.query(DpdMonthlySnapshot.dpd_bucket_name.distinct()).filter(DpdMonthlySnapshot.dpd_bucket_name != None).all()]  # 🎯 ADDED! Distinct DPD bucket names

    return {
        "emi_months": emi_months,
        "branches": branches,
        "dealers": dealers,
        "lenders": lenders,
        "statuses": statuses,
        # FIXED: Return PTP filter values that match API expectations
        "ptpDateOptions": ["overdue", "today", "tomorrow", "future", "no_ptp"], 
        "vehicle_statuses": vehicle_statuses,
        "team_leads": team_leads,
        "rms": rms,
        "source_rms": source_rms,
        "source_team_leads": source_team_leads,
        "demand_num": demand_num,  # 🎯 ADDED! Demand numbers for filtering
        "dpd_buckets": dpd_buckets,  # 🎯 ADDED! DPD buckets for filtering
    }


def cascading_options(
    db: Session, 
    branch_ids: list = None, 
    dealer_ids: list = None,
    lender_ids: list = None,
    tl_ids: list = None, 
    rm_ids: list = None,
    source_tl_ids: list = None,
    source_rm_ids: list = None
):
    """
    Get cascading filter options for Branch, Dealer, Lender, Current Team Lead, Current RM,
    Source Team Lead, and Source RM (from loan_details).
    All fields are dependent on each other through cascading logic.
    Uses payment_details table with JOINs to loan_details and applicant_details.
    Optimized with DISTINCT queries and proper joins to avoid N+1.
    Supports multiple values for all filter parameters (lists).
    """
    # Base query: payment_details -> loan_details -> applicant_details -> branch & dealer
    # Using aliases for cleaner joins
    pd = aliased(PaymentDetails)
    ld = aliased(LoanDetails)
    ad = aliased(ApplicantDetails)
    
    # Build the base query with joins - includes all fields we need
    base_query = db.query(
        pd.current_team_lead_id.label('current_tl_id'),
        pd.Collection_relationship_manager_id.label('current_rm_id'),
        ld.source_team_lead_id.label('source_tl_id'),
        ld.source_relationship_manager_id.label('source_rm_id'),
        ld.lenders_id.label('lender_id'),
        ad.branch_id.label('branch_id'),
        ad.dealer_id.label('dealer_id')
    ).join(
        ld, pd.loan_application_id == ld.loan_application_id
    ).join(
        ad, ld.applicant_id == ad.applicant_id
    )
    
    # Apply filters based on selected options (affects all cascading)
    # Support both single values and lists using IN clause
    if branch_ids:
        base_query = base_query.filter(ad.branch_id.in_(branch_ids))
    if dealer_ids:
        base_query = base_query.filter(ad.dealer_id.in_(dealer_ids))
    if lender_ids:
        base_query = base_query.filter(ld.lenders_id.in_(lender_ids))
    if tl_ids:
        base_query = base_query.filter(pd.current_team_lead_id.in_(tl_ids))
    if rm_ids:
        base_query = base_query.filter(pd.Collection_relationship_manager_id.in_(rm_ids))
    if source_tl_ids:
        base_query = base_query.filter(ld.source_team_lead_id.in_(source_tl_ids))
    if source_rm_ids:
        base_query = base_query.filter(ld.source_relationship_manager_id.in_(source_rm_ids))
    
    # Get all distinct combinations (one query for everything)
    all_results = base_query.filter(
        ad.branch_id.isnot(None)
    ).distinct().all()
    
    # Extract unique IDs using sets for O(1) lookups
    branch_ids = set()
    dealer_ids = set()
    lender_ids = set()
    current_tl_ids = set()
    current_rm_ids = set()
    source_tl_ids = set()
    source_rm_ids = set()
    
    for row in all_results:
        if row.branch_id:
            branch_ids.add(row.branch_id)
        if row.dealer_id:
            dealer_ids.add(row.dealer_id)
        if row.lender_id:
            lender_ids.add(row.lender_id)
        if row.current_tl_id:
            current_tl_ids.add(row.current_tl_id)
        if row.current_rm_id:
            current_rm_ids.add(row.current_rm_id)
        if row.source_tl_id:
            source_tl_ids.add(row.source_tl_id)
        if row.source_rm_id:
            source_rm_ids.add(row.source_rm_id)
    
    # Batch fetch branch details (1 query instead of N)
    branches = []
    if branch_ids:
        branches_query = db.query(Branch.id, Branch.name).filter(Branch.id.in_(branch_ids)).all()
        branches = [{"id": bid, "name": name} for bid, name in branches_query]
    
    # Batch fetch dealer details (1 query instead of N)
    dealers = []
    if dealer_ids:
        dealer_query = db.query(Dealer.id, Dealer.name).filter(Dealer.id.in_(dealer_ids)).all()
        dealers = [{"id": did, "name": name} for did, name in dealer_query]
    
    # Batch fetch lender details (1 query instead of N)
    lenders = []
    if lender_ids:
        lender_query = db.query(Lender.id, Lender.name).filter(Lender.id.in_(lender_ids)).all()
        lenders = [{"id": lid, "name": name} for lid, name in lender_query]
    
    # Batch fetch current team lead details (1 query instead of N)
    team_leads = []
    if current_tl_ids:
        tl_query = db.query(User.id, User.name).filter(User.id.in_(current_tl_ids)).all()
        team_leads = [{"id": uid, "name": name} for uid, name in tl_query]
    
    # Batch fetch current RM details (1 query instead of N)
    rms = []
    if current_rm_ids:
        rm_query = db.query(User.id, User.name).filter(User.id.in_(current_rm_ids)).all()
        rms = [{"id": uid, "name": name} for uid, name in rm_query]
    
    # Batch fetch source team lead details (1 query instead of N)
    source_team_leads = []
    if source_tl_ids:
        source_tl_query = db.query(User.id, User.name).filter(User.id.in_(source_tl_ids)).all()
        source_team_leads = [{"id": uid, "name": name} for uid, name in source_tl_query]
    
    # Batch fetch source RM details (1 query instead of N)
    source_rms = []
    if source_rm_ids:
        source_rm_query = db.query(User.id, User.name).filter(User.id.in_(source_rm_ids)).all()
        source_rms = [{"id": uid, "name": name} for uid, name in source_rm_query]
    
    return {
        "branches": branches,
        "dealers": dealers,
        "lenders": lenders,
        "team_leads": team_leads,
        "rms": rms,
        "source_team_leads": source_team_leads,
        "source_rms": source_rms
    }

