from sqlalchemy.orm import Session, aliased
from app.models.branch import Branch
from app.models.dealer import Dealer
from app.models.lenders import Lender
from app.models.repayment_status import RepaymentStatus
from app.models.vehicle_status import VehicleStatus
from app.models.payment_details import PaymentDetails
from app.models.user import User
from app.models.loan_details import LoanDetails
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
    # Get distinct TL and RM IDs from loan_details table
    team_lead_ids = [row[0] for row in db.query(LoanDetails.current_team_lead_id.distinct()).filter(LoanDetails.current_team_lead_id != None).all()]
    rm_ids = [row[0] for row in db.query(LoanDetails.Collection_relationship_manager_id.distinct()).filter(LoanDetails.Collection_relationship_manager_id != None).all()]
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
    


