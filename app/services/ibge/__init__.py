from app.services.ibge.ibge_service import fetch_municipios
from app.services.ibge.localidades_parser import parse_localidades

__all__ = ["fetch_municipios", "parse_localidades"]
