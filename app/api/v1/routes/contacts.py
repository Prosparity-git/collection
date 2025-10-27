from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.models.co_applicant import CoApplicant
from app.models.guarantor import Guarantor
from app.models.reference import Reference
from app.models.applicant_details import ApplicantDetails
from app.models.loan_details import LoanDetails
from app.models.relationship import Relationship
from typing import Dict, Any

router = APIRouter()

@router.get("/{loan_id}")
def get_application_contacts(
    loan_id: str = Path(..., description="The loan ID to get contacts for"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all contacts (applicant, co-applicants, guarantors, references) for an application"""
    try:
        # Convert loan_id to integer
        try:
            loan_id_int = int(loan_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid loan_id: {loan_id}. Must be a valid integer.")
        
        # Get main applicant details
        applicant = db.query(ApplicantDetails).join(
            LoanDetails, ApplicantDetails.applicant_id == LoanDetails.applicant_id
        ).filter(
            LoanDetails.loan_application_id == loan_id_int
        ).first()
        
        if not applicant:
            raise HTTPException(
                status_code=404, 
                detail=f"Applicant not found for loan_id: {loan_id_int}"
            )
        
        # Get co-applicants - these definitely exist in the database
        co_applicants = db.query(CoApplicant).filter(
            CoApplicant.loan_application_id == loan_id_int
        ).all()
        
        # Get guarantors - these definitely exist in the database
        guarantors = db.query(Guarantor).filter(
            Guarantor.loan_application_id == loan_id_int
        ).all()
        
        # Get references - now using the correct Reference model
        references = db.query(Reference).filter(
            Reference.loan_application_id == loan_id_int
        ).all()
        
        # Helper function to extract contact info based on actual database structure
        def extract_contact_info(contact, contact_type):
            try:
                # Based on DDL, we have first_name, middle_name, last_name, mobile
                name_parts = []
                
                if hasattr(contact, 'first_name') and contact.first_name:
                    name_parts.append(contact.first_name)
                if hasattr(contact, 'middle_name') and contact.middle_name:
                    name_parts.append(contact.middle_name)
                if hasattr(contact, 'last_name') and contact.last_name:
                    name_parts.append(contact.last_name)
                
                name = " ".join(name_parts) if name_parts else "Unknown Name"
                
                # Get mobile (this is the correct column name from DDL)
                mobile = getattr(contact, 'mobile', None)
                
                # Try to get email from different possible columns
                email = None
                for email_col in ['email', 'email_id']:
                    if hasattr(contact, email_col):
                        email_val = getattr(contact, email_col)
                        if email_val:
                            email = email_val
                            break
                
                # Get relationship name for co_applicant
                relationship = None
                if contact_type == "co_applicant":
                    rel_id = getattr(contact, 'relationship_with_applicant', None)
                    if rel_id:
                        rel_obj = db.query(Relationship).filter(
                            Relationship.id == rel_id
                        ).first()
                        if rel_obj:
                            relationship = rel_obj.relationship_name
                
                return {
                    "id": getattr(contact, 'id', None),
                    "name": name,
                    "phone": mobile,  # Use mobile from DDL
                    "email": email,
                    "type": contact_type,
                    "relationship": relationship
                }
            except Exception as e:
                print(f"Error extracting contact info for {contact_type}: {e}")
                return {
                    "id": None,
                    "name": "Unknown",
                    "phone": None,
                    "email": None,
                    "type": contact_type,
                    "relationship": None
                }
        
        # Build response with actual data
        response = {
            "loan_id": loan_id_int,
            "applicant": {
                "id": applicant.applicant_id,
                "name": f"{applicant.first_name or ''} {applicant.last_name or ''}".strip(),
                "phone": getattr(applicant, 'mobile', None) or getattr(applicant, 'phone', None),
                "email": getattr(applicant, 'email', None),
                "type": "applicant"
            },
            "co_applicants": [extract_contact_info(co, "co_applicant") for co in co_applicants],
            "guarantors": [extract_contact_info(gu, "guarantor") for gu in guarantors],
            "references": [extract_contact_info(ref, "reference") for ref in references]
        }
        
        # Debug logging
        print(f"🔍 Contacts API Debug for loan_id {loan_id_int}:")
        print(f"   - Applicant: {response['applicant']['name']}")
        print(f"   - Co-applicants found: {len(co_applicants)}")
        print(f"   - Guarantors found: {len(guarantors)}")
        print(f"   - References found: {len(references)}")
        
        return response
        
    except Exception as e:
        print(f"Error in get_application_contacts: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to get contacts: {str(e)}")
