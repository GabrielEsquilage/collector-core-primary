from pydantic import BaseModel, ConfigDict


class RegiaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_regiao: int
    nome: str


class EstadoSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_estado: int
    nome: str
    sigla: str
    id_regiao: int


class EstadoResponse(EstadoSummaryResponse):
    regiao: RegiaoResponse


class MunicipioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_municipio: int
    nome: str
    id_estado: int
    estado: EstadoSummaryResponse


class MunicipioListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[MunicipioResponse]

class DemografiaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    codigo_ibge_municipio: str
    ano: int
    variavel_codigo: str
    valor_estatistico: float

class DemografiaListResponse(BaseModel):
    total: int
    items: list[DemografiaResponse]
