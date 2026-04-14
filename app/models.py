from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


class Regiao(Base):
    __tablename__ = "dim_regioes"
    __table_args__ = {"schema": "datacrypt"}
    id_regiao = Column(Integer, primary_key=True, index=True)
    nome = Column(String(50), nullable=False)
    estados = relationship("Estado", back_populates="regiao")


class Estado(Base):
    __tablename__ = "dim_estados"
    __table_args__ = {"schema": "datacrypt"}
    id_estado = Column(Integer, primary_key=True, index=True)
    nome = Column(String(50), nullable=False)
    sigla = Column(String(2), nullable=False)
    id_regiao = Column(
        Integer, ForeignKey("datacrypt.dim_regioes.id_regiao"), nullable=False
    )
    regiao = relationship("Regiao", back_populates="estados")
    municipios = relationship("Municipio", back_populates="estado")


class Municipio(Base):
    __tablename__ = "dim_municipios"
    __table_args__ = {"schema": "datacrypt"}
    id_municipio = Column(Integer, primary_key=True, index=True)
    nome = Column(String(50), nullable=False)
    id_estado = Column(
        Integer, ForeignKey("datacrypt.dim_estados.id_estado"), nullable=False
    )
    estado = relationship("Estado", back_populates="municipios")


class TransparenciaOrgaoSiafiRaw(Base):
    __tablename__ = "transparencia_orgao_siafi_raw"
    __table_args__ = {"schema": "datacrypt"}
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(20), nullable=False, index=True)
    descricao = Column(Text, nullable=False)
    pagina_origem = Column(Integer, nullable=False)
    payload_original_json = Column(JSON, nullable=False)
    collected_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class TransparenciaOrgaoSiapeRaw(Base):
    __tablename__ = "transparencia_orgao_siape_raw"
    __table_args__ = {"schema": "datacrypt"}
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(20), nullable=False, index=True)
    descricao = Column(Text, nullable=False)
    pagina_origem = Column(Integer, nullable=False)
    payload_original_json = Column(JSON, nullable=False)
    collected_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class TransparenciaOrgaoSiafi(Base):
    __tablename__ = "transparencia_orgao_siafi"
    __table_args__ = {"schema": "datacrypt"}
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(20), nullable=False, unique=True, index=True)
    descricao = Column(Text, nullable=False)
    status_registro = Column(String(20), nullable=False, index=True)
    elegivel_dashboard = Column(Boolean, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class TransparenciaOrgaoSiape(Base):
    __tablename__ = "transparencia_orgao_siape"
    __table_args__ = {"schema": "datacrypt"}
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(20), nullable=False, unique=True, index=True)
    descricao = Column(Text, nullable=False)
    status_registro = Column(String(20), nullable=False, index=True)
    elegivel_dashboard = Column(Boolean, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class TransparenciaAuxilioBrasilMunicipio(Base):
    __tablename__ = "transparencia_auxilio_brasil_municipio"
    __table_args__ = (
        UniqueConstraint(
            "id_externo",
            "tipo_beneficio",
            "data_referencia",
            "municipio_codigo_ibge",
            name="uq_transparencia_auxilio_brasil_municipio_logical",
        ),
        {"schema": "datacrypt"},
    )
    id = Column(Integer, primary_key=True, index=True)
    id_externo = Column(Integer, nullable=False, index=True)
    tipo_beneficio = Column(String(50), nullable=False, index=True)
    data_referencia = Column(Date, nullable=False, index=True)
    municipio_codigo_ibge = Column(String(10), nullable=False, index=True)
    valor = Column(Numeric(18, 2), nullable=False)
    quantidade_beneficiados = Column(Integer, nullable=False)
    payload_json = Column(JSON, nullable=False)
    collected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
