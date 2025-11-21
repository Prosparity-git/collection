import argparse
import logging
import mimetypes
import os
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Optional
# add
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import requests
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.applicant_document import ApplicantDocument, DocCategory
from app.services import s3 as s3_service


LOGGER = logging.getLogger("import_fi_documents")


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


@contextmanager
def db_session() -> Iterable[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_fi_doc_category_id(db: Session, desired_code: str) -> int:
    category = db.query(DocCategory).filter(DocCategory.code == desired_code).one_or_none()
    if category is None:
        raise RuntimeError(
            f"Doc category with code '{desired_code}' not found. "
            "Please insert it before running this importer."
        )
    LOGGER.debug("Using doc_category_id=%s for code=%s", category.id, desired_code)
    return category.id


def normalize_extension(url: str, content_type: Optional[str]) -> str:
    ext = ""
    path = url.split("?", 1)[0]
    guess = Path(path).suffix
    if guess:
        ext = guess.lower()
    elif content_type:
        ext = mimetypes.guess_extension(content_type) or ""
    return ext or ".pdf"


def stream_download(url: str, timeout: int = 30) -> requests.Response:
    response = requests.get(url, stream=True, timeout=timeout)
    response.raise_for_status()
    return response


def build_s3_key(doc_category_code: str, loan_application_id: str, extension: str) -> str:
    safe_loan_id = loan_application_id.strip()
    if not safe_loan_id:
        raise ValueError("loan_application_id is required to build S3 key")
    unique_part = uuid.uuid4()
    cleaned_ext = extension if extension.startswith(".") else f".{extension}"
    return f"{doc_category_code}/loan/{safe_loan_id}/{unique_part}{cleaned_ext}"


def normalize_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value}".strip()
    return str(value).strip()


def discover_uploaded_by(default_uploaded_by: Optional[int]) -> int:
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
    doc_category_id: int,
    doc_category_code: str,
    s3_bucket: str,
    uploaded_by: int,
    dry_run: bool,
) -> bool:
    applicant_id = normalize_cell(row.get("Application ID", ""))
    loan_application_id = normalize_cell(row.get("loan_application_id", ""))
    source_url = normalize_cell(row.get("FI Report Link", ""))

    if not applicant_id or not loan_application_id or not source_url:
        LOGGER.warning(
            "Skipping row due to missing required fields: applicant_id=%s, loan_application_id=%s, source_url=%s",
            applicant_id,
            loan_application_id,
            source_url,
        )
        return False

    try:
        loan_application_id_int = int(loan_application_id)
    except ValueError:
        LOGGER.error("Invalid loan_application_id value: %s", loan_application_id)
        return False

    existing = (
        db.query(ApplicantDocument)
        .filter(
            ApplicantDocument.loan_application_id == loan_application_id_int,
            ApplicantDocument.doc_category_id == doc_category_id,
            ApplicantDocument.s3_key.like(f"{doc_category_code}/loan/{loan_application_id}/%"),
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
            "[Dry-run] Would process applicant_id=%s loan_application_id=%s url=%s",
            applicant_id,
            loan_application_id,
            source_url,
        )
        return True

    try:
        response = stream_download(source_url)
    except requests.RequestException as exc:
        LOGGER.error(
            "Failed to download file for loan_application_id=%s from %s: %s",
            loan_application_id,
            source_url,
            exc,
        )
        return False

    try:
        extension = normalize_extension(source_url, response.headers.get("Content-Type"))
        key = build_s3_key(doc_category_code, loan_application_id, extension)
        file_name = Path(key).name

        s3_service._s3.upload_fileobj(  # pylint: disable=protected-access
            response.raw,
            s3_bucket,
            key,
            ExtraArgs={"ContentType": response.headers.get("Content-Type", "application/pdf")},
        )
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.error("S3 upload failed for key=%s: %s", key, exc)
        return False
    finally:
        response.close()

    document = ApplicantDocument(
        applicant_id=applicant_id,
        loan_application_id=loan_application_id_int,
        repayment_id=None,
        field_visit_location_id=None,
        doc_category_id=doc_category_id,
        uploaded_by=uploaded_by,
        file_name=file_name,
        s3_key=key,
        notes=None,
    )

    try:
        db.add(document)
        db.commit()
    except SQLAlchemyError as exc:  # pylint: disable=broad-except
        LOGGER.error("Database insert failed for loan_application_id=%s: %s", loan_application_id, exc)
        db.rollback()
        return False

    LOGGER.info(
        "Imported applicant_id=%s loan_application_id=%s -> s3://%s/%s",
        applicant_id,
        loan_application_id,
        s3_bucket,
        key,
    )
    return True


def import_documents(
    excel_path: Path,
    uploaded_by: Optional[int],
    doc_category_code: str,
    dry_run: bool,
) -> None:
    uploaded_by_id = discover_uploaded_by(uploaded_by)
    LOGGER.info("Starting import from %s (dry-run=%s)", excel_path, dry_run)

    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found at {excel_path}")

    df = pd.read_excel(excel_path).fillna("")

    with db_session() as db:
        doc_category_id = get_fi_doc_category_id(db, doc_category_code)
        s3_bucket = s3_service.S3_BUCKET

        successes = 0
        for _, row in df.iterrows():
            if import_row(
                db=db,
                row=row,
                doc_category_id=doc_category_id,
                doc_category_code=doc_category_code,
                s3_bucket=s3_bucket,
                uploaded_by=uploaded_by_id,
                dry_run=dry_run,
            ):
                successes += 1

        if dry_run:
            LOGGER.info("Dry run complete. Rows evaluated: %s", len(df))
        else:
            LOGGER.info("Import complete. Documents inserted: %s", successes)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import FI documents into applicant_document table.")
    parser.add_argument(
        "--excel-path",
        type=Path,
        required=True,
        help="Absolute path to the Excel file (e.g., /path/to/FI_DOCS_WITH LOAN id.xlsx)",
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
        default="FI_LOCATION",
        help="Doc category code to use when looking up doc_category_id.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform validation without downloading/uploading or writing to the database.",
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
            uploaded_by=args.uploaded_by,
            doc_category_code=args.doc_category_code,
            dry_run=args.dry_run,
        )
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.exception("Import failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()

