import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.dependencies import DBDependency
from app.auth import CurrentUserDependency
from app.schemas import CompanyCreateRequest, CompanyResponse
from app.models import Company

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/companies",
    tags=["Companies"]
)

# Add a new company
@router.post("", status_code=status.HTTP_201_CREATED, response_model=CompanyResponse)
def create_company(
    company_request: CompanyCreateRequest,
    db: DBDependency,
    current_user: CurrentUserDependency
):
    ticker = company_request.ticker.upper()
    cik = company_request.cik.zfill(10)

    existing_company = db.scalar(
        select(Company).where(
            (Company.ticker == ticker) | (Company.cik == cik)
        )
    )

    if existing_company:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Company with this ticker or CIK already exists"
        )

    company = Company(
        cik=cik,
        ticker=ticker,
        name=company_request.name
    )

    db.add(company)

    try:
        db.commit()
        db.refresh(company)
    except IntegrityError:
        db.rollback()

        logger.warning(
            "Company creation failed: uniquenes conflict"
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Company with this ticker or CIK already exists"
        )

    logger.info(
        "Company created successfully: company_id=%s user_id=%s",
        company.id,
        current_user.id
    )

    return company


# Get all companies
@router.get("", status_code=status.HTTP_200_OK, response_model=list[CompanyResponse])
def get_companies(
    db: DBDependency,
    current_user: CurrentUserDependency
):
    companies = db.scalars(
        select(Company).order_by(Company.ticker)
    ).all()

    return companies

# Get company by ticker
@router.get("/{ticker}", status_code=status.HTTP_200_OK, response_model=CompanyResponse)
def get_company(
    ticker: str,
    db: DBDependency,
    current_user: CurrentUserDependency
):
    company = db.scalar(
        select(Company).where(
            Company.ticker == ticker.upper()
        )
    )

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    return company