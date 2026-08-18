import logging

from fastapi import APIRouter, HTTPException, status, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from app.auth import CurrentUserDependency
from app.db.dependencies import DBDependency
from app.schemas.filing import FilingCreateRequest, FilingResponse
from app.models import Filing, Company

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/filings",
    tags=["Filings"]
)

# Create a new filing
@router.post("", status_code=status.HTTP_201_CREATED, response_model=FilingResponse)
def create_filing(
    filing_request: FilingCreateRequest,
    db: DBDependency,
    current_user: CurrentUserDependency
):
    # Checking if company is already available
    company = db.scalar(
        select(Company).where(
            Company.id == filing_request.company_id
        )
    )

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    # Checking if filing already exists
    existing_filing = db.scalar(
        select(Filing).where(
            Filing.accession_number == filing_request.accession_number
        )
    )

    if existing_filing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Filing already exists"
        )

    filing = Filing(
        company_id=filing_request.company_id,
        accession_number=filing_request.accession_number,
        filing_type=filing_request.filing_type.upper(),
        filed_at=filing_request.filed_at,
        reporting_period=filing_request.reporting_period,
        source_url=filing_request.source_url,
        status="pending"
    )

    db.add(filing)

    try:
        db.commit()
        db.refresh(filing)
    except IntegrityError:
        db.rollback()

        logger.warning(
            "Filing creation failed: accession_number=%s",
            filing_request.accession_number
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Filing already exists"
        )


    logger.info(
        "Filing created successfully: filing_id=%s company_id=%s user_id=%s",
        filing.id,
        filing.company_id,
        current_user.id
    )

    return filing


# Get all filings
@router.get("", status_code=status.HTTP_200_OK, response_model=list[FilingResponse])
def get_filings(
    db: DBDependency, 
    current_user: CurrentUserDependency,
    company_id: int | None = Query(default=None, gt=0),
    filing_type: str | None = Query(default=None)
):

    query = select(Filing)

    if company_id is not None:
        query = query.where(Filing.company_id == company_id)

    if filing_type is not None:
        query = query.where(Filing.filing_type == filing_type.upper())

    query = query.order_by(
        Filing.filed_at.desc()
    )

    filings = db.scalars(query).all()

    return filings

# Get filings by filing_id
@router.get("/{filing_id}", status_code=status.HTTP_200_OK, response_model=FilingResponse)
def get_filing(
    filing_id: int,
    db: DBDependency,
    current_user: CurrentUserDependency
):

    filing = db.scalar(
        select(Filing).where(
            Filing.id == filing_id
        )
    )

    if filing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Filing not found"
        )

    return filing