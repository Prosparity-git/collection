from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.payment_details import PaymentDetails
from app.models.loan_details import LoanDetails
from app.models.applicant_details import ApplicantDetails
from app.models.user import User
from app.models.branch import Branch
from app.models.dealer import Dealer
from app.models.lenders import Lender
from app.models.co_applicant import CoApplicant
from app.models.guarantor import Guarantor
from app.models.reference import Reference
from app.models.repayment_status import RepaymentStatus
from app.models.comments import Comments
from typing import List, Dict, Any

def get_collection_export_data(db: Session, demand_month: int, demand_year: int) -> List[Dict[str, Any]]:
    """
    Get collection data for export based on demand month and year
    """
    query = text("""
        SELECT 
            ad.applicant_id,
             CONCAT(
             COALESCE(ad.first_name, ''), 
             ' ', 
             COALESCE(ad.middle_name, ''), 
             ' ', 
             COALESCE(ad.last_name, '')
          )  AS full_name,
            crm.name AS collection_rm,
            ctl.name AS collection_tl,
            srm.name as source_rm,
            stl.name as source_tl,
            br.name AS branch,
            dl.name AS dealer,
            l.name AS lender,
            ad.mobile AS borrower_mobile,
            ca.mobile AS co_borrower_mobile,
            g.mobile AS guarantor_mobile,
            r.mobile AS reference_mobile,
            ld.disbursal_date,
            ld.disbursal_amount,
            pd.demand_amount,
            pd.demand_date,
            pd.principal_amount,
            pd.interest,
            pd.demand_num,
            pd.ptp_date AS latest_ptp_date,
            pd.amount_collected,
            rs.repayment_status AS collection_status,
            
             ( SELECT GROUP_CONCAT(
                       CONCAT(
                         DATE_FORMAT(inner_c.created_at, '%d:%b:%Y %h:%i %p'),
                         ' - ',
                         COALESCE(u.name, 'Unknown'),
                         ': ',
                         inner_c.comment
                       )
                       SEPARATOR '\n'
                     )
                FROM (
                   SELECT c.user_id, c.comment, c.created_at
                   FROM comments c
                   WHERE c.repayment_id = pd.id
                   ORDER BY c.id DESC
                   LIMIT 3
                ) AS inner_c
                LEFT JOIN users u ON u.id = inner_c.user_id
              ) AS last_3_comments
        FROM
            payment_details AS pd
                LEFT JOIN
            loan_details AS ld ON ld.loan_application_id = pd.loan_application_id
                LEFT JOIN
            applicant_details AS ad ON ad.applicant_id = ld.applicant_id
                LEFT JOIN
            users AS crm ON crm.id = pd.Collection_relationship_manager_id
                LEFT JOIN
            users AS ctl ON ctl.id = pd.current_team_lead_id
                LEFT JOIN
            users AS srm ON srm.id = ld.source_relationship_manager_id
                LEFT JOIN
            users AS stl ON stl.id = ld.source_team_lead_id
                LEFT JOIN
            branch AS br ON br.id = ad.branch_id
                LEFT JOIN
            dealer AS dl ON dl.id = ad.dealer_id
                LEFT JOIN
            lenders AS l ON l.id = ld.lenders_id
                LEFT JOIN
            co_applicant AS ca ON ca.loan_application_id = ld.loan_application_id
                LEFT JOIN
            guarantor AS g ON g.loan_application_id = ld.loan_application_id
                LEFT JOIN
            reference AS r ON r.loan_application_id = ld.loan_application_id
                LEFT JOIN
            repayment_status AS rs ON rs.id = pd.Repayment_status_id
        WHERE
            demand_month = :demand_month AND demand_year = :demand_year
    """)
    
    result = db.execute(query, {"demand_month": demand_month, "demand_year": demand_year})
    return [dict(row._mapping) for row in result]

