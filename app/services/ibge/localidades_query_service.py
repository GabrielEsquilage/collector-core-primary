from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Estado, Municipio, Regiao


def get_regiao(db: Session, id_regiao: int):
    return (
        db.query(Regiao)
        .filter(Regiao.id_regiao == id_regiao)
        .one_or_none()
    )


def list_regiao_estados(db: Session, id_regiao: int):
    regiao = (
        db.query(Regiao)
        .options(selectinload(Regiao.estados).joinedload(Estado.regiao))
        .filter(Regiao.id_regiao == id_regiao)
        .one_or_none()
    )

    if regiao is None:
        return None, []

    estados = sorted(regiao.estados, key=lambda estado: estado.nome)
    return regiao, estados


def list_regioes(db: Session, id_regiao: int | None = None):
    query = db.query(Regiao)

    if id_regiao is not None:
        query = query.filter(Regiao.id_regiao == id_regiao)

    return query.order_by(Regiao.id_regiao).all()


def get_estado(db: Session, id_estado: int):
    return (
        db.query(Estado)
        .options(joinedload(Estado.regiao))
        .filter(Estado.id_estado == id_estado)
        .one_or_none()
    )


def list_estado_municipios(
    db: Session,
    id_estado: int,
    limit: int = 100,
    offset: int = 0,
    nome: str | None = None,
):
    estado = (
        db.query(Estado)
        .options(selectinload(Estado.municipios))
        .filter(Estado.id_estado == id_estado)
        .one_or_none()
    )

    if estado is None:
        return None, 0, []

    municipios = estado.municipios

    if nome is not None:
        termo = nome.lower()
        municipios = [
            municipio for municipio in municipios if termo in municipio.nome.lower()
        ]

    municipios = sorted(municipios, key=lambda municipio: municipio.nome)
    total = len(municipios)
    items = municipios[offset : offset + limit]

    return estado, total, items


def list_estados(
    db: Session,
    id_estado: int | None = None,
    sigla: str | None = None,
):
    query = db.query(Estado).options(joinedload(Estado.regiao))

    if id_estado is not None:
        query = query.filter(Estado.id_estado == id_estado)

    if sigla is not None:
        query = query.filter(Estado.sigla == sigla.upper())

    return query.order_by(Estado.nome).all()


def get_municipio(db: Session, id_municipio: int):
    return (
        db.query(Municipio)
        .options(joinedload(Municipio.estado))
        .filter(Municipio.id_municipio == id_municipio)
        .one_or_none()
    )


def list_municipios(
    db: Session,
    limit: int = 100,
    offset: int = 0,
    id_municipio: int | None = None,
    id_estado: int | None = None,
    nome: str | None = None,
):
    query = db.query(Municipio).options(joinedload(Municipio.estado))

    if id_municipio is not None:
        query = query.filter(Municipio.id_municipio == id_municipio)

    if id_estado is not None:
        query = query.filter(Municipio.id_estado == id_estado)

    if nome is not None:
        query = query.filter(Municipio.nome.ilike(f"%{nome}%"))

    total = query.count()
    items = query.order_by(Municipio.nome).offset(offset).limit(limit).all()

    return total, items
