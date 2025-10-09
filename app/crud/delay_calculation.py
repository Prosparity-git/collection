from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from app.models.payment_details import PaymentDetails
from datetime import date


def get_delay_calculations_for_loan(db: Session, loan_id: int):
    """
    Calculate delay days for repayments of a loan up to current month only.
    
    Logic:
    - Only includes EMIs up to current month (not future months)
    - If payment_date exists: delay_days = payment_date - demand_date
    - If payment_date is NULL: delay_days = current_date - demand_date
    """

    if not loan_id:
        return {
            "loan_id": loan_id,
            "total_repayments": 0,
            "results": []
        }

    today = date.today()
    current_month = today.month
    current_year = today.year

    # Get payment details for this loan up to current month only
    # Filter using demand_month and demand_year OR demand_date
    payments = (
        db.query(
            PaymentDetails.id.label("payment_id"),
            PaymentDetails.loan_application_id.label("loan_id"),
            PaymentDetails.demand_num,
            PaymentDetails.demand_date,
            PaymentDetails.payment_date,
            PaymentDetails.demand_month,
            PaymentDetails.demand_year,
            PaymentDetails.demand_amount,
            PaymentDetails.amount_collected
        )
        .filter(
            PaymentDetails.loan_application_id == loan_id,
            or_(
                # Filter by demand_month/demand_year if available
                and_(
                    PaymentDetails.demand_year.isnot(None),
                    PaymentDetails.demand_month.isnot(None),
                    or_(
                        PaymentDetails.demand_year < current_year,
                        and_(
                            PaymentDetails.demand_year == current_year,
                            PaymentDetails.demand_month <= current_month
                        )
                    )
                ),
                # Fallback: filter by demand_date if month/year not available
                and_(
                    or_(
                        PaymentDetails.demand_year.is_(None),
                        PaymentDetails.demand_month.is_(None)
                    ),
                    PaymentDetails.demand_date.isnot(None),
                    or_(
                        func.year(PaymentDetails.demand_date) < current_year,
                        and_(
                            func.year(PaymentDetails.demand_date) == current_year,
                            func.month(PaymentDetails.demand_date) <= current_month
                        )
                    )
                )
            )
        )
        .order_by(PaymentDetails.demand_num.asc())
        .all()
    )


    results = []

    for payment in payments:
        delay_days = None

        if payment.demand_date:
            if payment.payment_date:
                # Case 1: Payment exists - calculate payment_date - demand_date
                delay_days = (payment.payment_date - payment.demand_date).days
            else:
                # Case 2: No payment yet - calculate current_date - demand_date
                delay_days = (today - payment.demand_date).days

        # Calculate overdue_amount: max(0, demand_amount - amount_collected)
        # If amount_collected > demand_amount, show 0
        overdue_amount = None
        if payment.demand_amount is not None and payment.amount_collected is not None:
            overdue_amount = max(0, float(payment.demand_amount) - float(payment.amount_collected))
        elif payment.demand_amount is not None:
            # If no collection yet, full demand amount is overdue
            overdue_amount = float(payment.demand_amount)

        results.append({
            "payment_id": payment.payment_id,
            "loan_id": payment.loan_id,
            "demand_num": payment.demand_num,
            "demand_date": payment.demand_date.strftime('%Y-%m-%d') if payment.demand_date else None,
            "payment_date": payment.payment_date.strftime('%Y-%m-%d') if payment.payment_date else None,
            "delay_days": delay_days,
            "overdue_amount": overdue_amount
        })

    return {
        "loan_id": loan_id,
        "total_repayments": len(results),
        "results": results
    }