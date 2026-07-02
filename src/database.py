"""
=========================================================
PipingIQ V5.1
database.py
Database manager and engineering specification loader.
=========================================================
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


REQUIRED_COLUMNS = {"Spec", "Service", "Service_Abbv", "Size"}
DB_FILENAME = "PipeSpec_Master.xlsx"
ROOT = Path(__file__).resolve().parent
DEFAULT_DATABASE_PATH = ROOT.parent / "data" / DB_FILENAME


# ------------------------------------------------------------------
# Exceptions
# ------------------------------------------------------------------

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


# ------------------------------------------------------------------
# Runtime objects
# ------------------------------------------------------------------

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
        return cls(
            spec=str(row["Spec"]).strip(),
            service=str(row["Service"]).strip(),
            service_abbv=str(row["Service_Abbv"]).strip().upper(),
            size_rule=str(row["Size"]).strip(),
            fields={
                key: value
                for key, value in row.items()
                if key not in {"Spec", "Service", "Service_Abbv", "Size"}
            },
            row_index=int(row.name) if row.name is not None else None,
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
        return self.success and len(self.specifications) > 1


# ------------------------------------------------------------------
# Database manager
# ------------------------------------------------------------------

class DatabaseManager:
    def __init__(self, path: Path | str | None = None, autoload: bool = True):
        self.path = Path(path) if path is not None else DEFAULT_DATABASE_PATH
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
        return self._df

    def refresh(self) -> None:
        df = self._load_database()
        self._validate_database(df)
        self._normalize(df)
        self._build_indexes(df)
        self._df = df

    def _load_database(self) -> pd.DataFrame:
        if not self.path.exists():
            raise FileNotFoundError(f"Database not found: {self.path}")

        df = pd.read_excel(self.path)
        df.columns = [str(c).strip() for c in df.columns]
        df = df.fillna("")
        return df

    def _validate_database(self, df: pd.DataFrame) -> None:
        missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise DatabaseValidationError(f"Missing required columns: {missing}")

        invalid_rules = [
            (int(index), rule)
            for index, rule in df["Size"].items()
            if not _is_valid_size_rule(rule)
        ]
        if invalid_rules:
            raise DatabaseValidationError(
                f"Invalid size rules found: {invalid_rules[:10]}"
            )

    def _normalize(self, df: pd.DataFrame) -> None:
        for column in df.columns:
            if df[column].dtype == object:
                df[column] = df[column].astype(str).str.strip()

        df["Service_Abbv"] = df["Service_Abbv"].str.upper().str.strip()
        df["Service"] = df["Service"].str.strip()
        df["Spec"] = df["Spec"].str.strip()
        df["Size"] = df["Size"].astype(str).str.strip()

    def _build_indexes(self, df: pd.DataFrame) -> None:
        self._service_index = {
            service_abbrev: group.reset_index(drop=True)
            for service_abbrev, group in df.groupby("Service_Abbv")
        }
        self._spec_index = {
            spec_name.upper(): group.reset_index(drop=True)
            for spec_name, group in df.groupby("Spec")
        }
        self._service_name_index = {
            service_name.upper(): service_abbrev
            for service_abbrev, group in self._service_index.items()
            for service_name in group["Service"].astype(str).str.upper().unique()
        }

    def query(self, service: str | None = None, size: float | None = None, spec: str | None = None) -> QueryResult:
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

        return QueryResult(True, specifications=specs, message="Specification found.", service=service_key, requested_size=size)

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

    def _normalize_service(self, service: str) -> str:
        key = str(service).strip().upper()
        if key in self._service_index:
            return key
        if key in self._service_name_index:
            return self._service_name_index[key]
        raise ServiceNotFoundError(f"Service is not recognized: {service}")

    def statistics(self) -> dict[str, Any]:
        return {
            "loaded": self.loaded,
            "database_path": str(self.path),
            "record_count": len(self._df) if self._df is not None else 0,
            "service_count": len(self._service_index),
            "spec_count": len(self._spec_index),
        }


def _is_valid_size_rule(rule: Any) -> bool:
    rule_text = str(rule).strip().upper()
    if rule_text == "" or rule_text == "ALL":
        return True

    pattern = re.compile(r"^(<=|>=|<|>)?\s*(\d+(\.\d+)?)$")
    return bool(pattern.match(rule_text))


def size_matches(rule: Any, requested_size: float | None) -> bool:
    if requested_size is None:
        return True

    rule_text = str(rule).strip().upper()
    if rule_text == "" or rule_text == "ALL":
        return True

    try:
        if rule_text.startswith("<="):
            return requested_size <= float(rule_text[2:].strip())
        if rule_text.startswith(">="):
            return requested_size >= float(rule_text[2:].strip())
        if rule_text.startswith("<"):
            return requested_size < float(rule_text[1:].strip())
        if rule_text.startswith(">"):
            return requested_size > float(rule_text[1:].strip())
        return requested_size == float(rule_text)
    except ValueError:
        return False


__all__ = [
    "DatabaseManager",
    "EngineeringSpecification",
    "QueryResult",
    "DatabaseError",
    "DatabaseNotLoadedError",
    "DatabaseValidationError",
    "ServiceNotFoundError",
    "SpecificationNotFoundError",
    "QueryError",
    "size_matches",
]
