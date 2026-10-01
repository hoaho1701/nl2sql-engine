"""Tests for schema_context: DDL rendering helpers (no database needed) and doc chunks."""

import pytest
from sqlalchemy import types
from sqlalchemy.dialects import postgresql

from app import schema_context
from app.schema_context import (
    INNER_JOIN_ROW_LOSS,
    JOIN_PATHS,
    JOINS_WITHOUT_FK,
    NON_UNIQUE_PARENT_KEYS,
    NULLABLE_CHILD_KEYS,
    ONE_TO_MANY_JOINS,
    TABLE_DESCRIPTIONS,
    _column_ddl,
    _fk_ddl,
    _pk_ddl,
    _table_ddl,
    build_documentation_chunks,
    generate_ddl,
)

DIALECT = postgresql.dialect()


class FakeInspector:
    """Minimal stand-in for sqlalchemy.engine.reflection.Inspector."""

    def __init__(self, tables):
        self._tables = tables

    def get_sorted_table_and_fkc_names(self):
        # Mirrors the real shape: (table, fk constraints) pairs plus a trailing (None, [...]).
        return [(name, []) for name in self._tables] + [(None, [])]

    def get_columns(self, table):
        return self._tables[table]["columns"]

    def get_pk_constraint(self, table):
        return {"constrained_columns": self._tables[table].get("pk", [])}

    def get_foreign_keys(self, table):
        return self._tables[table].get("fks", [])


FAKE_TABLES = {
    "parents": {
        "columns": [
            {"name": "parent_id", "type": types.Text(), "nullable": False},
            {"name": "label", "type": types.Text(), "nullable": True},
        ],
        "pk": ["parent_id"],
    },
    "children": {
        "columns": [
            {"name": "parent_id", "type": types.Text(), "nullable": False},
            {"name": "line_no", "type": types.Integer(), "nullable": False},
            {"name": "amount", "type": types.Numeric(10, 2), "nullable": True},
        ],
        "pk": ["parent_id", "line_no"],
        "fks": [
            {
                "constrained_columns": ["parent_id"],
                "referred_table": "parents",
                "referred_columns": ["parent_id"],
            }
        ],
    },
    "loose": {
        "columns": [{"name": "value", "type": types.Float(), "nullable": True}],
    },
}


def test_column_ddl_not_null():
    column = {"name": "order_id", "type": types.Text(), "nullable": False}
    assert _column_ddl(column, DIALECT) == "order_id TEXT NOT NULL"


def test_column_ddl_nullable_has_no_not_null():
    column = {"name": "label", "type": types.Text(), "nullable": True}
    assert _column_ddl(column, DIALECT) == "label TEXT"


def test_column_ddl_renders_type_parameters():
    column = {"name": "price", "type": types.Numeric(10, 2), "nullable": False}
    assert _column_ddl(column, DIALECT) == "price NUMERIC(10, 2) NOT NULL"


def test_pk_ddl_composite():
    assert _pk_ddl({"constrained_columns": ["a", "b"]}) == "PRIMARY KEY (a, b)"


def test_pk_ddl_none_when_table_has_no_pk():
    assert _pk_ddl({"constrained_columns": []}) is None


def test_fk_ddl():
    fk = {
        "constrained_columns": ["order_id"],
        "referred_table": "orders",
        "referred_columns": ["order_id"],
    }
    assert _fk_ddl(fk) == "FOREIGN KEY (order_id) REFERENCES orders (order_id)"


def test_table_ddl_with_composite_pk_and_fk():
    ddl = _table_ddl(FakeInspector(FAKE_TABLES), "children", DIALECT)
    assert ddl == (
        "CREATE TABLE children (\n"
        "    parent_id TEXT NOT NULL,\n"
        "    line_no INTEGER NOT NULL,\n"
        "    amount NUMERIC(10, 2),\n"
        "    PRIMARY KEY (parent_id, line_no),\n"
        "    FOREIGN KEY (parent_id) REFERENCES parents (parent_id)\n"
        ")"
    )


def test_table_ddl_without_pk_or_fk_has_no_trailing_comma():
    ddl = _table_ddl(FakeInspector(FAKE_TABLES), "loose", DIALECT)
    assert ddl == "CREATE TABLE loose (\n    value FLOAT\n)"
    assert "PRIMARY KEY" not in ddl and "FOREIGN KEY" not in ddl


def test_generate_ddl_keeps_order_and_skips_none_entry(monkeypatch):
    class FakeEngine:
        dialect = DIALECT

    monkeypatch.setattr(
        schema_context, "inspect", lambda engine: FakeInspector(FAKE_TABLES)
    )
    ddl = generate_ddl(FakeEngine())
    assert len(ddl) == 3
    assert [statement.split()[2] for statement in ddl] == ["parents", "children", "loose"]


def test_one_chunk_per_documentation_entry():
    expected = (
        len(TABLE_DESCRIPTIONS)
        + len(NON_UNIQUE_PARENT_KEYS)
        + len(ONE_TO_MANY_JOINS)
        + len(JOINS_WITHOUT_FK)
        + len(NULLABLE_CHILD_KEYS)
        + len(INNER_JOIN_ROW_LOSS)
        + len(JOIN_PATHS)
    )
    assert len(build_documentation_chunks()) == expected


def test_chunks_are_nonempty_unique_strings():
    chunks = build_documentation_chunks()
    assert all(isinstance(chunk, str) and chunk.strip() for chunk in chunks)
    assert len(set(chunks)) == len(chunks)


@pytest.mark.parametrize("table", sorted(TABLE_DESCRIPTIONS))
def test_every_table_has_its_own_chunk(table):
    assert any(chunk.startswith(f"Table {table}:") for chunk in build_documentation_chunks())


def test_chunks_do_not_reference_python_variable_names():
    # Chunks are embedded on their own; a reference to a Python dict is meaningless to the LLM.
    names = [
        "NON_UNIQUE_PARENT_KEYS",
        "NULLABLE_CHILD_KEYS",
        "ONE_TO_MANY_JOINS",
        "JOINS_WITHOUT_FK",
        "INNER_JOIN_ROW_LOSS",
        "JOIN_PATHS",
        "TABLE_DESCRIPTIONS",
    ]
    for chunk in build_documentation_chunks():
        assert not any(name in chunk for name in names), chunk[:80]


def test_joins_without_fk_cover_the_three_missing_foreign_keys():
    joined = " ".join(JOINS_WITHOUT_FK)
    for fragment in (
        "customers.customer_zip_code_prefix",
        "sellers.seller_zip_code_prefix",
        "products.product_category_name",
    ):
        assert fragment in joined
