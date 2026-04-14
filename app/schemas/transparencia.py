from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TransparenciaCollectRequest(BaseModel):
    codigo: str | None = None
    descricao: str | None = None


class TransparenciaCollectResponse(BaseModel):
    tipo_orgao: str
    pages_collected: int
    records_received: int
    raw_inserted: int
    clean_inserted: int
    clean_updated: int


class TransparenciaOrgaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    descricao: str
    status_registro: str
    elegivel_dashboard: bool
    created_at: datetime
    updated_at: datetime


class TransparenciaOrgaoListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[TransparenciaOrgaoResponse]


class AuxilioBrasilCollectRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mes_ano: str = Field(alias="mesAno")
    codigo_ibge: str = Field(alias="codigoIbge")
    pagina_inicial: int = Field(default=1, alias="pagina")


class AuxilioBrasilCollectPeriodoRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ano: int = Field(ge=2000, le=2100)
    codigo_ibge: str = Field(alias="codigoIbge")
    pagina_inicial: int = Field(default=1, alias="pagina")


class AuxilioBrasilCollectResponse(BaseModel):
    tipo_beneficio: str
    pages_collected: int
    records_received: int
    inserted: int
    updated: int


class AuxilioBrasilCollectPeriodoMesResponse(BaseModel):
    mes_ano: str
    pages_collected: int
    records_received: int
    inserted: int
    updated: int


class AuxilioBrasilCollectPeriodoResponse(BaseModel):
    tipo_beneficio: str
    codigo_ibge: str
    ano: int
    months_processed: int
    pages_collected: int
    records_received: int
    inserted: int
    updated: int
    items: list[AuxilioBrasilCollectPeriodoMesResponse]


class AuxilioBrasilMunicipioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    id_externo: int
    tipo_beneficio: str
    data_referencia: date
    municipio_codigo_ibge: str
    valor: Decimal
    quantidade_beneficiados: int
    payload_json: dict
    collected_at: datetime


class AuxilioBrasilMunicipioListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[AuxilioBrasilMunicipioResponse]
