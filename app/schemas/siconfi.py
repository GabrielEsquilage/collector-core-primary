from pydantic import BaseModel
from typing import Optional

class SiconfiKpiMacroBase(BaseModel):
    cod_ibge: str
    uf: str
    periodo: int
    receita_total: Optional[float] = 0.0
    despesa_total: Optional[float] = 0.0
    receita_corrente_liquida: Optional[float] = 0.0
    despesa_saude: Optional[float] = 0.0
    despesa_educacao: Optional[float] = 0.0
    despesa_saneamento: Optional[float] = 0.0
    despesa_urbanismo: Optional[float] = 0.0
    despesa_seguranca: Optional[float] = 0.0
    investimentos: Optional[float] = 0.0
    despesa_pessoal: Optional[float] = 0.0
    divida_consolidada: Optional[float] = 0.0
    restos_a_pagar: Optional[float] = 0.0
    resultado_primario: Optional[float] = 0.0
    resultado_previdenciario: Optional[float] = 0.0
    ppp_contratadas: Optional[float] = 0.0

class SiconfiKpiMacroResponse(BaseModel):
    ano: int
    data: list[SiconfiKpiMacroBase]

class SiconfiRankingItem(BaseModel):
    cod_ibge: str
    uf: str
    periodo: int
    valor: float

class SiconfiRankingResponse(BaseModel):
    ano: int
    indicador: str
    data: list[SiconfiRankingItem]

class SiconfiSerieHistoricaItem(BaseModel):
    ano: int
    periodo: int
    valor: float

class SiconfiSerieHistoricaResponse(BaseModel):
    cod_ibge: str
    indicador: str
    data: list[SiconfiSerieHistoricaItem]

class SiconfiAgregacaoItem(BaseModel):
    periodo: int
    receita_total: Optional[float] = 0.0
    despesa_total: Optional[float] = 0.0
    receita_corrente_liquida: Optional[float] = 0.0
    despesa_saude: Optional[float] = 0.0
    despesa_educacao: Optional[float] = 0.0
    despesa_saneamento: Optional[float] = 0.0
    despesa_urbanismo: Optional[float] = 0.0
    despesa_seguranca: Optional[float] = 0.0
    investimentos: Optional[float] = 0.0
    despesa_pessoal: Optional[float] = 0.0
    divida_consolidada: Optional[float] = 0.0
    restos_a_pagar: Optional[float] = 0.0
    resultado_primario: Optional[float] = 0.0
    resultado_previdenciario: Optional[float] = 0.0
    ppp_contratadas: Optional[float] = 0.0

class SiconfiAgregacaoResponse(BaseModel):
    ano: int
    uf: Optional[str] = None
    data: list[SiconfiAgregacaoItem]

class SiconfiComparativoResponse(BaseModel):
    ano: int
    data: list[SiconfiKpiMacroBase]
