from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.routes import (
    application_row,
    filter_main,
    summary_status,
    user,
    comments,
    status_management,
    paidpending_approval,
    paidpending_applications,
    contacts,
    month_dropdown,
    recent_activity
)

app = FastAPI(title="Prosparity Collection Dashboard API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(user.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(application_row.router, prefix="/api/v1/applications", tags=["Applications"])
app.include_router(filter_main.router, prefix="/api/v1/filters", tags=["Filters"])
app.include_router(summary_status.router, prefix="/api/v1/summary", tags=["Summary"])
app.include_router(comments.router, prefix="/api/v1/comments", tags=["Comments"])
app.include_router(status_management.router, prefix="/api/v1/status-management", tags=["Status Management"])
app.include_router(paidpending_approval.router, prefix="/api/v1/paidpending-approval", tags=["PaidPending Approval"])
app.include_router(paidpending_applications.router, prefix="/api/v1/paidpending-applications", tags=["PaidPending Applications"])
app.include_router(contacts.router, prefix="/api/v1/contacts", tags=["Contacts"])
app.include_router(month_dropdown.router, prefix="/api/v1/month-dropdown", tags=["Month Dropdown"])
app.include_router(recent_activity.router, prefix="/api/v1/recent-activity", tags=["Recent Activity"])

@app.get("/")
def read_root():
    return {"message": "Prosparity Collection Dashboard API is running!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"} 