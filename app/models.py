from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Regiao(Base):
    __tablename__ = "dim_regioes"
    __table_args__ = {"schema": "datacrypt"}

    id_regiao: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(50), nullable=False)
    estados: Mapped[list[Estado]] = relationship("Estado", back_populates="regiao")


class Estado(Base):
    __tablename__ = "dim_estados"
    __table_args__ = {"schema": "datacrypt"}

    id_estado: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(50), nullable=False)
    sigla: Mapped[str] = mapped_column(String(2), nullable=False)
    id_regiao: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("datacrypt.dim_regioes.id_regiao"),
        nullable=False,
    )
    regiao: Mapped[Regiao] = relationship("Regiao", back_populates="estados")
    municipios: Mapped[list[Municipio]] = relationship("Municipio", back_populates="estado")


class Municipio(Base):
    __tablename__ = "dim_municipios"
    __table_args__ = {"schema": "datacrypt"}

    id_municipio: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(50), nullable=False)
    id_estado: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("datacrypt.dim_estados.id_estado"),
        nullable=False,
    )
    estado: Mapped[Estado] = relationship("Estado", back_populates="municipios")


class TransparenciaOrgaoSiafiRaw(Base):
    __tablename__ = "transparencia_orgao_siafi_raw"
    __table_args__ = {"schema": "datacrypt"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    pagina_origem: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_original_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class TransparenciaOrgaoSiapeRaw(Base):
    __tablename__ = "transparencia_orgao_siape_raw"
    __table_args__ = {"schema": "datacrypt"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    pagina_origem: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_original_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class TransparenciaOrgaoSiafi(Base):
    __tablename__ = "transparencia_orgao_siafi"
    __table_args__ = {"schema": "datacrypt"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    status_registro: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    elegivel_dashboard: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class TransparenciaOrgaoSiape(Base):
    __tablename__ = "transparencia_orgao_siape"
    __table_args__ = {"schema": "datacrypt"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    status_registro: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    elegivel_dashboard: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_externo: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tipo_beneficio: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    data_referencia: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    municipio_codigo_ibge: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    quantidade_beneficiados: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class TransparenciaBolsaFamiliaMunicipio(Base):
    __tablename__ = "transparencia_bolsa_familia_municipio"
    __table_args__ = (
        UniqueConstraint(
            "id_externo",
            "tipo_beneficio",
            "data_referencia",
            "municipio_codigo_ibge",
            name="uq_transparencia_bolsa_familia_municipio_logical",
        ),
        {"schema": "datacrypt"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_externo: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tipo_beneficio: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    data_referencia: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    municipio_codigo_ibge: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    quantidade_beneficiados: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class TransparenciaNovoBolsaFamiliaMunicipio(Base):
    __tablename__ = "transparencia_novo_bolsa_familia_municipio"
    __table_args__ = (
        UniqueConstraint(
            "id_externo",
            "tipo_beneficio",
            "data_referencia",
            "municipio_codigo_ibge",
            name="uq_transparencia_novo_bolsa_familia_municipio_logical",
        ),
        {"schema": "datacrypt"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    id_externo: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tipo_beneficio: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    data_referencia: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    municipio_codigo_ibge: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    quantidade_beneficiados: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class TransparenciaCargaJob(Base):
    __tablename__ = "transparencia_carga_job"
    __table_args__ = (
        UniqueConstraint("job_code", name="uq_transparencia_carga_job_code"),
        {"schema": "datacrypt"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    tipo_carga: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True, default="pending")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    total_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pending_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    running_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    items: Mapped[list[TransparenciaCargaJobItem]] = relationship(
        "TransparenciaCargaJobItem",
        back_populates="job",
        cascade="all, delete-orphan",
    )


class TransparenciaCargaJobItem(Base):
    __tablename__ = "transparencia_carga_job_item"
    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "tipo_beneficio",
            "codigo_ibge",
            "mes_ano",
            name="uq_transparencia_carga_job_item_logical",
        ),
        {"schema": "datacrypt"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("datacrypt.transparencia_carga_job.id"),
        nullable=False,
        index=True,
    )
    tipo_beneficio: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resource: Mapped[str] = mapped_column(String(100), nullable=False)
    codigo_ibge: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    mes_ano: Mapped[str] = mapped_column(String(6), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    pages_collected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    job: Mapped[TransparenciaCargaJob] = relationship("TransparenciaCargaJob", back_populates="items")
