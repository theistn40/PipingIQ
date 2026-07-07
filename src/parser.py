"""
Production parser for the PipeSpec master workbook and lightweight query parsing.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Literal, TypedDict

from database import (
    DEFAULT_MASTER_PATH,
    REQUIRED_COLUMNS,
    RUNTIME_METADATA_COLUMNS,
    DatabaseError,
    DatabaseValidationError,
    EngineeringSpecification,
    load_pipe_spec_dataframe,
    prepare_pipe_spec_dataframe,
)

LOGGER = logging.getLogger(__name__)

_TOKEN_RE: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9]+")
_MIXED_NUMBER_RE: Final[re.Pattern[str]] = re.compile(r"^(?P<whole>\d+)\s*[- ]\s*(?P<num>\d+)/(?P<den>\d+)$")
_FRACTION_RE: Final[re.Pattern[str]] = re.compile(r"^(?P<num>\d+)/(?P<den>\d+)$")
_COMPARATOR_RE: Final[re.Pattern[str]] = re.compile(r"^(?P<op><=|>=|<|>)\s*(?P<value>.+)$")
_RANGE_RE: Final[re.Pattern[str]] = re.compile(r"^(?P<start>\S+)\s*(?:-|TO)\s*(?P<end>\S+)$")
_SIZE_WITH_UNIT_RE: Final[re.Pattern[str]] = re.compile(
    r"(?P<size>\d+\s*[- ]\s*\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)\s*(?:\"|INCH(?:ES)?\b|IN\.\b|IN\b)",
    re.IGNORECASE,
)
_SIZE_CONTEXT_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:FOR|SIZE|AT|LINE)\s+(?P<size>\d+\s*[- ]\s*\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)

_REQUEST_WORDS: Final[set[str]] = {
    "a",
    "an",
    "for",
    "give",
    "i",
    "is",
    "me",
    "need",
    "of",
    "pipe",
    "piping",
    "please",
    "show",
    "spec",
    "specification",
    "specifications",
    "tell",
    "the",
    "what",
    "which",
}

FIELD_WORDS: Final[dict[str, tuple[str, ...]]] = {
    "Pipe": ("pipe", "piping", "material"),
    "Schedule": ("schedule", "sch", "wall thickness"),
    "Coupling": ("coupling", "couplings"),
    "Fitting": ("fitting", "fittings"),
    "Joint": ("joint", "joints"),
    "Valve": ("valve", "valves"),
    "Flange": ("flange", "flanges"),
    "Bolts": ("bolt", "bolts", "fastener", "fasteners"),
    "Clamps": ("clamp", "clamps"),
    "SOLDER": ("solder",),
    "Gasket": ("gasket", "gaskets"),
    "Insulation": ("insulation", "insulated"),
    "Support Spacing": ("support spacing", "hanger spacing", "supports"),
    "Test Pressure": ("test pressure", "hydrotest pressure"),
    "Flexible Hose": ("flexible hose", "hose"),
    "MAXIMUM PRESSURE (PSI)": ("maximum pressure", "max pressure", "pressure"),
    "MAXIMUM TEMPERATURE (F)": ("maximum temperature", "max temperature", "temperature"),
    "Thread Compound": ("thread compound", "pipe dope", "sealant"),
    "Strainers": ("strainer", "strainers"),
    "Traps": ("trap", "traps"),
    "o'lets": ("olet", "olets", "o'let", "weldolet", "sockolet", "threadolet"),
    "90 deg elbow": ("90 elbow", "90 degree elbow"),
    "45 deg elbow": ("45 elbow", "45 degree elbow"),
    "Tee": ("tee", "tees"),
    "Coatings": ("coating", "coatings"),
    "Lining": ("lining",),
    "Unions": ("union", "unions"),
}


class ParserError(Exception):
    """Base parser error."""


class ParserWorkbookError(ParserError):
    """Raised when the workbook cannot be read."""


class ParserValidationError(ParserError):
    """Raised when the workbook contents are invalid."""


class ParsedQuestion(TypedDict):
    service: str | None
    field: str | None
    size: float | None


@dataclass(frozen=True)
class PipeSizeRule:
    raw_value: str
    normalized_value: str
    kind: Literal["all", "exact", "lt", "lte", "gt", "gte", "range"]
    lower_bound: float | None = None
    upper_bound: float | None = None


@dataclass(frozen=True)
class ServiceDefinition:
    service: str
    service_abbreviation: str
    normalized_service: str
    normalized_service_abbreviation: str


@dataclass(frozen=True)
class ParsedPipeSpecification:
    specification: EngineeringSpecification
    service_definition: ServiceDefinition
    size_rule: PipeSizeRule

    @property
    def spec(self) -> str:
        return self.specification.spec

    @property
    def service(self) -> str:
        return self.specification.service

    @property
    def service_abbreviation(self) -> str:
        return self.specification.service_abbv

    @property
    def fields(self) -> dict[str, Any]:
        return self.specification.fields


@dataclass(frozen=True)
class ParsedWorkbook:
    source_path: Path
    discovered_columns: tuple[str, ...]
    required_columns: tuple[str, ...]
    services: tuple[ServiceDefinition, ...]
    records: tuple[ParsedPipeSpecification, ...]

    def find_by_spec(self, spec: str) -> tuple[ParsedPipeSpecification, ...]:
        normalized_spec = _normalize_spec(spec)
        return tuple(record for record in self.records if _normalize_spec(record.spec) == normalized_spec)

    def find_by_service(self, service: str) -> tuple[ParsedPipeSpecification, ...]:
        normalized_service = normalize_service(service)
        normalized_abbreviation = normalize_service_abbreviation(service)
        return tuple(
            record
            for record in self.records
            if record.service_definition.normalized_service == normalized_service
            or record.service_definition.normalized_service_abbreviation == normalized_abbreviation
        )

    def engineering_specifications(self) -> tuple[EngineeringSpecification, ...]:
        return tuple(record.specification for record in self.records)


def parse_pipe_spec_workbook(path: Path | str = DEFAULT_MASTER_PATH) -> ParsedWorkbook:
    source_path = Path(path)
    _log(logging.INFO, "pipe_spec_parser_started", source_path=source_path)

    try:
        source_dataframe = load_pipe_spec_dataframe(source_path)
        discovered_columns = tuple(str(column) for column in source_dataframe.columns)
        _validate_required_columns(discovered_columns)

        prepared_dataframe = prepare_pipe_spec_dataframe(source_dataframe)
        record_dataframe = prepared_dataframe.drop(columns=list(RUNTIME_METADATA_COLUMNS), errors="ignore")
        records = tuple(_build_record(row) for _, row in record_dataframe.iterrows())
        services = _build_service_catalog(records)
    except FileNotFoundError as exc:
        _log(logging.ERROR, "pipe_spec_parser_file_missing", source_path=source_path, error=str(exc))
        raise ParserWorkbookError(f"Workbook not found: {source_path}") from exc
    except DatabaseValidationError as exc:
        _log(logging.ERROR, "pipe_spec_parser_validation_failed", source_path=source_path, error=str(exc))
        raise ParserValidationError(str(exc)) from exc
    except DatabaseError as exc:
        _log(logging.ERROR, "pipe_spec_parser_database_error", source_path=source_path, error=str(exc))
        raise ParserError(f"Unable to parse workbook '{source_path}': {exc}") from exc
    except Exception as exc:
        _log(logging.ERROR, "pipe_spec_parser_unexpected_error", source_path=source_path, error=str(exc))
        raise ParserError(f"Unexpected parser failure for '{source_path}': {exc}") from exc

    parsed_workbook = ParsedWorkbook(
        source_path=source_path,
        discovered_columns=discovered_columns,
        required_columns=tuple(sorted(REQUIRED_COLUMNS)),
        services=services,
        records=records,
    )
    _log(
        logging.INFO,
        "pipe_spec_parser_completed",
        source_path=source_path,
        row_count=len(parsed_workbook.records),
        column_count=len(parsed_workbook.discovered_columns),
        service_count=len(parsed_workbook.services),
    )
    return parsed_workbook


def load_engineering_specifications(path: Path | str = DEFAULT_MASTER_PATH) -> tuple[EngineeringSpecification, ...]:
    return parse_pipe_spec_workbook(path).engineering_specifications()


def normalize_service(service: str) -> str:
    return " ".join(token.lower() for token in _TOKEN_RE.findall(str(service).strip()))


def normalize_service_abbreviation(service_abbreviation: str) -> str:
    return " ".join(token.upper() for token in _TOKEN_RE.findall(str(service_abbreviation).strip()))


def normalize_pipe_size(size_value: Any) -> PipeSizeRule:
    raw_value = str(size_value).strip()
    normalized_value = _normalize_size_text(raw_value)

    if normalized_value == "" or normalized_value == "ALL":
        return PipeSizeRule(
            raw_value=raw_value,
            normalized_value="ALL" if normalized_value == "ALL" else "",
            kind="all",
        )

    comparator_match = _COMPARATOR_RE.match(normalized_value)
    if comparator_match:
        comparator = comparator_match.group("op")
        boundary = _parse_numeric_size(comparator_match.group("value"))
        kind_map: dict[str, Literal["lt", "lte", "gt", "gte"]] = {
            "<": "lt",
            "<=": "lte",
            ">": "gt",
            ">=": "gte",
        }
        return PipeSizeRule(
            raw_value=raw_value,
            normalized_value=f"{comparator} {_format_numeric_size(boundary)}",
            kind=kind_map[comparator],
            upper_bound=boundary if comparator.startswith("<") else None,
            lower_bound=boundary if comparator.startswith(">") else None,
        )

    range_match = _RANGE_RE.match(normalized_value)
    if range_match:
        lower_bound = _parse_numeric_size(range_match.group("start"))
        upper_bound = _parse_numeric_size(range_match.group("end"))
        if lower_bound > upper_bound:
            lower_bound, upper_bound = upper_bound, lower_bound
        return PipeSizeRule(
            raw_value=raw_value,
            normalized_value=f"{_format_numeric_size(lower_bound)} - {_format_numeric_size(upper_bound)}",
            kind="range",
            lower_bound=lower_bound,
            upper_bound=upper_bound,
        )

    exact_value = _parse_numeric_size(normalized_value)
    return PipeSizeRule(
        raw_value=raw_value,
        normalized_value=_format_numeric_size(exact_value),
        kind="exact",
        lower_bound=exact_value,
        upper_bound=exact_value,
    )


def parse_question(question: str) -> ParsedQuestion:
    question_text = " ".join(str(question).split())
    normalized_question = normalize_service(question_text)
    size = _extract_requested_size(question_text)
    field = _match_field(normalized_question)
    service = _extract_service_text(question_text, normalized_question, field)

    _log(
        logging.DEBUG,
        "question_parsed",
        question=question_text,
        parsed_service=service or "",
        parsed_field=field or "",
        parsed_size=size,
    )
    return {
        "service": service,
        "field": field,
        "size": size,
    }


def _build_record(row: Any) -> ParsedPipeSpecification:
    specification = EngineeringSpecification.from_series(row)
    service_definition = ServiceDefinition(
        service=specification.service,
        service_abbreviation=specification.service_abbv,
        normalized_service=normalize_service(specification.service),
        normalized_service_abbreviation=normalize_service_abbreviation(specification.service_abbv),
    )
    return ParsedPipeSpecification(
        specification=specification,
        service_definition=service_definition,
        size_rule=normalize_pipe_size(specification.size_rule),
    )


def _build_service_catalog(records: tuple[ParsedPipeSpecification, ...]) -> tuple[ServiceDefinition, ...]:
    services_by_key: dict[tuple[str, str], ServiceDefinition] = {}
    for record in records:
        service_definition = record.service_definition
        key = (service_definition.service, service_definition.service_abbreviation)
        services_by_key.setdefault(key, service_definition)
    return tuple(sorted(services_by_key.values(), key=lambda service: (service.service, service.service_abbreviation)))


def _validate_required_columns(columns: tuple[str, ...]) -> None:
    missing_columns = [column for column in sorted(REQUIRED_COLUMNS) if column not in columns]
    if missing_columns:
        raise ParserValidationError(f"Missing required columns: {missing_columns}")


def _normalize_size_text(size_value: str) -> str:
    normalized = str(size_value).strip()
    normalized = normalized.replace("”", '"').replace("“", '"').replace("″", '"')
    normalized = re.sub(r"\bINCH(?:ES)?\b", '"', normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bIN\.\b", '"', normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bNPS\b", "", normalized, flags=re.IGNORECASE)
    normalized = normalized.replace('"', "")
    normalized = re.sub(r"<\s*=", "<=", normalized)
    normalized = re.sub(r">\s*=", ">=", normalized)
    normalized = re.sub(r"\s+TO\s+", " TO ", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", " ", normalized).strip().upper()
    return normalized


def _parse_numeric_size(size_value: str) -> float:
    value = _normalize_size_text(size_value)
    if not value:
        raise ParserValidationError("Pipe size cannot be blank.")

    try:
        return float(value)
    except ValueError:
        pass

    mixed_number_match = _MIXED_NUMBER_RE.match(value)
    if mixed_number_match:
        whole = float(mixed_number_match.group("whole"))
        numerator = float(mixed_number_match.group("num"))
        denominator = float(mixed_number_match.group("den"))
        return whole + (numerator / denominator)

    fraction_match = _FRACTION_RE.match(value)
    if fraction_match:
        numerator = float(fraction_match.group("num"))
        denominator = float(fraction_match.group("den"))
        return numerator / denominator

    raise ParserValidationError(f"Unable to parse pipe size: {size_value}")


def _format_numeric_size(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _normalize_spec(spec: str) -> str:
    return " ".join(str(spec).strip().upper().split())


def _extract_requested_size(question: str) -> float | None:
    matches = list(_SIZE_WITH_UNIT_RE.finditer(question))
    if matches:
        return _parse_numeric_size(matches[-1].group("size"))

    contextual_matches = list(_SIZE_CONTEXT_RE.finditer(question))
    if contextual_matches:
        return _parse_numeric_size(contextual_matches[-1].group("size"))

    return None


def _match_field(normalized_question: str) -> str | None:
    matches: list[tuple[int, int, str]] = []
    question_tokens = set(normalized_question.split())

    for field_name, aliases in FIELD_WORDS.items():
        normalized_field_name = normalize_service(field_name)
        all_aliases = {normalized_field_name}
        all_aliases.update(normalize_service(alias) for alias in aliases)

        best_score = 0
        for alias in all_aliases:
            alias_tokens = alias.split()
            if not alias_tokens:
                continue
            if alias in normalized_question:
                best_score = max(best_score, 100 + len(alias_tokens))
            elif set(alias_tokens).issubset(question_tokens):
                best_score = max(best_score, 50 + len(alias_tokens))
        if best_score:
            matches.append((best_score, len(normalized_field_name.split()), field_name))

    if not matches:
        return None

    matches.sort(reverse=True)
    return matches[0][2]


def _extract_service_text(question: str, normalized_question: str, field: str | None) -> str | None:
    working_question = normalized_question

    if field is not None:
        candidate_aliases = {normalize_service(field)}
        candidate_aliases.update(normalize_service(alias) for alias in FIELD_WORDS.get(field, ()))
        for alias in sorted(candidate_aliases, key=len, reverse=True):
            if alias:
                working_question = re.sub(rf"\b{re.escape(alias)}\b", " ", working_question)

    working_question = _SIZE_WITH_UNIT_RE.sub(" ", working_question)
    working_question = _SIZE_CONTEXT_RE.sub(" ", working_question)
    tokens = [token for token in working_question.split() if token not in _REQUEST_WORDS]

    if not tokens:
        return None
    return " ".join(tokens).strip() or None


def _serialize_log_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, tuple):
        return list(value)
    return str(value)


def _log(level: int, event: str, **fields: Any) -> None:
    payload = {"event": event}
    payload.update({key: _serialize_log_value(value) for key, value in fields.items()})
    LOGGER.log(level, json.dumps(payload, ensure_ascii=True, sort_keys=True))


__all__ = [
    "FIELD_WORDS",
    "ParsedPipeSpecification",
    "ParsedQuestion",
    "ParsedWorkbook",
    "ParserError",
    "ParserValidationError",
    "ParserWorkbookError",
    "PipeSizeRule",
    "ServiceDefinition",
    "load_engineering_specifications",
    "normalize_pipe_size",
    "normalize_service",
    "normalize_service_abbreviation",
    "parse_pipe_spec_workbook",
    "parse_question",
]
