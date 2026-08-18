from pydantic import BaseModel, Field

class CompanyCreateRequest(BaseModel):
    cik: str = Field(min_length=1, max_length=10)
    ticker: str = Field(min_length=1, max_length=10)
    name: str = Field(min_length=1, max_length=255)

class CompanyResponse(BaseModel):
    id: int
    cik: str
    ticker: str
    name: str

    model_config = {
        "from_attributes": True
    }