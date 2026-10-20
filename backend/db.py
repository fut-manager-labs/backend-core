"""Configuração compartilhada; importar não conecta ao banco."""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv(Path(__file__).with_name(".env"))


class Base(DeclarativeBase):
    pass


def build_database_url(*, require_credentials=False):
    try:
        port = int(os.getenv("DB_PORT", "3306"))
    except ValueError:
        raise ValueError("DB_PORT deve ser um número inteiro.") from None
    if not 1 <= port <= 65535:
        raise ValueError("DB_PORT deve estar entre 1 e 65535.")
    if require_credentials and (not os.getenv("DB_USER") or "DB_PASSWORD" not in os.environ):
        raise ValueError("Configure DB_USER e DB_PASSWORD no ambiente ou no arquivo .env.")
    host = os.getenv("DB_HOST", "localhost")
    database = os.getenv("DB_NAME", "fut_manager")
    if not host or not database:
        raise ValueError("DB_HOST e DB_NAME não podem estar vazios.")
    return URL.create(
        "mysql+pymysql", username=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
        host=host, port=port, database=database, query={"charset": "utf8mb4"},
    )


engine = create_engine(build_database_url(), pool_pre_ping=True, echo=False,
                       connect_args={"connect_timeout": 5})
SessionLocal = sessionmaker(bind=engine)
