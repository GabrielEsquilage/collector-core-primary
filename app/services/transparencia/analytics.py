from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, Integer

from app.models import FatoRepasseMunicipio, Municipio, Estado

def get_serie_historica_beneficio(db: Session, tipo_beneficio: str, codigo_ibge: str):
    query = (
        db.query(
            extract('year', FatoRepasseMunicipio.data_referencia).label('ano'),
            extract('month', FatoRepasseMunicipio.data_referencia).label('mes'),
            func.sum(FatoRepasseMunicipio.valor).label('valor'),
            func.sum(FatoRepasseMunicipio.quantidade_beneficiados).label('quantidade_beneficiados')
        )
        .filter(
            FatoRepasseMunicipio.tipo_beneficio == tipo_beneficio,
            FatoRepasseMunicipio.municipio_codigo_ibge == codigo_ibge
        )
        .group_by('ano', 'mes')
        .order_by('ano', 'mes')
    )
    
    results = query.all()
    return [
        {
            "ano": int(r.ano),
            "mes": int(r.mes),
            "valor": Decimal(r.valor or 0),
            "quantidade_beneficiados": int(r.quantidade_beneficiados or 0)
        }
        for r in results
    ]

def get_ranking_beneficio(db: Session, tipo_beneficio: str, ano: int, uf: str | None = None, limit: int = 10):
    query = (
        db.query(
            FatoRepasseMunicipio.municipio_codigo_ibge.label('codigo_ibge'),
            Estado.sigla.label('uf'),
            Municipio.nome.label('nome_municipio'),
            func.sum(FatoRepasseMunicipio.valor).label('valor_total'),
            func.sum(FatoRepasseMunicipio.quantidade_beneficiados).label('quantidade_beneficiados_total')
        )
        .join(Municipio, Municipio.id_municipio == func.cast(FatoRepasseMunicipio.municipio_codigo_ibge, Integer))
        .join(Estado, Estado.id_estado == Municipio.id_estado)
        .filter(
            FatoRepasseMunicipio.tipo_beneficio == tipo_beneficio,
            extract('year', FatoRepasseMunicipio.data_referencia) == ano
        )
    )
    
    if uf:
        query = query.filter(Estado.sigla == uf.upper())
        
    query = (
        query.group_by(
            FatoRepasseMunicipio.municipio_codigo_ibge,
            Estado.sigla,
            Municipio.nome
        )
        .order_by(func.sum(FatoRepasseMunicipio.valor).desc())
        .limit(limit)
    )
    
    results = query.all()
    return [
        {
            "codigo_ibge": r.codigo_ibge,
            "uf": r.uf,
            "nome_municipio": r.nome_municipio,
            "valor_total": Decimal(r.valor_total or 0),
            "quantidade_beneficiados_total": int(r.quantidade_beneficiados_total or 0)
        }
        for r in results
    ]

def get_agregacao_beneficio(db: Session, tipo_beneficio: str, ano: int, uf: str | None = None):
    query = (
        db.query(
            extract('month', FatoRepasseMunicipio.data_referencia).label('mes'),
            func.sum(FatoRepasseMunicipio.valor).label('valor_total'),
            func.sum(FatoRepasseMunicipio.quantidade_beneficiados).label('quantidade_beneficiados_total')
        )
        .filter(
            FatoRepasseMunicipio.tipo_beneficio == tipo_beneficio,
            extract('year', FatoRepasseMunicipio.data_referencia) == ano
        )
    )
    
    if uf:
        query = query.join(Municipio, Municipio.id_municipio == func.cast(FatoRepasseMunicipio.municipio_codigo_ibge, Integer))
        query = query.join(Estado, Estado.id_estado == Municipio.id_estado)
        query = query.filter(Estado.sigla == uf.upper())
        
    query = query.group_by('mes').order_by('mes')
    
    results = query.all()
    return [
        {
            "mes": int(r.mes),
            "valor_total": Decimal(r.valor_total or 0),
            "quantidade_beneficiados_total": int(r.quantidade_beneficiados_total or 0)
        }
        for r in results
    ]
