import io
import os
import unittest
from contextlib import redirect_stderr
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import URL
from sqlalchemy.dialects.mysql import dialect, INTEGER, VARCHAR
from sqlalchemy.orm import configure_mappers

import check_db
from db import Base, build_database_url
from models import User


class DatabaseTests(unittest.TestCase):
    def test_url_special_password_and_defaults(self):
        password = "p@ss:/?#% café"
        with patch.dict(os.environ, {"DB_USER": "test", "DB_PASSWORD": password}, clear=True):
            url = build_database_url(require_credentials=True)
        self.assertEqual(url.password, password)
        self.assertEqual((url.host, url.port, url.database), ("localhost", 3306, "fut_manager"))
        self.assertEqual(url.drivername, "mysql+pymysql")
        self.assertEqual(url.query["charset"], "utf8mb4")

    def test_invalid_configuration(self):
        for config in ({}, {"DB_PORT": "wrong"}, {"DB_PORT": "65536"}, {"DB_HOST": ""}, {"DB_NAME": ""}):
            with self.subTest(config=config), patch.dict(os.environ, config, clear=True):
                with self.assertRaises(ValueError):
                    build_database_url(require_credentials=True)

    def test_models_and_positions(self):
        configure_mappers()
        self.assertEqual(set(Base.metadata.tables), {
            "positions", "roles", "users", "teams", "team_players",
            "match_history", "match_teams", "player_match_ratings",
        })
        self.assertEqual(sum(len(t.foreign_key_constraints) for t in Base.metadata.tables.values()), 9)
        self.assertFalse(User.__table__.c.username.nullable)
        self.assertEqual(User.__table__.c.username.type.length, 100)
        self.assertTrue(User.__table__.c.rating.nullable)
        self.assertEqual(str(User.__table__.c.rating.type), "DOUBLE")
        self.assertEqual(str(User.__table__.c.created_at.server_default.arg), "CURRENT_TIMESTAMP")
        for name in ("current_position", "last_position"):
            relationship = User.__mapper__.relationships[name]
            self.assertEqual({c.name for c in relationship.local_columns}, {name + "_id"})
        for mapper in Base.registry.mappers:
            for relationship in mapper.relationships:
                self.assertNotIn("delete", relationship.cascade)
                self.assertNotIn("delete-orphan", relationship.cascade)

    def schema_fixture(self):
        from unittest.mock import Mock
        inspector = Mock()
        inspector.get_table_names.return_value = list(Base.metadata.tables)
        columns, fks = {}, {}
        for table in Base.metadata.tables.values():
            columns[table.name] = [dict(
                name=c.name, type=c.type, nullable=c.nullable,
                default=str(c.server_default.arg) if c.server_default else None,
                autoincrement=c.primary_key,
            ) for c in table.columns]
            fks[table.name] = [dict(
                name=fk.name, constrained_columns=[e.parent.name for e in fk.elements],
                referred_table=next(iter(fk.elements)).column.table.name,
                referred_columns=[e.column.name for e in fk.elements], options={},
            ) for fk in table.foreign_key_constraints]
        inspector.get_columns.side_effect = lambda name: columns[name]
        inspector.get_foreign_keys.side_effect = lambda name: fks[name]
        inspector.get_pk_constraint.return_value = {"constrained_columns": ["id"]}
        connection = SimpleNamespace(dialect=dialect(), engine=SimpleNamespace(url=URL.create("mysql+pymysql", database="fut_manager")))
        return inspector, columns, fks, connection

    def test_schema_match_and_drift(self):
        inspector, columns, fks, connection = self.schema_fixture()
        with patch("check_db.inspect", return_value=inspector):
            self.assertEqual(check_db.compare_schema(connection, Base.metadata), [])
            columns["users"][1]["type"] = VARCHAR(50)
            columns["users"][1]["nullable"] = True
            fks["users"][0]["referred_table"] = "wrong_table"
            differences = check_db.compare_schema(connection, Base.metadata)
        self.assertTrue(any("tipo diferente" in d for d in differences))
        self.assertTrue(any("nulabilidade diferente" in d for d in differences))
        self.assertTrue(any("chaves estrangeiras diferentes" in d for d in differences))

    def test_missing_tables(self):
        inspector, _, _, connection = self.schema_fixture()
        inspector.get_table_names.return_value = []
        with patch("check_db.inspect", return_value=inspector):
            self.assertEqual(len(check_db.compare_schema(connection, Base.metadata)), 8)

    def test_mysql_normalization(self):
        self.assertEqual(check_db.normalize_type(INTEGER(display_width=11), dialect()), "INTEGER")
        self.assertEqual(check_db.normalize_default("current_timestamp()"), "CURRENT_TIMESTAMP")
        self.assertEqual(check_db.normalize_default("'0'"), "0")

    def test_auth_error_does_not_expose_password(self):
        from sqlalchemy.exc import OperationalError
        import db
        error = OperationalError(None, None, Exception(1045, "secret-password"))
        output = io.StringIO()
        with patch.dict(os.environ, {"DB_USER": "test", "DB_PASSWORD": "secret-password"}), \
             patch.object(db.engine, "connect", side_effect=error), redirect_stderr(output):
            self.assertEqual(check_db.main(), 1)
        self.assertIn("Autenticação", output.getvalue())
        self.assertNotIn("secret-password", output.getvalue())


if __name__ == "__main__":
    unittest.main()
