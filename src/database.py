"""
=========================================================
PipingIQ Professional v6.0
database.py
SQLite schema, imports, backups, and lookup helpers.
=========================================================
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from config import (
    APP_NAME,
    AUTHOR,
    DATABASE_BACKUPS,
    PIPE_SPEC_DATABASE,
    SQLITE_DATABASE,
    VERSION,
)

APP_METADATA_TABLE = "app_metadata"
LIBRARIES_TABLE = "libraries"
IMPORT_BATCHES_TABLE = "import_batches"
PIPE_SPECS_TABLE = "pipe_specs"
SERVICE_ALIASES_TABLE = "service_aliases"
FIELD_ALIASES_TABLE = "field_aliases"
QUERY_HISTORY_TABLE = "query_history"
SAVED_ANSWERS_TABLE = "saved_answers"
STANDARDS_REFERENCES_TABLE = "standards_references"
DATABASE_AUDIT_LOG_TABLE = "database_audit_log"

# Backward-compatible runtime tables used by the current modules and tests.
PIPE_SPEC_TABLE = "pipe_specifications"
IMPORT_METADATA_TABLE = "import_metadata"

REQUIRED_COLUMNS = {"Spec", "Service", "Service_Abbv", "Size"}
RUNTIME_METADATA_COLUMNS = {
    "library_name",
    "library_type",
    "client_name",
    "project_name",
    "import_batch_id",
    "is_active",
}
CANONICAL_BASE_COLUMNS = {"Spec", "Service", "Service_Abbv", "Size"} | RUNTIME_METADATA_COLUMNS

FUTURE_LIBRARY_DEFAULTS: dict[str, Any] = {
    "library_name": "Standard Pipe Specifications",
    "library_type": "pipe_specification",
    "client_name": "",
    "project_name": "",
    "import_batch_id": "",
    "is_active": 1,
}

APP_METADATA_DEFAULTS: dict[str, tuple[str, str]] = {
    "app_name": (APP_NAME, "Application name"),
    "app_version": (VERSION, "Application version"),
    "app_author": (AUTHOR, "Application author"),
    "schema_version": ("1", "SQLite schema version"),
}

DEFAULT_MASTER_PATH = PIPE_SPEC_DATABASE
DEFAULT_SQLITE_PATH = SQLITE_DATABASE
DEFAULT_BACKUP_DIR = DATABASE_BACKUPS


class DatabaseError(Exception):
    """Base class for database errors."""


class DatabaseNotLoadedError(DatabaseError):
    """Raised when the database has not been loaded."""


class DatabaseValidationError(DatabaseError):
    """Raised when the database schema or contents are invalid."""


class ServiceNotFoundError(DatabaseError):
    """Raised when a requested service is not present in the database."""


class SpecificationNotFoundError(DatabaseError):
    """Raised when a requested specification is not present in the database."""


class QueryError(DatabaseError):
    """Raised when a query cannot be satisfied."""


@dataclass
class EngineeringSpecification:
    spec: str
    service: str
    service_abbv: str
    size_rule: str
    fields: dict[str, Any] = field(default_factory=dict)
    row_index: int | None = None

    @classmethod
    def from_series(cls, row: pd.Series) -> "EngineeringSpecification":
        row_idx: int | None = None
        if row.name is not None:
            try:
                row_idx = int(row.name)  # type: ignore[arg-type]
            except (ValueError, TypeError):
                row_idx = None

        return cls(
            spec=str(row["Spec"]).strip(),
            service=str(row["Service"]).strip(),
            service_abbv=str(row["Service_Abbv"]).strip().upper(),
            size_rule=str(row["Size"]).strip(),
            fields={
                str(key): value
                for key, value in row.items()
                if key not in {"Spec", "Service", "Service_Abbv", "Size"}
            },
            row_index=row_idx,
        )

    def as_dict(self) -> dict[str, Any]:
        result = {
            "Spec": self.spec,
            "Service": self.service,
            "Service_Abbv": self.service_abbv,
            "Size": self.size_rule,
        }
        result.update(self.fields)
        return result

    def get(self, key: str, default: Any = None) -> Any:
        return self.as_dict().get(key, default)


@dataclass
class QueryResult:
    success: bool
    specifications: list[EngineeringSpecification] = field(default_factory=list)
    message: str = ""
    service: str | None = None
    requested_size: float | None = None

    @property
    def single(self) -> bool:
        return self.success and len(self.specifications) == 1

    @property
    def ambiguous(self) -> bool:
        return len(self.specifications) > 1


@dataclass(frozen=True)
class ExcelImportProfile:
    dataset_name: str
    target_table: str
    required_columns: tuple[str, ...]
    importer: Callable[[sqlite3.Connection, pd.DataFrame, Mapping[str, Any]], int]
    default_sheet_name: str | int = 0


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _utcnow_text() -> str:
    return _utcnow().isoformat()


def normalize_column_name(column_name: Any) -> str:
    return re.sub(r"\s+", " ", str(column_name).replace("\n", " ")).strip()


def _normalize_search_text(text: Any) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(text).lower()))


def _slugify(*parts: Any) -> str:
    tokens = [_normalize_search_text(part).replace(" ", "-") for part in parts if str(part).strip()]
    slug = "-".join(token for token in tokens if token)
    return slug or "default-library"


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _to_serializable_value(value: Any) -> Any:
    if pd.isna(value):
        return ""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _build_import_batch_id(prefix: str = "pipe-spec") -> str:
    timestamp = _utcnow().strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{timestamp}"


def _build_library_id(
    library_name: str,
    library_type: str,
    client_name: str = "",
    project_name: str = "",
) -> str:
    return _slugify(library_type, library_name, client_name, project_name)


def connect_database(sqlite_path: Path | str = DEFAULT_SQLITE_PATH) -> sqlite3.Connection:
    target_path = Path(sqlite_path)
    _ensure_parent_dir(target_path)

    connection = sqlite3.connect(target_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    return connection


def _sqlite_object_exists(connection: sqlite3.Connection, object_type: str, object_name: str) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = ? AND name = ?
        LIMIT 1
        """,
        (object_type, object_name),
    ).fetchone()
    return row is not None


def _create_table_if_missing(connection: sqlite3.Connection, table_name: str, ddl: str) -> None:
    if _sqlite_object_exists(connection, "table", table_name):
        return
    connection.execute(ddl)


def _has_unique_index_conflicts(
    connection: sqlite3.Connection,
    table_name: str,
    key_expressions: Sequence[str],
) -> bool:
    row = connection.execute(
        f"""
        SELECT 1
        FROM {table_name}
        GROUP BY {", ".join(key_expressions)}
        HAVING COUNT(*) > 1
        LIMIT 1
        """
    ).fetchone()
    return row is not None


def _create_index_if_missing(
    connection: sqlite3.Connection,
    index_name: str,
    ddl: str,
    *,
    table_name: str,
    unique_key_expressions: Sequence[str] | None = None,
) -> None:
    if _sqlite_object_exists(connection, "index", index_name):
        return
    if unique_key_expressions and _has_unique_index_conflicts(connection, table_name, unique_key_expressions):
        return
    connection.execute(ddl)


def _create_schema(connection: sqlite3.Connection) -> None:
    _create_table_if_missing(
        connection,
        APP_METADATA_TABLE,
        f"""
        CREATE TABLE IF NOT EXISTS {APP_METADATA_TABLE} (
            meta_key TEXT PRIMARY KEY,
            meta_value TEXT NOT NULL,
            value_type TEXT NOT NULL DEFAULT 'text',
            description TEXT NOT NULL DEFAULT '',
            created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL
        )
        """,
    )
    _create_table_if_missing(
        connection,
        LIBRARIES_TABLE,
        f"""
        CREATE TABLE IF NOT EXISTS {LIBRARIES_TABLE} (
            library_id TEXT PRIMARY KEY,
            library_name TEXT NOT NULL,
            library_type TEXT NOT NULL,
            client_name TEXT NOT NULL DEFAULT '',
            project_name TEXT NOT NULL DEFAULT '',
            source_path TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL
        )
        """,
    )
    _create_table_if_missing(
        connection,
        IMPORT_BATCHES_TABLE,
        f"""
        CREATE TABLE IF NOT EXISTS {IMPORT_BATCHES_TABLE} (
            import_batch_id TEXT PRIMARY KEY,
            library_id TEXT NOT NULL,
            dataset_name TEXT NOT NULL,
            source_path TEXT NOT NULL,
            source_sha256 TEXT NOT NULL DEFAULT '',
            row_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'completed',
            notes TEXT NOT NULL DEFAULT '',
            imported_at_utc TEXT NOT NULL,
            FOREIGN KEY (library_id) REFERENCES {LIBRARIES_TABLE}(library_id)
        )
        """,
    )
    _create_table_if_missing(
        connection,
        PIPE_SPECS_TABLE,
        f"""
        CREATE TABLE IF NOT EXISTS {PIPE_SPECS_TABLE} (
            pipe_spec_id INTEGER PRIMARY KEY AUTOINCREMENT,
            library_id TEXT NOT NULL,
            import_batch_id TEXT NOT NULL,
            spec TEXT NOT NULL,
            service TEXT NOT NULL,
            service_abbv TEXT NOT NULL,
            size_rule TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{{}}',
            source_row_number INTEGER,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            created_at_utc TEXT NOT NULL,
            FOREIGN KEY (library_id) REFERENCES {LIBRARIES_TABLE}(library_id),
            FOREIGN KEY (import_batch_id) REFERENCES {IMPORT_BATCHES_TABLE}(import_batch_id)
        )
        """,
    )
    _create_table_if_missing(
        connection,
        SERVICE_ALIASES_TABLE,
        f"""
        CREATE TABLE IF NOT EXISTS {SERVICE_ALIASES_TABLE} (
            service_alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT NOT NULL,
            service_abbv TEXT NOT NULL DEFAULT '',
            alias TEXT NOT NULL,
            alias_normalized TEXT NOT NULL,
            library_id TEXT,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            created_at_utc TEXT NOT NULL,
            FOREIGN KEY (library_id) REFERENCES {LIBRARIES_TABLE}(library_id)
        )
        """,
    )
    _create_table_if_missing(
        connection,
        FIELD_ALIASES_TABLE,
        f"""
        CREATE TABLE IF NOT EXISTS {FIELD_ALIASES_TABLE} (
            field_alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
            field_name TEXT NOT NULL,
            alias TEXT NOT NULL,
            alias_normalized TEXT NOT NULL,
            library_id TEXT,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            created_at_utc TEXT NOT NULL,
            FOREIGN KEY (library_id) REFERENCES {LIBRARIES_TABLE}(library_id)
        )
        """,
    )
    _create_table_if_missing(
        connection,
        QUERY_HISTORY_TABLE,
        f"""
        CREATE TABLE IF NOT EXISTS {QUERY_HISTORY_TABLE} (
            query_id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            normalized_question TEXT NOT NULL DEFAULT '',
            parsed_service TEXT NOT NULL DEFAULT '',
            parsed_field TEXT NOT NULL DEFAULT '',
            requested_size REAL,
            result_count INTEGER NOT NULL DEFAULT 0,
            success INTEGER NOT NULL DEFAULT 0 CHECK (success IN (0, 1)),
            response_summary TEXT NOT NULL DEFAULT '',
            created_at_utc TEXT NOT NULL
        )
        """,
    )
    _create_table_if_missing(
        connection,
        SAVED_ANSWERS_TABLE,
        f"""
        CREATE TABLE IF NOT EXISTS {SAVED_ANSWERS_TABLE} (
            answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL DEFAULT '',
            answer_text TEXT NOT NULL,
            service TEXT NOT NULL DEFAULT '',
            field_name TEXT NOT NULL DEFAULT '',
            spec TEXT NOT NULL DEFAULT '',
            source_reference TEXT NOT NULL DEFAULT '',
            tags TEXT NOT NULL DEFAULT '',
            created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL
        )
        """,
    )
    _create_table_if_missing(
        connection,
        STANDARDS_REFERENCES_TABLE,
        f"""
        CREATE TABLE IF NOT EXISTS {STANDARDS_REFERENCES_TABLE} (
            reference_id INTEGER PRIMARY KEY AUTOINCREMENT,
            standard_name TEXT NOT NULL,
            reference_key TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            citation_text TEXT NOT NULL DEFAULT '',
            source_path TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_at_utc TEXT NOT NULL
        )
        """,
    )
    _create_table_if_missing(
        connection,
        DATABASE_AUDIT_LOG_TABLE,
        f"""
        CREATE TABLE IF NOT EXISTS {DATABASE_AUDIT_LOG_TABLE} (
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL DEFAULT '',
            details_json TEXT NOT NULL DEFAULT '{{}}',
            created_at_utc TEXT NOT NULL
        )
        """,
    )
    _create_table_if_missing(
        connection,
        IMPORT_METADATA_TABLE,
        f"""
        CREATE TABLE IF NOT EXISTS {IMPORT_METADATA_TABLE} (
            import_batch_id TEXT PRIMARY KEY,
            table_name TEXT NOT NULL,
            source_path TEXT NOT NULL,
            row_count INTEGER NOT NULL,
            library_name TEXT NOT NULL,
            library_type TEXT NOT NULL,
            imported_at_utc TEXT NOT NULL
        )
        """,
    )
    _create_table_if_missing(
        connection,
        PIPE_SPEC_TABLE,
        f"""
        CREATE TABLE IF NOT EXISTS {PIPE_SPEC_TABLE} (
            "Spec" TEXT NOT NULL DEFAULT '',
            "Service" TEXT NOT NULL DEFAULT '',
            "Service_Abbv" TEXT NOT NULL DEFAULT '',
            "Size" TEXT NOT NULL DEFAULT '',
            library_name TEXT NOT NULL DEFAULT '',
            library_type TEXT NOT NULL DEFAULT '',
            client_name TEXT NOT NULL DEFAULT '',
            project_name TEXT NOT NULL DEFAULT '',
            import_batch_id TEXT NOT NULL DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 1
        )
        """,
    )


def _create_indexes(connection: sqlite3.Connection) -> None:
    _create_index_if_missing(
        connection,
        f"idx_{APP_METADATA_TABLE}_meta_key",
        f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{APP_METADATA_TABLE}_meta_key ON {APP_METADATA_TABLE} (meta_key)",
        table_name=APP_METADATA_TABLE,
        unique_key_expressions=("meta_key",),
    )
    _create_index_if_missing(
        connection,
        f"idx_{LIBRARIES_TABLE}_identity",
        f"""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_{LIBRARIES_TABLE}_identity
        ON {LIBRARIES_TABLE} (library_name, library_type, client_name, project_name)
        """,
        table_name=LIBRARIES_TABLE,
        unique_key_expressions=("library_name", "library_type", "client_name", "project_name"),
    )
    _create_index_if_missing(
        connection,
        f"idx_{LIBRARIES_TABLE}_active",
        f"CREATE INDEX IF NOT EXISTS idx_{LIBRARIES_TABLE}_active ON {LIBRARIES_TABLE} (is_active, library_name)",
        table_name=LIBRARIES_TABLE,
    )
    _create_index_if_missing(
        connection,
        f"idx_{IMPORT_BATCHES_TABLE}_library",
        f"CREATE INDEX IF NOT EXISTS idx_{IMPORT_BATCHES_TABLE}_library ON {IMPORT_BATCHES_TABLE} (library_id, imported_at_utc)",
        table_name=IMPORT_BATCHES_TABLE,
    )
    _create_index_if_missing(
        connection,
        f"idx_{PIPE_SPECS_TABLE}_spec",
        f"CREATE INDEX IF NOT EXISTS idx_{PIPE_SPECS_TABLE}_spec ON {PIPE_SPECS_TABLE} (spec)",
        table_name=PIPE_SPECS_TABLE,
    )
    _create_index_if_missing(
        connection,
        f"idx_{PIPE_SPECS_TABLE}_service",
        f"CREATE INDEX IF NOT EXISTS idx_{PIPE_SPECS_TABLE}_service ON {PIPE_SPECS_TABLE} (service_abbv, service)",
        table_name=PIPE_SPECS_TABLE,
    )
    _create_index_if_missing(
        connection,
        f"idx_{PIPE_SPECS_TABLE}_library_active",
        f"CREATE INDEX IF NOT EXISTS idx_{PIPE_SPECS_TABLE}_library_active ON {PIPE_SPECS_TABLE} (library_id, is_active)",
        table_name=PIPE_SPECS_TABLE,
    )
    _create_index_if_missing(
        connection,
        f"idx_{SERVICE_ALIASES_TABLE}_alias",
        f"""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_{SERVICE_ALIASES_TABLE}_alias
        ON {SERVICE_ALIASES_TABLE} (alias_normalized, COALESCE(library_id, ''))
        """,
        table_name=SERVICE_ALIASES_TABLE,
        unique_key_expressions=("alias_normalized", "COALESCE(library_id, '')"),
    )
    _create_index_if_missing(
        connection,
        f"idx_{FIELD_ALIASES_TABLE}_alias",
        f"""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_{FIELD_ALIASES_TABLE}_alias
        ON {FIELD_ALIASES_TABLE} (alias_normalized, COALESCE(library_id, ''))
        """,
        table_name=FIELD_ALIASES_TABLE,
        unique_key_expressions=("alias_normalized", "COALESCE(library_id, '')"),
    )
    _create_index_if_missing(
        connection,
        f"idx_{QUERY_HISTORY_TABLE}_created",
        f"CREATE INDEX IF NOT EXISTS idx_{QUERY_HISTORY_TABLE}_created ON {QUERY_HISTORY_TABLE} (created_at_utc)",
        table_name=QUERY_HISTORY_TABLE,
    )
    _create_index_if_missing(
        connection,
        f"idx_{SAVED_ANSWERS_TABLE}_created",
        f"CREATE INDEX IF NOT EXISTS idx_{SAVED_ANSWERS_TABLE}_created ON {SAVED_ANSWERS_TABLE} (created_at_utc)",
        table_name=SAVED_ANSWERS_TABLE,
    )
    _create_index_if_missing(
        connection,
        f"idx_{STANDARDS_REFERENCES_TABLE}_lookup",
        f"""
        CREATE INDEX IF NOT EXISTS idx_{STANDARDS_REFERENCES_TABLE}_lookup
        ON {STANDARDS_REFERENCES_TABLE} (standard_name, reference_key)
        """,
        table_name=STANDARDS_REFERENCES_TABLE,
    )
    _create_index_if_missing(
        connection,
        f"idx_{DATABASE_AUDIT_LOG_TABLE}_created",
        f"CREATE INDEX IF NOT EXISTS idx_{DATABASE_AUDIT_LOG_TABLE}_created ON {DATABASE_AUDIT_LOG_TABLE} (created_at_utc)",
        table_name=DATABASE_AUDIT_LOG_TABLE,
    )
    _create_index_if_missing(
        connection,
        f"idx_{IMPORT_METADATA_TABLE}_table",
        f"CREATE INDEX IF NOT EXISTS idx_{IMPORT_METADATA_TABLE}_table ON {IMPORT_METADATA_TABLE} (table_name, imported_at_utc)",
        table_name=IMPORT_METADATA_TABLE,
    )
    _create_index_if_missing(
        connection,
        f"idx_{PIPE_SPEC_TABLE}_spec",
        f'CREATE INDEX IF NOT EXISTS idx_{PIPE_SPEC_TABLE}_spec ON {PIPE_SPEC_TABLE} ("Spec")',
        table_name=PIPE_SPEC_TABLE,
    )
    _create_index_if_missing(
        connection,
        f"idx_{PIPE_SPEC_TABLE}_service",
        f'CREATE INDEX IF NOT EXISTS idx_{PIPE_SPEC_TABLE}_service ON {PIPE_SPEC_TABLE} ("Service")',
        table_name=PIPE_SPEC_TABLE,
    )
    _create_index_if_missing(
        connection,
        f"idx_{PIPE_SPEC_TABLE}_service_abbv",
        f'CREATE INDEX IF NOT EXISTS idx_{PIPE_SPEC_TABLE}_service_abbv ON {PIPE_SPEC_TABLE} ("Service_Abbv")',
        table_name=PIPE_SPEC_TABLE,
    )
    _create_index_if_missing(
        connection,
        f"idx_{PIPE_SPEC_TABLE}_active_library",
        f'CREATE INDEX IF NOT EXISTS idx_{PIPE_SPEC_TABLE}_active_library ON {PIPE_SPEC_TABLE} ("is_active", "library_name")',
        table_name=PIPE_SPEC_TABLE,
    )


def _seed_app_metadata(connection: sqlite3.Connection) -> None:
    for meta_key, (meta_value, description) in APP_METADATA_DEFAULTS.items():
        _upsert_app_metadata_value(
            connection,
            key=meta_key,
            value=meta_value,
            value_type="text",
            description=description,
        )


def _upsert_app_metadata_value(
    connection: sqlite3.Connection,
    *,
    key: str,
    value: Any,
    value_type: str,
    description: str,
) -> None:
    now_text = _utcnow_text()
    connection.execute(
        f"""
        INSERT INTO {APP_METADATA_TABLE} (
            meta_key,
            meta_value,
            value_type,
            description,
            created_at_utc,
            updated_at_utc
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(meta_key) DO UPDATE SET
            meta_value = excluded.meta_value,
            value_type = excluded.value_type,
            description = excluded.description,
            updated_at_utc = excluded.updated_at_utc
        """,
        (str(key).strip(), str(value), value_type, description, now_text, now_text),
    )


def create_schema(sqlite_path: Path | str = DEFAULT_SQLITE_PATH) -> Path:
    target_path = Path(sqlite_path)
    _ensure_parent_dir(target_path)

    connection = connect_database(target_path)
    try:
        _create_schema(connection)
        _create_indexes(connection)
        _seed_app_metadata(connection)
        connection.commit()
    finally:
        connection.close()

    return target_path


def get_app_metadata(sqlite_path: Path | str = DEFAULT_SQLITE_PATH) -> dict[str, str]:
    create_schema(sqlite_path)
    connection = connect_database(sqlite_path)
    try:
        rows = connection.execute(
            f"SELECT meta_key, meta_value FROM {APP_METADATA_TABLE} ORDER BY meta_key"
        ).fetchall()
        return {str(row["meta_key"]): str(row["meta_value"]) for row in rows}
    finally:
        connection.close()


def set_app_metadata(
    key: str,
    value: Any,
    *,
    sqlite_path: Path | str = DEFAULT_SQLITE_PATH,
    value_type: str = "text",
    description: str = "",
) -> None:
    if not str(key).strip():
        raise DatabaseValidationError("Metadata key cannot be blank.")

    create_schema(sqlite_path)
    connection = connect_database(sqlite_path)
    try:
        _upsert_app_metadata_value(
            connection,
            key=str(key).strip(),
            value=str(value),
            value_type=value_type,
            description=description,
        )
        _record_audit_event(
            connection,
            action="set_app_metadata",
            entity_type="app_metadata",
            entity_id=str(key).strip(),
            details={"value_type": value_type},
        )
        connection.commit()
    finally:
        connection.close()


def load_pipe_spec_dataframe(path: Path | str) -> pd.DataFrame:
    source_path = Path(path)
    if not source_path.exists():
        raise FileNotFoundError(f"Pipe specification workbook not found: {source_path}")

    raw_dataframe = pd.read_excel(
        source_path,
        sheet_name="Master_Spec_Template_Full",
        header=None,
        dtype=object,
        keep_default_na=False,
        na_filter=False,
    ).fillna("")

    header_index: int | None = None
    for index, row in raw_dataframe.iterrows():
        normalized_values = {normalize_column_name(value) for value in row.tolist()}
        if REQUIRED_COLUMNS.issubset(normalized_values):
            header_index = int(index)
            break

    if header_index is None:
        dataframe = pd.read_excel(source_path, sheet_name="Master_Spec_Template_Full").fillna("")
        dataframe.columns = [normalize_column_name(column) for column in dataframe.columns]
    else:
        column_counts: dict[str, int] = {}
        columns: list[str] = []
        for position, column in enumerate(raw_dataframe.iloc[header_index].tolist()):
            normalized_column = normalize_column_name(column) or f"Unnamed: {position}"
            column_count = column_counts.get(normalized_column, 0)
            column_counts[normalized_column] = column_count + 1
            columns.append(
                normalized_column if column_count == 0 else f"{normalized_column}.{column_count}"
            )

        dataframe = raw_dataframe.iloc[header_index + 1 :].copy()
        dataframe.columns = columns
        dataframe.columns = [normalize_column_name(column) for column in dataframe.columns]

    if REQUIRED_COLUMNS.issubset(dataframe.columns):
        populated_spec_rows = dataframe[list(REQUIRED_COLUMNS)].apply(
            lambda row: any(str(value).strip() for value in row),
            axis=1,
        )
        dataframe = dataframe.loc[populated_spec_rows]
        repeated_headers = (
            dataframe["Spec"].astype(str).str.strip().str.upper().eq("SPEC")
            & dataframe["Service"].astype(str).str.strip().str.upper().eq("SERVICE")
            & dataframe["Size"].astype(str).str.strip().str.upper().eq("SIZE")
        )
        if repeated_headers.any():
            dataframe = dataframe.loc[~repeated_headers].reset_index(drop=True)

    return dataframe


def prepare_pipe_spec_dataframe(
    dataframe: pd.DataFrame,
    *,
    library_name: str = str(FUTURE_LIBRARY_DEFAULTS["library_name"]),
    library_type: str = str(FUTURE_LIBRARY_DEFAULTS["library_type"]),
    client_name: str = str(FUTURE_LIBRARY_DEFAULTS["client_name"]),
    project_name: str = str(FUTURE_LIBRARY_DEFAULTS["project_name"]),
    import_batch_id: str | None = None,
    is_active: int = int(FUTURE_LIBRARY_DEFAULTS["is_active"]),
) -> pd.DataFrame:
    runtime_df = dataframe.copy()
    runtime_df.columns = [normalize_column_name(column) for column in runtime_df.columns]
    _validate_database(runtime_df)
    _normalize_dataframe(runtime_df)

    batch_id = import_batch_id or _build_import_batch_id()
    runtime_df["library_name"] = library_name
    runtime_df["library_type"] = library_type
    runtime_df["client_name"] = client_name
    runtime_df["project_name"] = project_name
    runtime_df["import_batch_id"] = batch_id
    runtime_df["is_active"] = int(is_active)
    return runtime_df


def _upsert_library(
    connection: sqlite3.Connection,
    *,
    library_name: str,
    library_type: str,
    client_name: str,
    project_name: str,
    source_path: Path | str,
    is_active: int,
) -> str:
    library_id = _build_library_id(library_name, library_type, client_name, project_name)
    now_text = _utcnow_text()
    connection.execute(
        f"""
        INSERT INTO {LIBRARIES_TABLE} (
            library_id,
            library_name,
            library_type,
            client_name,
            project_name,
            source_path,
            is_active,
            created_at_utc,
            updated_at_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(library_id) DO UPDATE SET
            library_name = excluded.library_name,
            library_type = excluded.library_type,
            client_name = excluded.client_name,
            project_name = excluded.project_name,
            source_path = excluded.source_path,
            is_active = excluded.is_active,
            updated_at_utc = excluded.updated_at_utc
        """,
        (
            library_id,
            library_name,
            library_type,
            client_name,
            project_name,
            str(source_path),
            int(is_active),
            now_text,
            now_text,
        ),
    )
    return library_id


def _write_import_batch(
    connection: sqlite3.Connection,
    *,
    import_batch_id: str,
    library_id: str,
    dataset_name: str,
    source_path: Path | str,
    row_count: int,
    source_sha256: str,
    notes: str = "",
) -> None:
    connection.execute(
        f"""
        INSERT OR REPLACE INTO {IMPORT_BATCHES_TABLE} (
            import_batch_id,
            library_id,
            dataset_name,
            source_path,
            source_sha256,
            row_count,
            status,
            notes,
            imported_at_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            import_batch_id,
            library_id,
            dataset_name,
            str(source_path),
            source_sha256,
            row_count,
            "completed",
            notes,
            _utcnow_text(),
        ),
    )


def _write_import_metadata(
    connection: sqlite3.Connection,
    *,
    source_path: Path,
    row_count: int,
    import_batch_id: str,
    library_name: str,
    library_type: str,
) -> None:
    connection.execute(
        f"""
        INSERT OR REPLACE INTO {IMPORT_METADATA_TABLE} (
            import_batch_id,
            table_name,
            source_path,
            row_count,
            library_name,
            library_type,
            imported_at_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            import_batch_id,
            PIPE_SPEC_TABLE,
            str(source_path),
            row_count,
            library_name,
            library_type,
            _utcnow_text(),
        ),
    )


def _replace_runtime_pipe_specifications(
    connection: sqlite3.Connection,
    runtime_df: pd.DataFrame,
) -> None:
    runtime_df.to_sql(PIPE_SPEC_TABLE, connection, if_exists="replace", index=False)


def _replace_canonical_pipe_specs(
    connection: sqlite3.Connection,
    runtime_df: pd.DataFrame,
    *,
    library_id: str,
    import_batch_id: str,
) -> None:
    connection.execute(f"DELETE FROM {PIPE_SPECS_TABLE} WHERE library_id = ?", (library_id,))

    now_text = _utcnow_text()
    rows_to_insert: list[tuple[Any, ...]] = []
    for row_number, (_, row) in enumerate(runtime_df.iterrows(), start=1):
        payload = {
            column: _to_serializable_value(row[column])
            for column in runtime_df.columns
            if column not in CANONICAL_BASE_COLUMNS
        }
        rows_to_insert.append(
            (
                library_id,
                import_batch_id,
                str(row["Spec"]).strip(),
                str(row["Service"]).strip(),
                str(row["Service_Abbv"]).strip().upper(),
                str(row["Size"]).strip(),
                _json_dumps(payload),
                row_number,
                int(row["is_active"]),
                now_text,
            )
        )

    if rows_to_insert:
        connection.executemany(
            f"""
            INSERT INTO {PIPE_SPECS_TABLE} (
                library_id,
                import_batch_id,
                spec,
                service,
                service_abbv,
                size_rule,
                payload_json,
                source_row_number,
                is_active,
                created_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows_to_insert,
        )


def _refresh_alias_tables(
    connection: sqlite3.Connection,
    runtime_df: pd.DataFrame,
    *,
    library_id: str,
) -> None:
    now_text = _utcnow_text()
    connection.execute(f"DELETE FROM {SERVICE_ALIASES_TABLE} WHERE library_id = ?", (library_id,))
    connection.execute(f"DELETE FROM {FIELD_ALIASES_TABLE} WHERE library_id = ?", (library_id,))

    service_alias_rows_by_key: dict[tuple[str, str], tuple[str, str, str, str, str, int, str]] = {}

    def add_service_alias_row(service_name: str, service_abbv: str, alias: str) -> None:
        alias_normalized = _normalize_search_text(alias)
        alias_key = (alias_normalized, library_id)
        if alias_key in service_alias_rows_by_key:
            return
        service_alias_rows_by_key[alias_key] = (
            service_name,
            service_abbv,
            alias,
            alias_normalized,
            library_id,
            1,
            now_text,
        )

    for _, row in runtime_df[["Service", "Service_Abbv"]].fillna("").iterrows():
        service_name = str(row["Service"]).strip()
        service_abbv = str(row["Service_Abbv"]).strip().upper()
        if service_name:
            add_service_alias_row(service_name, service_abbv, service_name)
        if service_abbv:
            add_service_alias_row(service_name, service_abbv, service_abbv)

    service_alias_rows = list(service_alias_rows_by_key.values())

    if service_alias_rows:
        connection.executemany(
            f"""
            INSERT INTO {SERVICE_ALIASES_TABLE} (
                service_name,
                service_abbv,
                alias,
                alias_normalized,
                library_id,
                is_active,
                created_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            service_alias_rows,
        )

    field_alias_rows: set[tuple[str, str, str, str, int, str]] = set()
    for column in runtime_df.columns:
        if column in REQUIRED_COLUMNS or column in RUNTIME_METADATA_COLUMNS:
            continue
        field_alias_rows.add(
            (
                str(column),
                str(column),
                _normalize_search_text(column),
                library_id,
                1,
                now_text,
            )
        )

    if field_alias_rows:
        connection.executemany(
            f"""
            INSERT INTO {FIELD_ALIASES_TABLE} (
                field_name,
                alias,
                alias_normalized,
                library_id,
                is_active,
                created_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            sorted(field_alias_rows),
        )


def _record_audit_event(
    connection: sqlite3.Connection,
    *,
    action: str,
    entity_type: str,
    entity_id: str = "",
    details: Mapping[str, Any] | None = None,
) -> None:
    connection.execute(
        f"""
        INSERT INTO {DATABASE_AUDIT_LOG_TABLE} (
            action,
            entity_type,
            entity_id,
            details_json,
            created_at_utc
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            action,
            entity_type,
            entity_id,
            _json_dumps(dict(details or {})),
            _utcnow_text(),
        ),
    )


def record_audit_event(
    action: str,
    entity_type: str,
    *,
    entity_id: str = "",
    details: Mapping[str, Any] | None = None,
    sqlite_path: Path | str = DEFAULT_SQLITE_PATH,
) -> None:
    create_schema(sqlite_path)
    connection = connect_database(sqlite_path)
    try:
        _record_audit_event(
            connection,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
        connection.commit()
    finally:
        connection.close()


def backup_database(
    sqlite_path: Path | str = DEFAULT_SQLITE_PATH,
    *,
    backup_dir: Path | str = DEFAULT_BACKUP_DIR,
) -> Path:
    source_path = Path(sqlite_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Runtime SQLite database not found: {source_path}")

    destination_dir = Path(backup_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    timestamp = _utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup_path = destination_dir / f"{source_path.stem}_{timestamp}{source_path.suffix or '.db'}"

    source_connection = connect_database(source_path)
    backup_connection = connect_database(backup_path)
    try:
        source_connection.backup(backup_connection)
        backup_connection.commit()
    finally:
        backup_connection.close()
        source_connection.close()

    return backup_path


def build_sqlite_database(
    sqlite_path: Path | str = DEFAULT_SQLITE_PATH,
    pipe_spec_path: Path | str = DEFAULT_MASTER_PATH,
    *,
    library_name: str = str(FUTURE_LIBRARY_DEFAULTS["library_name"]),
    library_type: str = str(FUTURE_LIBRARY_DEFAULTS["library_type"]),
    client_name: str = str(FUTURE_LIBRARY_DEFAULTS["client_name"]),
    project_name: str = str(FUTURE_LIBRARY_DEFAULTS["project_name"]),
    is_active: int = int(FUTURE_LIBRARY_DEFAULTS["is_active"]),
    backup_existing: bool = True,
    backup_dir: Path | str = DEFAULT_BACKUP_DIR,
) -> Path:
    target_path = Path(sqlite_path)
    master_path = Path(pipe_spec_path)
    _ensure_parent_dir(target_path)

    backup_path: Path | None = None
    if backup_existing and target_path.exists() and target_path.stat().st_size > 0:
        backup_path = backup_database(target_path, backup_dir=backup_dir)

    create_schema(target_path)
    master_df = load_pipe_spec_dataframe(master_path)
    runtime_df = prepare_pipe_spec_dataframe(
        master_df,
        library_name=library_name,
        library_type=library_type,
        client_name=client_name,
        project_name=project_name,
        is_active=is_active,
    )
    import_batch_id = (
        str(runtime_df["import_batch_id"].iloc[0])
        if not runtime_df.empty
        else _build_import_batch_id()
    )

    connection = connect_database(target_path)
    try:
        library_id = _upsert_library(
            connection,
            library_name=library_name,
            library_type=library_type,
            client_name=client_name,
            project_name=project_name,
            source_path=master_path,
            is_active=is_active,
        )
        _write_import_batch(
            connection,
            import_batch_id=import_batch_id,
            library_id=library_id,
            dataset_name="pipe_specs",
            source_path=master_path,
            row_count=len(runtime_df),
            source_sha256=_sha256_file(master_path),
        )
        _replace_runtime_pipe_specifications(connection, runtime_df)
        _replace_canonical_pipe_specs(
            connection,
            runtime_df,
            library_id=library_id,
            import_batch_id=import_batch_id,
        )
        _write_import_metadata(
            connection,
            source_path=master_path,
            row_count=len(runtime_df),
            import_batch_id=import_batch_id,
            library_name=library_name,
            library_type=library_type,
        )
        _refresh_alias_tables(connection, runtime_df, library_id=library_id)
        _upsert_app_metadata_value(
            connection,
            key="last_pipe_spec_import_batch_id",
            value=import_batch_id,
            value_type="text",
            description="Most recent pipe specification import batch",
        )
        _upsert_app_metadata_value(
            connection,
            key="last_pipe_spec_source_path",
            value=str(master_path),
            value_type="text",
            description="Source workbook for the most recent pipe specification import",
        )
        _record_audit_event(
            connection,
            action="build_sqlite_database",
            entity_type="pipe_specs",
            entity_id=import_batch_id,
            details={
                "library_id": library_id,
                "library_name": library_name,
                "row_count": len(runtime_df),
                "source_path": str(master_path),
                "backup_path": str(backup_path) if backup_path is not None else "",
            },
        )
        _create_indexes(connection)
        connection.commit()
    finally:
        connection.close()

    return target_path


def load_runtime_dataframe(sqlite_path: Path | str = DEFAULT_SQLITE_PATH) -> pd.DataFrame:
    runtime_path = Path(sqlite_path)
    if not runtime_path.exists():
        raise FileNotFoundError(f"Runtime SQLite database not found: {runtime_path}")

    connection = connect_database(runtime_path)
    try:
        dataframe = pd.read_sql_query(
            f'SELECT * FROM {PIPE_SPEC_TABLE} WHERE "is_active" = 1 ORDER BY rowid',
            connection,
        ).fillna("")
    except sqlite3.DatabaseError as exc:
        raise DatabaseValidationError(f"Unable to load runtime table '{PIPE_SPEC_TABLE}': {exc}") from exc
    finally:
        connection.close()

    dataframe.columns = [normalize_column_name(column) for column in dataframe.columns]
    _validate_database(dataframe)
    _normalize_dataframe(dataframe)
    if "is_active" in dataframe.columns:
        dataframe["is_active"] = dataframe["is_active"].astype(int)
    return dataframe


def _validate_database(dataframe: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in dataframe.columns]
    if missing:
        raise DatabaseValidationError(f"Missing required columns: {missing}")

    invalid_rules: list[tuple[Any, Any]] = []
    for index, rule in dataframe["Size"].items():
        if _is_valid_size_rule(rule):
            continue
        try:
            row_index: Any = int(index)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            row_index = index
        invalid_rules.append((row_index, rule))

    if invalid_rules:
        raise DatabaseValidationError(f"Invalid size rules found: {invalid_rules[:10]}")


def _normalize_dataframe(dataframe: pd.DataFrame) -> None:
    for column in dataframe.columns:
        if dataframe[column].dtype == object:
            dataframe[column] = dataframe[column].astype(str).str.strip()

    dataframe["Service_Abbv"] = dataframe["Service_Abbv"].astype(str).str.upper().str.strip()
    dataframe["Service"] = dataframe["Service"].astype(str).str.strip()
    dataframe["Spec"] = dataframe["Spec"].astype(str).str.strip()
    dataframe["Size"] = dataframe["Size"].astype(str).str.strip()


def _normalize_size_rule(rule: Any) -> str:
    normalized = str(rule).strip().replace('"', "").replace("”", "").upper()
    normalized = re.sub(r"<\s*=", "<=", normalized)
    normalized = re.sub(r">\s*=", ">=", normalized)
    return normalized.strip()


def _is_valid_size_rule(rule: Any) -> bool:
    normalized = _normalize_size_rule(rule)
    if normalized == "" or normalized == "ALL":
        return True

    comp_match = re.match(r"^(<=|>=|<|>)\s*(.+)$", normalized)
    if comp_match:
        _, rhs = comp_match.groups()
        try:
            _parse_numeric_size(rhs)
            return True
        except ValueError:
            return False

    range_match = re.match(r"^(\S+)\s*-\s*(\S+)$", normalized) or re.match(
        r"^(\S+)\s+TO\s+(\S+)$",
        normalized,
    )
    if range_match:
        start_value, end_value = range_match.groups()
        try:
            _parse_numeric_size(start_value)
            _parse_numeric_size(end_value)
            return True
        except ValueError:
            return False

    try:
        _parse_numeric_size(normalized)
        return True
    except ValueError:
        return False


def size_matches(rule: Any, requested_size: float | None) -> bool:
    if requested_size is None:
        return True

    normalized = _normalize_size_rule(rule)
    if normalized == "" or normalized == "ALL":
        return True

    comp_match = re.match(r"^(<=|>=|<|>)\s*(.+)$", normalized)
    if comp_match:
        comparator, rhs = comp_match.groups()
        try:
            limit = _parse_numeric_size(rhs)
        except ValueError:
            return False

        if comparator == "<=":
            return requested_size <= limit
        if comparator == ">=":
            return requested_size >= limit
        if comparator == "<":
            return requested_size < limit
        return requested_size > limit

    range_match = re.match(r"^(\S+)\s*-\s*(\S+)$", normalized) or re.match(
        r"^(\S+)\s+TO\s+(\S+)$",
        normalized,
    )
    if range_match:
        start_value, end_value = range_match.groups()
        try:
            lower = _parse_numeric_size(start_value)
            upper = _parse_numeric_size(end_value)
        except ValueError:
            return False
        return lower <= requested_size <= upper

    try:
        return requested_size == _parse_numeric_size(normalized)
    except ValueError:
        return False


def _parse_numeric_size(text: str) -> float:
    value = str(text).strip().strip('"').strip()

    try:
        return float(value)
    except ValueError:
        pass

    mixed_number = re.match(r"^(\d+)\s*[- ]\s*(\d+)/(\d+)$", value)
    if mixed_number:
        whole, numerator, denominator = mixed_number.groups()
        return float(whole) + float(numerator) / float(denominator)

    fraction = re.match(r"^(\d+)/(\d+)$", value)
    if fraction:
        numerator, denominator = fraction.groups()
        return float(numerator) / float(denominator)

    raise ValueError(f"Cannot parse numeric size from '{text}'")


def list_libraries(
    sqlite_path: Path | str = DEFAULT_SQLITE_PATH,
    *,
    active_only: bool = False,
) -> list[dict[str, Any]]:
    create_schema(sqlite_path)
    sql = f"""
        SELECT
            library_id,
            library_name,
            library_type,
            client_name,
            project_name,
            source_path,
            is_active,
            created_at_utc,
            updated_at_utc
        FROM {LIBRARIES_TABLE}
    """
    params: list[Any] = []
    if active_only:
        sql += " WHERE is_active = ?"
        params.append(1)
    sql += " ORDER BY library_name, library_type, client_name, project_name"

    connection = connect_database(sqlite_path)
    try:
        rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_import_batches(
    sqlite_path: Path | str = DEFAULT_SQLITE_PATH,
    *,
    dataset_name: str | None = None,
    library_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    create_schema(sqlite_path)
    sql = f"""
        SELECT
            import_batch_id,
            library_id,
            dataset_name,
            source_path,
            source_sha256,
            row_count,
            status,
            notes,
            imported_at_utc
        FROM {IMPORT_BATCHES_TABLE}
        WHERE 1 = 1
    """
    params: list[Any] = []
    if dataset_name:
        sql += " AND dataset_name = ?"
        params.append(dataset_name)
    if library_id:
        sql += " AND library_id = ?"
        params.append(library_id)
    sql += " ORDER BY imported_at_utc DESC LIMIT ?"
    params.append(int(limit))

    connection = connect_database(sqlite_path)
    try:
        rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def lookup_service_alias(
    alias: str,
    *,
    sqlite_path: Path | str = DEFAULT_SQLITE_PATH,
) -> dict[str, str] | None:
    normalized_alias = _normalize_search_text(alias)
    if not normalized_alias:
        return None

    create_schema(sqlite_path)
    connection = connect_database(sqlite_path)
    try:
        row = connection.execute(
            f"""
            SELECT service_name, service_abbv, alias
            FROM {SERVICE_ALIASES_TABLE}
            WHERE alias_normalized = ? AND is_active = 1
            ORDER BY CASE WHEN alias = service_abbv THEN 0 ELSE 1 END, service_name
            LIMIT 1
            """,
            (normalized_alias,),
        ).fetchone()
        if row is None:
            return None
        return {
            "service": str(row["service_name"]),
            "service_abbv": str(row["service_abbv"]),
            "alias": str(row["alias"]),
        }
    finally:
        connection.close()


def lookup_field_alias(
    alias: str,
    *,
    sqlite_path: Path | str = DEFAULT_SQLITE_PATH,
) -> dict[str, str] | None:
    normalized_alias = _normalize_search_text(alias)
    if not normalized_alias:
        return None

    create_schema(sqlite_path)
    connection = connect_database(sqlite_path)
    try:
        row = connection.execute(
            f"""
            SELECT field_name, alias
            FROM {FIELD_ALIASES_TABLE}
            WHERE alias_normalized = ? AND is_active = 1
            ORDER BY field_name
            LIMIT 1
            """,
            (normalized_alias,),
        ).fetchone()
        if row is None:
            return None
        return {"field_name": str(row["field_name"]), "alias": str(row["alias"])}
    finally:
        connection.close()


def lookup_pipe_specs(
    *,
    sqlite_path: Path | str = DEFAULT_SQLITE_PATH,
    service: str | None = None,
    service_abbv: str | None = None,
    spec: str | None = None,
    size: float | None = None,
    library_name: str | None = None,
    active_only: bool = True,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    create_schema(sqlite_path)
    sql = f'SELECT * FROM {PIPE_SPEC_TABLE} WHERE 1 = 1'
    params: list[Any] = []

    if active_only:
        sql += ' AND "is_active" = ?'
        params.append(1)
    if spec:
        sql += ' AND UPPER(TRIM("Spec")) = ?'
        params.append(str(spec).strip().upper())
    if service_abbv:
        sql += ' AND UPPER(TRIM("Service_Abbv")) = ?'
        params.append(str(service_abbv).strip().upper())
    elif service:
        sql += ' AND UPPER(TRIM("Service")) = ?'
        params.append(str(service).strip().upper())
    if library_name:
        sql += " AND library_name = ?"
        params.append(str(library_name))
    sql += " ORDER BY rowid"

    connection = connect_database(sqlite_path)
    try:
        dataframe = pd.read_sql_query(sql, connection, params=params).fillna("")
    finally:
        connection.close()

    if size is not None and not dataframe.empty:
        dataframe = dataframe[dataframe["Size"].apply(lambda rule: size_matches(rule, size))]
    if limit is not None:
        dataframe = dataframe.head(int(limit))
    return dataframe.to_dict(orient="records")


def log_query_history(
    question: str,
    *,
    sqlite_path: Path | str = DEFAULT_SQLITE_PATH,
    parsed_service: str = "",
    parsed_field: str = "",
    requested_size: float | None = None,
    result_count: int = 0,
    success: bool = False,
    response_summary: str = "",
) -> int:
    create_schema(sqlite_path)
    connection = connect_database(sqlite_path)
    try:
        cursor = connection.execute(
            f"""
            INSERT INTO {QUERY_HISTORY_TABLE} (
                question,
                normalized_question,
                parsed_service,
                parsed_field,
                requested_size,
                result_count,
                success,
                response_summary,
                created_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                question,
                _normalize_search_text(question),
                parsed_service,
                parsed_field,
                requested_size,
                int(result_count),
                int(success),
                response_summary,
                _utcnow_text(),
            ),
        )
        query_id = int(cursor.lastrowid)
        _record_audit_event(
            connection,
            action="log_query_history",
            entity_type="query_history",
            entity_id=str(query_id),
            details={"success": bool(success), "result_count": int(result_count)},
        )
        connection.commit()
        return query_id
    finally:
        connection.close()


def save_answer(
    answer_text: str,
    *,
    sqlite_path: Path | str = DEFAULT_SQLITE_PATH,
    question: str = "",
    service: str = "",
    field_name: str = "",
    spec: str = "",
    source_reference: str = "",
    tags: str = "",
) -> int:
    if not str(answer_text).strip():
        raise DatabaseValidationError("Saved answer text cannot be blank.")

    create_schema(sqlite_path)
    connection = connect_database(sqlite_path)
    try:
        now_text = _utcnow_text()
        cursor = connection.execute(
            f"""
            INSERT INTO {SAVED_ANSWERS_TABLE} (
                question,
                answer_text,
                service,
                field_name,
                spec,
                source_reference,
                tags,
                created_at_utc,
                updated_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                question,
                answer_text,
                service,
                field_name,
                spec,
                source_reference,
                tags,
                now_text,
                now_text,
            ),
        )
        answer_id = int(cursor.lastrowid)
        _record_audit_event(
            connection,
            action="save_answer",
            entity_type="saved_answers",
            entity_id=str(answer_id),
            details={"service": service, "field_name": field_name, "spec": spec},
        )
        connection.commit()
        return answer_id
    finally:
        connection.close()


def get_saved_answers(
    sqlite_path: Path | str = DEFAULT_SQLITE_PATH,
    *,
    search_text: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    create_schema(sqlite_path)
    sql = f"""
        SELECT
            answer_id,
            question,
            answer_text,
            service,
            field_name,
            spec,
            source_reference,
            tags,
            created_at_utc,
            updated_at_utc
        FROM {SAVED_ANSWERS_TABLE}
        WHERE 1 = 1
    """
    params: list[Any] = []
    if search_text:
        sql += " AND (question LIKE ? OR answer_text LIKE ? OR service LIKE ? OR spec LIKE ?)"
        like_value = f"%{search_text}%"
        params.extend([like_value, like_value, like_value, like_value])
    sql += " ORDER BY created_at_utc DESC LIMIT ?"
    params.append(int(limit))

    connection = connect_database(sqlite_path)
    try:
        rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def add_standards_reference(
    standard_name: str,
    *,
    sqlite_path: Path | str = DEFAULT_SQLITE_PATH,
    reference_key: str = "",
    title: str = "",
    citation_text: str = "",
    source_path: str = "",
    notes: str = "",
) -> int:
    if not str(standard_name).strip():
        raise DatabaseValidationError("Standard name cannot be blank.")

    create_schema(sqlite_path)
    connection = connect_database(sqlite_path)
    try:
        cursor = connection.execute(
            f"""
            INSERT INTO {STANDARDS_REFERENCES_TABLE} (
                standard_name,
                reference_key,
                title,
                citation_text,
                source_path,
                notes,
                created_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                standard_name,
                reference_key,
                title,
                citation_text,
                source_path,
                notes,
                _utcnow_text(),
            ),
        )
        reference_id = int(cursor.lastrowid)
        _record_audit_event(
            connection,
            action="add_standards_reference",
            entity_type="standards_references",
            entity_id=str(reference_id),
            details={"standard_name": standard_name, "reference_key": reference_key},
        )
        connection.commit()
        return reference_id
    finally:
        connection.close()


def lookup_standards_references(
    *,
    sqlite_path: Path | str = DEFAULT_SQLITE_PATH,
    standard_name: str | None = None,
    reference_key: str | None = None,
    title_contains: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    create_schema(sqlite_path)
    sql = f"""
        SELECT
            reference_id,
            standard_name,
            reference_key,
            title,
            citation_text,
            source_path,
            notes,
            created_at_utc
        FROM {STANDARDS_REFERENCES_TABLE}
        WHERE 1 = 1
    """
    params: list[Any] = []
    if standard_name:
        sql += " AND standard_name = ?"
        params.append(standard_name)
    if reference_key:
        sql += " AND reference_key = ?"
        params.append(reference_key)
    if title_contains:
        sql += " AND title LIKE ?"
        params.append(f"%{title_contains}%")
    sql += " ORDER BY standard_name, reference_key, title LIMIT ?"
    params.append(int(limit))

    connection = connect_database(sqlite_path)
    try:
        rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def load_excel_dataframe(path: Path | str, *, sheet_name: str | int = 0) -> pd.DataFrame:
    source_path = Path(path)
    if not source_path.exists():
        raise FileNotFoundError(f"Excel workbook not found: {source_path}")

    dataframe = pd.read_excel(source_path, sheet_name=sheet_name).fillna("")
    dataframe.columns = [normalize_column_name(column) for column in dataframe.columns]
    return dataframe


def _import_pipe_specs_profile(
    connection: sqlite3.Connection,
    dataframe: pd.DataFrame,
    context: Mapping[str, Any],
) -> int:
    runtime_df = prepare_pipe_spec_dataframe(
        dataframe,
        library_name=str(context["library_name"]),
        library_type=str(context["library_type"]),
        client_name=str(context["client_name"]),
        project_name=str(context["project_name"]),
        import_batch_id=str(context["import_batch_id"]),
        is_active=int(context["is_active"]),
    )
    _replace_runtime_pipe_specifications(connection, runtime_df)
    _replace_canonical_pipe_specs(
        connection,
        runtime_df,
        library_id=str(context["library_id"]),
        import_batch_id=str(context["import_batch_id"]),
    )
    _refresh_alias_tables(connection, runtime_df, library_id=str(context["library_id"]))
    _write_import_metadata(
        connection,
        source_path=Path(str(context["source_path"])),
        row_count=len(runtime_df),
        import_batch_id=str(context["import_batch_id"]),
        library_name=str(context["library_name"]),
        library_type=str(context["library_type"]),
    )
    return len(runtime_df)


def _import_service_aliases_profile(
    connection: sqlite3.Connection,
    dataframe: pd.DataFrame,
    context: Mapping[str, Any],
) -> int:
    required = {"alias", "service_name"}
    missing = [column for column in required if column not in dataframe.columns]
    if missing:
        raise DatabaseValidationError(f"Missing required columns for service aliases: {missing}")

    connection.execute(
        f"DELETE FROM {SERVICE_ALIASES_TABLE} WHERE library_id = ?",
        (str(context["library_id"]),),
    )
    now_text = _utcnow_text()
    rows: list[tuple[str, str, str, str, str, int, str]] = []
    for _, row in dataframe.iterrows():
        alias = str(row["alias"]).strip()
        service_name = str(row["service_name"]).strip()
        service_abbv = str(row.get("service_abbv", "")).strip().upper()
        if not alias or not service_name:
            continue
        rows.append(
            (
                service_name,
                service_abbv,
                alias,
                _normalize_search_text(alias),
                str(context["library_id"]),
                int(context["is_active"]),
                now_text,
            )
        )
    from collections import Counter

    pairs = [(r[3], r[4]) for r in rows]  # alias_normalized, library_id

    counts = Counter(pairs)

    print("\n========== SERVICE ALIAS DUPLICATES ==========")

    duplicates = False

    for key, count in counts.items():
        if count > 1:
            duplicates = True
            print(f"DUPLICATE -> {key}  COUNT={count}")

    if not duplicates:
        print("No duplicate alias_normalized values found.")

    print("=============================================\n")

    if rows:
        connection.executemany(
            f"""
            INSERT INTO {SERVICE_ALIASES_TABLE} (
                service_name,
                service_abbv,
                alias,
                alias_normalized,
                library_id,
                is_active,
                created_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    return len(rows)


def _import_field_aliases_profile(
    connection: sqlite3.Connection,
    dataframe: pd.DataFrame,
    context: Mapping[str, Any],
) -> int:
    required = {"field_name", "alias"}
    missing = [column for column in required if column not in dataframe.columns]
    if missing:
        raise DatabaseValidationError(f"Missing required columns for field aliases: {missing}")

    connection.execute(
        f"DELETE FROM {FIELD_ALIASES_TABLE} WHERE library_id = ?",
        (str(context["library_id"]),),
    )
    now_text = _utcnow_text()
    rows: list[tuple[str, str, str, str, int, str]] = []
    for _, row in dataframe.iterrows():
        field_name = str(row["field_name"]).strip()
        alias = str(row["alias"]).strip()
        if not field_name or not alias:
            continue
        rows.append(
            (
                field_name,
                alias,
                _normalize_search_text(alias),
                str(context["library_id"]),
                int(context["is_active"]),
                now_text,
            )
        )
    if rows:
        connection.executemany(
            f"""
            INSERT INTO {FIELD_ALIASES_TABLE} (
                field_name,
                alias,
                alias_normalized,
                library_id,
                is_active,
                created_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    return len(rows)


def _import_standards_references_profile(
    connection: sqlite3.Connection,
    dataframe: pd.DataFrame,
    context: Mapping[str, Any],
) -> int:
    required = {"standard_name"}
    missing = [column for column in required if column not in dataframe.columns]
    if missing:
        raise DatabaseValidationError(f"Missing required columns for standards references: {missing}")

    rows: list[tuple[str, str, str, str, str, str, str]] = []
    for _, row in dataframe.iterrows():
        standard_name = str(row["standard_name"]).strip()
        if not standard_name:
            continue
        rows.append(
            (
                standard_name,
                str(row.get("reference_key", "")).strip(),
                str(row.get("title", "")).strip(),
                str(row.get("citation_text", "")).strip(),
                str(row.get("source_path", str(context["source_path"]))).strip(),
                str(row.get("notes", "")).strip(),
                _utcnow_text(),
            )
        )
    if rows:
        connection.executemany(
            f"""
            INSERT INTO {STANDARDS_REFERENCES_TABLE} (
                standard_name,
                reference_key,
                title,
                citation_text,
                source_path,
                notes,
                created_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    return len(rows)


EXCEL_IMPORT_PROFILES: dict[str, ExcelImportProfile] = {
    "pipe_specs": ExcelImportProfile(
        dataset_name="pipe_specs",
        target_table=PIPE_SPECS_TABLE,
        required_columns=("Spec", "Service", "Service_Abbv", "Size"),
        importer=_import_pipe_specs_profile,
    ),
    "service_aliases": ExcelImportProfile(
        dataset_name="service_aliases",
        target_table=SERVICE_ALIASES_TABLE,
        required_columns=("alias", "service_name"),
        importer=_import_service_aliases_profile,
    ),
    "field_aliases": ExcelImportProfile(
        dataset_name="field_aliases",
        target_table=FIELD_ALIASES_TABLE,
        required_columns=("field_name", "alias"),
        importer=_import_field_aliases_profile,
    ),
    "standards_references": ExcelImportProfile(
        dataset_name="standards_references",
        target_table=STANDARDS_REFERENCES_TABLE,
        required_columns=("standard_name",),
        importer=_import_standards_references_profile,
    ),
}


def import_excel_dataset(
    dataset_name: str,
    workbook_path: Path | str,
    *,
    sqlite_path: Path | str = DEFAULT_SQLITE_PATH,
    sheet_name: str | int | None = None,
    library_name: str = str(FUTURE_LIBRARY_DEFAULTS["library_name"]),
    library_type: str = "excel_import",
    client_name: str = "",
    project_name: str = "",
    is_active: int = 1,
) -> str:
    normalized_name = str(dataset_name).strip().lower()
    if normalized_name not in EXCEL_IMPORT_PROFILES:
        available = ", ".join(sorted(EXCEL_IMPORT_PROFILES))
        raise DatabaseValidationError(
            f"Unsupported dataset '{dataset_name}'. Available datasets: {available}"
        )

    profile = EXCEL_IMPORT_PROFILES[normalized_name]
    workbook = Path(workbook_path)
    import_batch_id = _build_import_batch_id(prefix=normalized_name.replace("_", "-"))
    dataframe = load_excel_dataframe(
        workbook,
        sheet_name=profile.default_sheet_name if sheet_name is None else sheet_name,
    )
    missing_columns = [column for column in profile.required_columns if column not in dataframe.columns]
    if missing_columns:
        raise DatabaseValidationError(
            f"Missing required columns for dataset '{dataset_name}': {missing_columns}"
        )

    create_schema(sqlite_path)
    connection = connect_database(sqlite_path)
    try:
        library_id = _upsert_library(
            connection,
            library_name=library_name,
            library_type=library_type,
            client_name=client_name,
            project_name=project_name,
            source_path=workbook,
            is_active=is_active,
        )
        context = {
            "library_id": library_id,
            "library_name": library_name,
            "library_type": library_type,
            "client_name": client_name,
            "project_name": project_name,
            "source_path": str(workbook),
            "import_batch_id": import_batch_id,
            "is_active": int(is_active),
        }
        row_count = profile.importer(connection, dataframe, context)
        _write_import_batch(
            connection,
            import_batch_id=import_batch_id,
            library_id=library_id,
            dataset_name=profile.dataset_name,
            source_path=workbook,
            row_count=row_count,
            source_sha256=_sha256_file(workbook),
        )
        _record_audit_event(
            connection,
            action="import_excel_dataset",
            entity_type=profile.target_table,
            entity_id=import_batch_id,
            details={
                "dataset_name": profile.dataset_name,
                "library_id": library_id,
                "row_count": row_count,
                "source_path": str(workbook),
            },
        )
        _create_indexes(connection)
        connection.commit()
        return import_batch_id
    finally:
        connection.close()


class DatabaseManager:
    def __init__(
        self,
        path: Path | str | None = None,
        sqlite_path: Path | str | None = None,
        autoload: bool = True,
    ):
        self.path = Path(path) if path is not None else DEFAULT_MASTER_PATH
        if sqlite_path is not None:
            self.sqlite_path = Path(sqlite_path)
        elif path is not None:
            self.sqlite_path = self.path.with_name("PipingIQ.db")
        else:
            self.sqlite_path = DEFAULT_SQLITE_PATH
        self._df: pd.DataFrame | None = None
        self._service_index: dict[str, pd.DataFrame] = {}
        self._spec_index: dict[str, pd.DataFrame] = {}
        self._service_name_index: dict[str, str] = {}

        if autoload:
            self.refresh()

    @property
    def loaded(self) -> bool:
        return self._df is not None

    @property
    def dataframe(self) -> pd.DataFrame:
        if not self.loaded:
            raise DatabaseNotLoadedError("Database has not been loaded.")
        return self._df  # type: ignore[return-value]

    def refresh(self) -> None:
        if self.path.exists():
            build_sqlite_database(
                sqlite_path=self.sqlite_path,
                pipe_spec_path=self.path,
            )
        elif not self.sqlite_path.exists():
            raise FileNotFoundError(
                f"No source workbook or runtime database was found for '{self.path}'."
            )
        dataframe = load_runtime_dataframe(self.sqlite_path)
        self._build_indexes(dataframe)
        self._df = dataframe

    def create_backup(self, backup_dir: Path | str = DEFAULT_BACKUP_DIR) -> Path:
        return backup_database(self.sqlite_path, backup_dir=backup_dir)

    def query(
        self,
        service: str | None = None,
        size: float | None = None,
        spec: str | None = None,
    ) -> QueryResult:
        if not self.loaded:
            return QueryResult(False, message="Database is not loaded.")

        if spec is not None and str(spec).strip():
            return self.query_by_spec(spec, size)

        if service is None or not str(service).strip():
            return QueryResult(False, message="Service is required for this query.")

        return self.query_by_service(service, size)

    def query_by_service(self, service: str, size: float | None = None) -> QueryResult:
        try:
            service_key = self._normalize_service(service)
        except ServiceNotFoundError as exc:
            return QueryResult(False, message=str(exc), service=service)

        rows = self._service_index.get(service_key, pd.DataFrame())
        if rows.empty:
            return QueryResult(False, message=f"Service not found: {service_key}", service=service_key)

        matching_rows = rows[rows["Size"].apply(lambda rule: size_matches(rule, size))]
        if matching_rows.empty:
            return QueryResult(
                False,
                message=f"No specification matches size {size} for service {service_key}.",
                service=service_key,
                requested_size=size,
            )

        specs = [EngineeringSpecification.from_series(row) for _, row in matching_rows.iterrows()]
        if len(specs) > 1:
            return QueryResult(
                False,
                specifications=specs,
                message=f"Multiple specifications match service {service_key} and size {size}.",
                service=service_key,
                requested_size=size,
            )

        return QueryResult(
            True,
            specifications=specs,
            message="Specification found.",
            service=service_key,
            requested_size=size,
        )

    def query_by_spec(self, spec: str, size: float | None = None) -> QueryResult:
        spec_key = str(spec).strip().upper()
        rows = self._spec_index.get(spec_key, pd.DataFrame())
        if rows.empty:
            return QueryResult(False, message=f"Specification not found: {spec}")

        matching_rows = rows[rows["Size"].apply(lambda rule: size_matches(rule, size))]
        if matching_rows.empty:
            return QueryResult(
                False,
                message=f"Specification {spec} found but does not match size {size}.",
                requested_size=size,
            )

        specs = [EngineeringSpecification.from_series(row) for _, row in matching_rows.iterrows()]
        if len(specs) > 1:
            return QueryResult(
                False,
                specifications=specs,
                message=f"Multiple entries found for specification {spec} and size {size}.",
                requested_size=size,
            )

        return QueryResult(True, specifications=specs, message="Specification found.", requested_size=size)

    def list_libraries(self, *, active_only: bool = False) -> list[dict[str, Any]]:
        return list_libraries(self.sqlite_path, active_only=active_only)

    def lookup_service_alias(self, alias: str) -> dict[str, str] | None:
        return lookup_service_alias(alias, sqlite_path=self.sqlite_path)

    def lookup_field_alias(self, alias: str) -> dict[str, str] | None:
        return lookup_field_alias(alias, sqlite_path=self.sqlite_path)

    def lookup_pipe_specs(
        self,
        *,
        service: str | None = None,
        service_abbv: str | None = None,
        spec: str | None = None,
        size: float | None = None,
        library_name: str | None = None,
        active_only: bool = True,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        return lookup_pipe_specs(
            sqlite_path=self.sqlite_path,
            service=service,
            service_abbv=service_abbv,
            spec=spec,
            size=size,
            library_name=library_name,
            active_only=active_only,
            limit=limit,
        )

    def statistics(self) -> dict[str, Any]:
        return {
            "loaded": self.loaded,
            "master_workbook_path": str(self.path),
            "runtime_database_path": str(self.sqlite_path),
            "record_count": len(self._df) if self._df is not None else 0,
            "service_count": len(self._service_index),
            "spec_count": len(self._spec_index),
            "library_count": len(self.list_libraries()) if self.sqlite_path.exists() else 0,
        }

    def _build_indexes(self, dataframe: pd.DataFrame) -> None:
        self._service_index = {
            str(service_abbrev).strip().upper(): group.reset_index(drop=True)
            for service_abbrev, group in dataframe.groupby("Service_Abbv")
        }
        self._spec_index = {
            str(spec_name).strip().upper(): group.reset_index(drop=True)
            for spec_name, group in dataframe.groupby("Spec")
        }

        service_name_index: dict[str, str] = {}
        for service_abbrev, group in self._service_index.items():
            for service_name in group["Service"].astype(str).str.upper().unique():
                service_name = service_name.strip()
                if service_name:
                    service_name_index[service_name] = service_abbrev
        self._service_name_index = service_name_index

    def _normalize_service(self, service: str) -> str:
        key = str(service).strip().upper()
        if key in self._service_index:
            return key
        if key in self._service_name_index:
            return self._service_name_index[key]

        alias_match = self.lookup_service_alias(service)
        if alias_match is not None:
            alias_key = str(alias_match.get("service_abbv", "")).strip().upper()
            service_name = str(alias_match.get("service", "")).strip().upper()
            if alias_key in self._service_index:
                return alias_key
            if service_name in self._service_name_index:
                return self._service_name_index[service_name]

        raise ServiceNotFoundError(f"Service is not recognized: {service}")


__all__ = [
    "APP_METADATA_TABLE",
    "DATABASE_AUDIT_LOG_TABLE",
    "DatabaseError",
    "DatabaseManager",
    "DatabaseNotLoadedError",
    "DatabaseValidationError",
    "EngineeringSpecification",
    "ExcelImportProfile",
    "FIELD_ALIASES_TABLE",
    "IMPORT_BATCHES_TABLE",
    "IMPORT_METADATA_TABLE",
    "LIBRARIES_TABLE",
    "PIPE_SPECS_TABLE",
    "PIPE_SPEC_TABLE",
    "QUERY_HISTORY_TABLE",
    "QueryError",
    "QueryResult",
    "SAVED_ANSWERS_TABLE",
    "SERVICE_ALIASES_TABLE",
    "STANDARDS_REFERENCES_TABLE",
    "ServiceNotFoundError",
    "SpecificationNotFoundError",
    "add_standards_reference",
    "backup_database",
    "build_sqlite_database",
    "connect_database",
    "create_schema",
    "get_app_metadata",
    "get_import_batches",
    "get_saved_answers",
    "import_excel_dataset",
    "list_libraries",
    "load_excel_dataframe",
    "load_pipe_spec_dataframe",
    "load_runtime_dataframe",
    "log_query_history",
    "lookup_field_alias",
    "lookup_pipe_specs",
    "lookup_service_alias",
    "lookup_standards_references",
    "normalize_column_name",
    "prepare_pipe_spec_dataframe",
    "record_audit_event",
    "save_answer",
    "set_app_metadata",
    "size_matches",
]
