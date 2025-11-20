import argparse
import logging
import mimetypes
import os
import sys
import uuid
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.applicant_document import ApplicantDocument, DocCategory
from app.services import s3 as s3_service

LOGGER = logging.getLogger("import_local_documents")


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def get_doc_category_id(db: Session, doc_category_code: str) -> int:
    """Get doc_category_id by code (e.g., 'LEGAL' for id=12)"""
    category = db.query(DocCategory).filter(DocCategory.code == doc_category_code).one_or_none()
    if category is None:
        raise RuntimeError(
            f"Doc category with code '{doc_category_code}' not found. "
            "Please insert it before running this importer."
        )
    LOGGER.debug("Using doc_category_id=%s for code=%s", category.id, doc_category_code)
    return category.id


def build_s3_key_with_applicant_id(
    doc_category_code: str,
    loan_application_id: str,
    applicant_id: str,
    original_filename: str,
) -> str:
    """Build S3 key with applicant_id included in the path.
    
    Format: {doc_category_code}/{loan_application_id}/{applicant_id}/{original_filename}
    Example: LEGAL/12345/APP001/Legal-APP001.pdf
    """
    safe_loan_id = loan_application_id.strip()
    safe_applicant_id = applicant_id.strip()
    
    if not safe_loan_id:
        raise ValueError("loan_application_id is required to build S3 key")
    if not safe_applicant_id:
        raise ValueError("applicant_id is required to build S3 key")
    
    # Format: {doc_category_code}/{loan_application_id}/{applicant_id}/{original_filename}
    return f"{doc_category_code}/{safe_loan_id}/{safe_applicant_id}/{original_filename}"


def normalize_cell(value: object) -> str:
    """Normalize Excel cell value to string"""
    if value is None:
        return ""
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value}".strip()
    return str(value).strip()


def find_pdf_file(pdf_folder: Path, applicant_id: str) -> Path | None:
    """Find PDF file by applicant_id in the folder.
    
    Tries multiple patterns:
    1. {applicant_id}.pdf
    2. Legal-{applicant_id}.pdf (for LEGAL category)
    3. Files starting with {applicant_id}_
    4. Files containing {applicant_id}
    """
    applicant_id_clean = applicant_id.strip()
    
    # Try exact match first
    for ext in ['.pdf', '.PDF']:
        file_path = pdf_folder / f"{applicant_id_clean}{ext}"
        if file_path.exists():
            return file_path
    
    # Try Legal-{applicant_id}.pdf format
    for ext in ['.pdf', '.PDF']:
        file_path = pdf_folder / f"Legal-{applicant_id_clean}{ext}"
        if file_path.exists():
            return file_path
    
    # Try files starting with applicant_id
    for file_path in pdf_folder.glob(f"{applicant_id_clean}*"):
        if file_path.suffix.lower() == '.pdf':
            return file_path
    
    # Try files containing applicant_id
    for file_path in pdf_folder.glob(f"*{applicant_id_clean}*.pdf"):
        if file_path.exists():
            return file_path
    
    return None


def discover_uploaded_by(default_uploaded_by: Optional[int]) -> int:
    """Get uploaded_by user ID"""
    if default_uploaded_by is not None:
        return default_uploaded_by

    uploaded_by = os.getenv("DEFAULT_UPLOADED_BY_ID")
    if uploaded_by:
        try:
            return int(uploaded_by)
        except ValueError as exc:
            raise ValueError(
                f"Invalid DEFAULT_UPLOADED_BY_ID value: {uploaded_by}"
            ) from exc

    raise RuntimeError(
        "No uploaded_by id provided. Pass --uploaded-by or set DEFAULT_UPLOADED_BY_ID."
    )


def import_row(
    db: Session,
    row: dict,
    pdf_folder: Path,
    doc_category_id: int,
    doc_category_code: str,
    s3_bucket: str,
    uploaded_by: int,
    dry_run: bool,
    applicant_id_column: str = "applicant_id",
    loan_application_id_column: str = "loan_application_id",
) -> bool:
    """Import a single row from Excel"""
    
    applicant_id = normalize_cell(row.get(applicant_id_column, ""))
    loan_application_id = normalize_cell(row.get(loan_application_id_column, ""))
    
    if not applicant_id or not loan_application_id:
        LOGGER.warning(
            "Skipping row due to missing required fields: applicant_id=%s, loan_application_id=%s",
            applicant_id,
            loan_application_id,
        )
        return False
    
    try:
        loan_application_id_int = int(loan_application_id)
    except ValueError:
        LOGGER.error("Invalid loan_application_id value: %s", loan_application_id)
        return False
    
    # Find the PDF file by applicant_id
    pdf_file = find_pdf_file(pdf_folder, applicant_id)
    if not pdf_file:
        LOGGER.warning(
            "PDF file not found for applicant_id=%s in folder %s",
            applicant_id,
            pdf_folder,
        )
        return False
    
    # Get original filename from local file (e.g., "PROSAPP001.pdf")
    original_filename = pdf_file.name
    
    # Add prefix based on doc_category
    # If doc_category is LEGAL (id=12), add "Legal-" prefix to filename
    if doc_category_code.upper() == "LEGAL" or doc_category_id == 12:
        # Check if prefix already exists
        if not original_filename.startswith("Legal-"):
            db_filename = f"Legal-{original_filename}"
        else:
            db_filename = original_filename
    else:
        db_filename = original_filename
    
    # Check if document already exists
    existing = (
        db.query(ApplicantDocument)
        .filter(
            ApplicantDocument.loan_application_id == loan_application_id_int,
            ApplicantDocument.doc_category_id == doc_category_id,
        )
        .first()
    )
    if existing:
        LOGGER.info(
            "Document already exists for loan_application_id=%s; skipping",
            loan_application_id,
        )
        return False
    
    if dry_run:
        LOGGER.info(
            "[Dry-run] Would process applicant_id=%s loan_application_id=%s file=%s",
            applicant_id,
            loan_application_id,
            pdf_file,
        )
        return True
    
    # Determine content type
    content_type, _ = mimetypes.guess_type(str(pdf_file))
    if not content_type:
        content_type = "application/pdf"
    
    # Build S3 key with applicant_id included
    # Format: {doc_category_code}/{loan_application_id}/{applicant_id}/{db_filename}
    # Use db_filename (with prefix if needed) for S3 key
    key = build_s3_key_with_applicant_id(
        doc_category_code,
        loan_application_id,
        applicant_id,
        db_filename,  # Use filename with prefix (e.g., "Legal-PROSAPP001.pdf")
    )
    
    try:
        # Upload file to S3
        s3_service._s3.upload_file(
            str(pdf_file),
            s3_bucket,
            key,
            ExtraArgs={"ContentType": content_type}
        )
        LOGGER.info("Uploaded to S3: s3://%s/%s", s3_bucket, key)
    except Exception as exc:
        LOGGER.error("S3 upload failed for key=%s: %s", key, exc)
        return False
    
    # Create database record with prefixed filename
    document = ApplicantDocument(
        applicant_id=applicant_id,
        loan_application_id=loan_application_id_int,
        repayment_id=None,
        field_visit_location_id=None,
        doc_category_id=doc_category_id,
        uploaded_by=uploaded_by,
        file_name=db_filename,  # Use filename with prefix (e.g., "Legal-PROSAPP001.pdf")
        s3_key=key,
        notes=None,
    )
    
    try:
        db.add(document)
        db.commit()
        db.refresh(document)
    except SQLAlchemyError as exc:
        LOGGER.error("Database insert failed for loan_application_id=%s: %s", loan_application_id, exc)
        db.rollback()
        return False
    
    LOGGER.info(
        "Imported applicant_id=%s loan_application_id=%s file_name=%s (original=%s) -> s3://%s/%s",
        applicant_id,
        loan_application_id,
        db_filename,
        original_filename,
        s3_bucket,
        key,
    )
    return True


def import_documents(
    excel_path: Path,
    pdf_folder: Path,
    uploaded_by: Optional[int],
    doc_category_code: str,
    dry_run: bool,
    applicant_id_column: str = "applicant_id",
    loan_application_id_column: str = "loan_application_id",
) -> None:
    """Main import function"""
    uploaded_by_id = discover_uploaded_by(uploaded_by)
    LOGGER.info("Starting import from %s (dry-run=%s)", excel_path, dry_run)
    LOGGER.info("PDF folder: %s", pdf_folder)
    LOGGER.info("Doc category code: %s", doc_category_code)
    
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found at {excel_path}")
    
    if not pdf_folder.exists():
        raise FileNotFoundError(f"PDF folder not found at {pdf_folder}")
    
    df = pd.read_excel(excel_path).fillna("")
    
    db = SessionLocal()
    
    try:
        doc_category_id = get_doc_category_id(db, doc_category_code)
        s3_bucket = s3_service.S3_BUCKET
        
        LOGGER.info("Using doc_category_id=%s for code=%s", doc_category_id, doc_category_code)
        
        successes = 0
        for idx, row in df.iterrows():
            if import_row(
                db=db,
                row=row,
                pdf_folder=pdf_folder,
                doc_category_id=doc_category_id,
                doc_category_code=doc_category_code,
                s3_bucket=s3_bucket,
                uploaded_by=uploaded_by_id,
                dry_run=dry_run,
                applicant_id_column=applicant_id_column,
                loan_application_id_column=loan_application_id_column,
            ):
                successes += 1
        
        if dry_run:
            LOGGER.info("Dry run complete. Rows evaluated: %s", len(df))
        else:
            LOGGER.info("Import complete. Documents inserted: %s/%s", successes, len(df))
    finally:
        db.close()


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import local PDF documents (named by applicant_id) into applicant_document table."
    )
    parser.add_argument(
        "--excel-path",
        type=Path,
        required=True,
        help="Absolute path to the Excel file with applicant_id and loan_application_id columns",
    )
    parser.add_argument(
        "--pdf-folder",
        type=Path,
        required=True,
        help="Absolute path to folder containing PDF files (files should be named like 'Legal-{applicant_id}.pdf')",
    )
    parser.add_argument(
        "--uploaded-by",
        type=int,
        default=None,
        help="User ID to record as uploaded_by. If omitted, DEFAULT_UPLOADED_BY_ID env var is used.",
    )
    parser.add_argument(
        "--doc-category-code",
        type=str,
        default="LEGAL",
        help="Doc category code (default: 'LEGAL' for doc_category_id=12)",
    )
    parser.add_argument(
        "--applicant-id-column",
        type=str,
        default="applicant_id",
        help="Excel column name for applicant_id (default: 'applicant_id')",
    )
    parser.add_argument(
        "--loan-id-column",
        type=str,
        default="loan_application_id",
        help="Excel column name for loan_application_id (default: 'loan_application_id')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform validation without uploading or writing to the database.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)
    configure_logging(args.verbose)
    LOGGER.debug("Using database URL: %s", settings.DATABASE_URL)
    try:
        import_documents(
            excel_path=args.excel_path,
            pdf_folder=args.pdf_folder,
            uploaded_by=args.uploaded_by,
            doc_category_code=args.doc_category_code,
            dry_run=args.dry_run,
            applicant_id_column=args.applicant_id_column,
            loan_application_id_column=args.loan_id_column,
        )
    except Exception as exc:
        LOGGER.exception("Import failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()

