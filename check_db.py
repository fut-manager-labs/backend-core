"""Verificação somente de leitura: python check_db.py."""
import re
import sys

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError


def normalize_type(value, dialect):
    value = str(value.compile(dialect=dialect)).upper()
    return re.sub(r"\b(?:INTEGER|INT)\b(?:\(\d+\))?", "INTEGER", value)


def normalize_default(value):
    if value is None:
        return None
    value = str(value).strip().strip("'").upper()
    return "CURRENT_TIMESTAMP" if value in {"CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP()"} else value


def compare_schema(connection, metadata):
    inspector = inspect(connection)
    differences = []
    existing = set(inspector.get_table_names())
    for table in metadata.sorted_tables:
        if table.name not in existing:
            differences.append(f"Tabela ausente: {table.name}")
            continue
        actual = {c["name"]: c for c in inspector.get_columns(table.name)}
        for name in actual.keys() - set(table.columns.keys()):
            differences.append(f"Coluna extra: {table.name}.{name}")
        for column in table.columns:
            label = f"{table.name}.{column.name}"
            if column.name not in actual:
                differences.append(f"Coluna ausente: {label}")
                continue
            found = actual[column.name]
            expected_default = column.server_default.arg if column.server_default else None
            checks = {
                "tipo": (normalize_type(found["type"], connection.dialect), normalize_type(column.type, connection.dialect)),
                "nulabilidade": (found["nullable"], column.nullable),
                "valor padrão": (normalize_default(found.get("default")), normalize_default(expected_default)),
            }
            if column.primary_key:
                checks["autoincremento"] = (found.get("autoincrement", False), True)
            for property_name, (observed, expected) in checks.items():
                if observed != expected:
                    differences.append(f"{label}: {property_name} diferente (banco={observed}, modelo={expected})")
        pk = inspector.get_pk_constraint(table.name).get("constrained_columns", [])
        if pk != [c.name for c in table.primary_key]:
            differences.append(f"{table.name}: chave primária diferente")
        expected_fks = {
            (fk.name, tuple(e.parent.name for e in fk.elements),
             tuple(e.column.table.name for e in fk.elements), tuple(e.column.name for e in fk.elements))
            for fk in table.foreign_key_constraints
        }
        observed_fks = set()
        for fk in inspector.get_foreign_keys(table.name):
            observed_fks.add((fk.get("name"), tuple(fk["constrained_columns"]),
                              tuple([fk["referred_table"]] * len(fk["referred_columns"])),
                              tuple(fk["referred_columns"])))
            if fk.get("referred_schema") not in (None, connection.engine.url.database):
                differences.append(f"{table.name}: chave estrangeira aponta para outro banco")
            for action in ("ondelete", "onupdate"):
                if fk.get("options", {}).get(action, "RESTRICT").upper() not in {"RESTRICT", "NO ACTION"}:
                    differences.append(f"{table.name}: {action} diferente em {fk.get('name')}")
        if observed_fks != expected_fks:
            differences.append(f"{table.name}: chaves estrangeiras diferentes (nome, colunas ou destino)")
    return differences


def main():
    engine = None
    try:
        from db import Base, build_database_url, engine
        import models  # Registra todos os modelos no metadata.

        url = build_database_url(require_credentials=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            selected = connection.scalar(text("SELECT DATABASE()"))
            if selected != url.database:
                print("Banco selecionado diferente de DB_NAME.", file=sys.stderr)
                return 1
            differences = compare_schema(connection, Base.metadata)
        if differences:
            print("Conexão estabelecida; divergências encontradas:")
            for difference in differences:
                print(f"- {difference}")
            return 1
        print(f"Conexão OK: {selected}. As oito tabelas correspondem aos modelos.")
        return 0
    except ValueError as error:
        print(f"Configuração inválida: {error}", file=sys.stderr)
        return 1
    except SQLAlchemyError as error:
        args = getattr(getattr(error, "orig", None), "args", ())
        code = args[0] if args else None
        if code in (1044, 1045, 1698):
            message = "Autenticação ou permissão negada. Confira DB_USER, DB_PASSWORD e permissões."
        elif code == 1049:
            message = "Banco inexistente. Confira DB_NAME; nenhuma tabela foi criada."
        elif code in (2002, 2003, 2005, 2006, 2013):
            message = "Falha de conexão. Confira o serviço MySQL, DB_HOST e DB_PORT."
        else:
            message = "Falha ao consultar o MySQL. Confira configuração e permissões de leitura."
        print(message, file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
