from sqlalchemy.orm import Session
from sqlalchemy import func, and_, cast, Numeric
from datetime import date
from typing import Dict, List, Optional
from app.models.activity_log import ActivityLog
from app.models.field_types import FieldTypes


def calculate_current_overdue_batch(
    db: Session,
    loan_ids: List[int],
    current_month: Optional[date] = None
) -> Dict[int, Optional[float]]:
    """
    Batch calculate current overdue amount for multiple loans (optimized to avoid N+1 queries).
    
    Formula for each loan:
    x = (sum of new_values) - (sum of previous_values) from activity_log
        where field_type = 'amount_collected' 
        and created_at >= 7th of current month
        and loan_application_id = loan_id
    
    current_overdue = total_overdue_amount (from LMS) - x
    
    Args:
        db: Database session
        loan_ids: List of loan application IDs
        current_month: Current month date (defaults to today)
    
    Returns:
        Dictionary mapping loan_id -> current_overdue_amount (or None if loan not found/invalid)
    """
    if not loan_ids:
        return {}
    
    # Determine the 7th of current month
    if current_month is None:
        current_month = date.today()
    
    # Calculate the 7th of current month
    seventh_of_month = date(current_month.year, current_month.month, 6)
    
    # Get field_type_id for 'amount_collected' (single query)
    amount_field_type = db.query(FieldTypes).filter(
        FieldTypes.field_name == 'amount_collected'
    ).first()
    
    if not amount_field_type:
        # If field_type doesn't exist, return empty dict (will use total_overdue_amount as is)
        return {}
    
    # Single optimized query to get sums for all loans at once
    # Group by loan_application_id and calculate sums
    activity_sums = (
        db.query(
            ActivityLog.loan_application_id,
            func.sum(
                func.cast(ActivityLog.new_value, Numeric(12, 2))
            ).label('sum_new_values'),
            func.sum(
                func.cast(ActivityLog.previous_value, Numeric(12, 2))
            ).label('sum_previous_values')
        )
        .filter(
            and_(
                ActivityLog.loan_application_id.in_(loan_ids),
                ActivityLog.field_type_id == amount_field_type.id,
                func.date(ActivityLog.created_at) >= seventh_of_month
            )
        )
        .group_by(ActivityLog.loan_application_id)
        .all()
    )
    
    # Create a dictionary for quick lookup: loan_id -> (sum_new, sum_previous)
    activity_dict = {}
    for loan_id, sum_new, sum_previous in activity_sums:
        sum_new_float = float(sum_new) if sum_new else 0.0
        sum_previous_float = float(sum_previous) if sum_previous else 0.0
        activity_dict[loan_id] = (sum_new_float, sum_previous_float)
    
    # Get total_overdue_amount for all loans in one query
    from app.models.loan_details import LoanDetails
    loans = (
        db.query(
            LoanDetails.loan_application_id,
            LoanDetails.total_overdue_amount
        )
        .filter(LoanDetails.loan_application_id.in_(loan_ids))
        .all()
    )
    
    # Build result dictionary
    result = {}
    for loan_id, total_overdue in loans:
        if total_overdue is None:
            result[loan_id] = None
            continue
        
        # Get activity sums for this loan (default to 0 if no activity)
        sum_new, sum_previous = activity_dict.get(loan_id, (0.0, 0.0))
        
        # Calculate x
        x = sum_new - sum_previous
        
        # Calculate current_overdue
        total_overdue_float = float(total_overdue)
        current_overdue = total_overdue_float - x
        
        # Ensure current_overdue is not negative
        result[loan_id] = max(0.0, current_overdue)
    
    # Handle loans that weren't found in the query (shouldn't happen, but safety check)
    for loan_id in loan_ids:
        if loan_id not in result:
            result[loan_id] = None
    
    return result

