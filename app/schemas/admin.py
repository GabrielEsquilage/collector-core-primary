from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    tipo_beneficio: str
    resource: str
    codigo_ibge: str
    mes_ano: str
    status: str
    attempts: int
    last_error: str | None
    pages_collected: int
    records_received: int
    inserted: int
    updated: int
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class JobItemListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[JobItemResponse]
