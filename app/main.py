from sqlalchemy import text

from app.database import Base, engine


def init_db():
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS datacrypt"))
        conn.commit()

    Base.metadata.create_all(engine)
