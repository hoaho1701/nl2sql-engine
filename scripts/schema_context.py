"""Generate schema DDL, business descriptions, and data-trap warnings for the RAG vector store."""


def generate_ddl(engine) -> list[str]:
    """Use sqlalchemy.inspect(engine) to generate CREATE TABLE statements, including real FKs."""
    raise NotImplementedError


TABLE_DESCRIPTIONS = {
    # TODO: business description per table, including real enum values
}

NON_UNIQUE_PARENT_KEYS = {
    # TODO: join columns known to be non-unique (fan-out risk)
}

NULLABLE_CHILD_KEYS = {
    # TODO: nullable FK columns (INNER JOIN silently drops rows)
}


def build_documentation_chunks() -> list[str]:
    """Flatten TABLE_DESCRIPTIONS / NON_UNIQUE_PARENT_KEYS / NULLABLE_CHILD_KEYS into
    independent text chunks, each embedded separately in the vector store."""
    raise NotImplementedError
