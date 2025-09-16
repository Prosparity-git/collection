from fastapi import APIRouter
from app.api.v1.routes import (
    user, 
    application_row, 
    comments, 
    contacts, 
    filter_main, 
    month_dropdown, 
    paidpending_applications, 
    paidpending_approval, 
    recent_activity, 
    status_management, 
    summary_status,
    field_visit_location,
    export
)

api_router = APIRouter()

api_router.include_router(user.router, prefix="/users", tags=["users"])
api_router.include_router(application_row.router, prefix="/application-row", tags=["application-row"])
api_router.include_router(comments.router, prefix="/comments", tags=["comments"])
api_router.include_router(contacts.router, prefix="/contacts", tags=["contacts"])
api_router.include_router(filter_main.router, prefix="/filter-main", tags=["filter-main"])
api_router.include_router(month_dropdown.router, prefix="/month-dropdown", tags=["month-dropdown"])
api_router.include_router(paidpending_applications.router, prefix="/paidpending-applications", tags=["paidpending-applications"])
api_router.include_router(paidpending_approval.router, prefix="/paidpending-approval", tags=["paidpending-approval"])
api_router.include_router(recent_activity.router, prefix="/recent-activity", tags=["recent-activity"])
api_router.include_router(status_management.router, prefix="/status-management", tags=["status-management"])
api_router.include_router(summary_status.router, prefix="/summary-status", tags=["summary-status"])
api_router.include_router(field_visit_location.router, prefix="/field-visit-location", tags=["field-visit-location"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
