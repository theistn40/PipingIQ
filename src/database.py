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

from config import PIPE_DIMENSIONS_DB

REQUIRED_COLUMNS = {"Spec", "Service", "Service_Abbv", "Size"}
DB_FILENAME = "PipeSpec_Master.xlsx"
ROOT = Path(__file__).resolve().parent
DEFAULT_DATABASE_PATH = ROOT.parent / "data" / DB_FILENAME
DEFAULT_DIMENSIONS_PATH = PIPE_DIMENSIONS_DB


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


@dataclass
class DimensionQueryResult:
    success: bool
    records: list[dict[str, Any]] = field(default_factory=list)
    message: str = ""
    item: str | None = None
    requested_size: float | None = None


class DimensionDatabase:
    def __init__(self, path: Path | str | None = None, autoload: bool = True):
        self.path = Path(path) if path is not None else DEFAULT_DIMENSIONS_PATH
        self._df: pd.DataFrame | None = None

        if autoload:
            self.refresh()

    @property
    def loaded(self) -> bool:
        return self._df is not None

    @property
    def dataframe(self) -> pd.DataFrame:
        if not self.loaded:
            raise DatabaseNotLoadedError("Dimension database has not been loaded.")
        return self._df

    def refresh(self) -> None:
        df = self._load_database()
        self._normalize(df)
        self._df = df

    def _load_database(self) -> pd.DataFrame:
        if not self.path.exists():
            raise FileNotFoundError(f"Dimension database not found: {self.path}")

        df = pd.read_excel(self.path, header=2)
        return df

    def _normalize(self, df: pd.DataFrame) -> None:
        df = df.fillna("")
        df.columns = [str(c).strip() for c in df.columns]

        # Drop blank header/data rows introduced by the sheet layout
        if "SIZE" not in df.columns and df.columns.size > 0:
            raise DatabaseValidationError("Dimension database is missing a SIZE column.")

        df = df.loc[df["SIZE"].astype(str).str.strip() != ""].reset_index(drop=True)
        df["SIZE"] = df["SIZE"].astype(str).str.strip()
        self._df = df

    def item_options(self) -> list[str]:
        if not self.loaded:
            return []
        seen: set[str] = set()
        columns: list[str] = []
        for col in self._df.columns:
            name = str(col).strip()
            if not name or name.upper() == "SIZE":
                continue
            if name in seen:
                continue
            seen.add(name)
            columns.append(name)
        return columns

    def query(self, item: str | None = None, size: float | None = None) -> DimensionQueryResult:
        if not self.loaded:
            return DimensionQueryResult(False, message="Dimension database is not loaded.")

        if item is None or not str(item).strip():
            return DimensionQueryResult(False, message="Please select a dimension item.")

        if size is None:
            return DimensionQueryResult(False, message="Please enter a size to search.")

        item_name = str(item).strip()
        if item_name not in self._df.columns:
            return DimensionQueryResult(False, message=f"Unknown dimension item: {item_name}")

        matched = []
        for _, row in self._df.iterrows():
            try:
                if size_matches(row["SIZE"], size):
                    matched.append({
                        "Size": row["SIZE"],
                        "Item": item_name,
                        item_name: row[item_name],
                        **{col: row[col] for col in self._df.columns if col not in {"SIZE", item_name}},
                    })
            except Exception:
                continue

        if not matched:
            return DimensionQueryResult(
                False,
                message=f"No dimension results found for {item_name} at size {size}.",
                item=item_name,
                requested_size=size,
            )

        return DimensionQueryResult(
            True,
            records=matched,
            message=f"Found {len(matched)} dimension record(s).",
            item=item_name,
            requested_size=size,
        )


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

        # Remove accidental repeated header rows inside the sheet where cells contain the column names
        try:
            if "Spec" in df.columns and "Service" in df.columns and "Size" in df.columns:
                spec_header = df["Spec"].astype(str).str.strip().str.upper() == "SPEC"
                service_header = df["Service"].astype(str).str.strip().str.upper() == "SERVICE"
                size_header = df["Size"].astype(str).str.strip().str.upper() == "SIZE"
                header_rows = spec_header & service_header & size_header
                if header_rows.any():
                    df = df.loc[~header_rows].reset_index(drop=True)
        except Exception:
            # If anything unexpected happens, keep the original dataframe and let validation handle it
            pass
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
    # Accept size rules with optional trailing double-quote (e.g. <=2" or > 2")
    rule_text = str(rule).strip()
    if rule_text == "" or rule_text.upper() == "ALL":
        return True

    # Normalize by removing common quote characters before validation
    normalized = rule_text.replace('"', '').replace('”', '').upper()

    # Collapse spaced comparator tokens like '< =' into '<=' so they validate
    normalized = re.sub(r"<\s*=", "<=", normalized)
    normalized = re.sub(r">\s*=", ">=", normalized)

    # Accept 'ALL' or blank
    if normalized == "" or normalized == "ALL":
        return True

    # Accept simple comparator + numeric (including fractions) or range expressions like '1-2' or '1 TO 2'
    comp_match = re.match(r"^(<=|>=|<|>)\s*(.+)$", normalized)
    if comp_match:
        _, rhs = comp_match.groups()
        try:
            _parse_numeric_size(rhs)
            return True
        except ValueError:
            return False

    # Range forms: 'x-y' or 'x TO y'
    range_match = re.match(r"^(\S+)\s*[-]\s*(\S+)$", normalized) or re.match(r"^(\S+)\s+TO\s+(\S+)$", normalized)
    if range_match:
        a, b = range_match.groups()
        try:
            _parse_numeric_size(a)
            _parse_numeric_size(b)
            return True
        except ValueError:
            return False

    # Otherwise expect a single numeric value (possibly a fraction)
    try:
        _parse_numeric_size(normalized)
        return True
    except ValueError:
        return False


def size_matches(rule: Any, requested_size: float | None) -> bool:
    if requested_size is None:
        return True
    # Remove quotes and normalize for numeric comparison
    rule_text = str(rule).strip()
    if rule_text == "" or rule_text.upper() == "ALL":
        return True

    # Normalize
    rule_norm = rule_text.replace('"', '').replace('”', '').strip().upper()
    rule_norm = re.sub(r"<\s*=", "<=", rule_norm)
    rule_norm = re.sub(r">\s*=", ">=", rule_norm)

    # Blank or ALL matches anything
    if rule_norm == "" or rule_norm == "ALL":
        return True

    # Comparator forms
    comp_match = re.match(r"^(<=|>=|<|>)\s*(.+)$", rule_norm)
    if comp_match:
        comp, rhs = comp_match.groups()
        try:
            val = _parse_numeric_size(rhs)
        except ValueError:
            return False
        if comp == "<=":
            return requested_size <= val
        if comp == ">=":
            return requested_size >= val
        if comp == "<":
            return requested_size < val
        if comp == ">":
            return requested_size > val

    # Range forms like 'x-y' or 'x TO y'
    range_match = re.match(r"^(\S+)\s*[-]\s*(\S+)$", rule_norm) or re.match(r"^(\S+)\s+TO\s+(\S+)$", rule_norm)
    if range_match:
        a, b = range_match.groups()
        try:
            low = _parse_numeric_size(a)
            high = _parse_numeric_size(b)
        except ValueError:
            return False
        return low <= requested_size <= high

    # Single numeric value
    try:
        val = _parse_numeric_size(rule_norm)
        return requested_size == val
    except ValueError:
        return False


def _parse_numeric_size(text: str) -> float:
    """Parse a numeric size token which may be a decimal or a fraction like '1 1/2' or '3/4'.

    Raises ValueError if parsing fails.
    """
    s = str(text).strip()
    # remove any trailing punctuation
    s = s.strip().strip('"').strip()

    # Try plain float first
    try:
        return float(s)
    except Exception:
        pass

    # Match mixed number like '1 1/2' or '1-1/2' (treat dash between int and fraction as space)
    mixed = re.match(r"^(\d+)\s*[- ]\s*(\d+)/(\d+)$", s)
    if mixed:
        whole, num, den = mixed.groups()
        return float(whole) + float(num) / float(den)

    # Match simple fraction like '3/4'
    frac = re.match(r"^(\d+)/(\d+)$", s)
    if frac:
        num, den = frac.groups()
        return float(num) / float(den)

    # If none matched, raise
    raise ValueError(f"Cannot parse numeric size from '{text}'")


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
