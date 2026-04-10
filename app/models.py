from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


class Regiao(Base):
    __tablename__ = "dim_regioes"
    __table_args__ = {"schema": "datacrypt"}
    id = Column(Integer, primary_key=True, index=True)
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
    municipio = relationship("Municipio", back_populates="estado")


class Municipio(Base):
    __tablename__ = "dim_municipios"
    __table_args__ = {"schema": "datacrypt"}
    id_municipio = Column(Integer, primary_key=True, index=True)
    nome = Column(String(50), nullable=False)
    id_estado = Column(
        Integer, ForeignKey("datacrypt.dim_estados.id_estado"), nullable=False
    )
    estado = relationship("Estado", back_populates="municipio")
