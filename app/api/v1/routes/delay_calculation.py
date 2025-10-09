from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session 
from app.core.deps import get_db, get_current_user
from app.schemas.delay_calculation import DelayCalculationResponse
from app.crud.delay_calculation import get_delay_calculations_for_loan

router = APIRouter()

@router.get("/{loan_id}", response_model=DelayCalculationResponse)
def calculate_delays_for_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Calculate delay days for repayments of a given loan up to current month.
    
    Returns a table of delays for EMIs/repayments up to current month only (excludes future months):
    - demand_num: EMI number (1, 2, 3, etc.)
    - delay_days calculation:
      * If payment exists: delay_days = payment_date - demand_date (negative = paid early, positive = paid late)
      * If no payment yet: delay_days = current_date - demand_date (current overdue days)
      * If no demand date: delay_days = None
    
    Note: Only returns EMIs up to and including the current month. Future month EMIs are excluded.
    
    Example Response:
    ```json
    {
      "loan_id": 200,
      "total_repayments": 10,
      "results": [
        {
          "payment_id": 123, 
          "demand_num": 1, 
          "demand_date": "2025-01-05", 
          "payment_date": "2025-01-10", 
          "delay_days": 5,
          "overdue_amount": 500.00
        },
        {
          "payment_id": 124, 
          "demand_num": 2, 
          "demand_date": "2025-02-05", 
          "payment_date": null, 
          "delay_days": 245,
          "overdue_amount": 5000.00
        },
        {
          "payment_id": 125, 
          "demand_num": 3, 
          "demand_date": "2025-09-05", 
          "payment_date": null, 
          "delay_days": 32,
          "overdue_amount": 0.00
        }
      ]
    }
    ```
    """
    return get_delay_calculations_for_loan(db=db, loan_id=loan_id)