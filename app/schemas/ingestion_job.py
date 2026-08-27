from datetime import datetime
from typing import Any

from pydantic import BaseModel


class IngestionJobResponse(BaseModel):
    id: int
    company_id: int
    job_type: str
    status: str
    payload: dict[str, Any]
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    model_config = {
        "from_attributes": True,
    }
