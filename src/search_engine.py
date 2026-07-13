"""
=========================================================
PipingIQ Professional v6.0
search_engine.py
Engineering query engine for Pipe Specifications.
=========================================================
"""

from typing import Any
import re

from database import size_matches
from parser import FIELD_WORDS, parse_question


BASE_COLUMNS = {"Spec", "Service", "Service_Abbv", "Size"}
INTERNAL_COLUMNS = BASE_COLUMNS | {
    "library_name",
    "library_type",
    "client_name",
    "project_name",
    "import_batch_id",
    "is_active",
}


def normalize_search_text(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(text).lower()))


def build_field_aliases(field_name: str) -> set[str]:
    aliases = {field_name, normalize_search_text(field_name)}
    without_parens = re.sub(r"\([^)]*\)", "", field_name).strip()
    if without_parens:
        aliases.add(without_parens)
        aliases.add(normalize_search_text(without_parens))
    tokens = normalize_search_text(field_name).split()
    if tokens:
        aliases.add(" ".join(tokens))
        if len(tokens) > 1 and tokens[0] == "maximum":
            aliases.add(" ".join(tokens[1:]))
        if tokens[-1].endswith("s") and len(tokens[-1]) > 3:
            singular_tokens = list(tokens)
            singular_tokens[-1] = singular_tokens[-1][:-1]
            aliases.add(" ".join(singular_tokens))

    for alias in FIELD_WORDS.get(field_name, []):
        aliases.add(alias)
        aliases.add(normalize_search_text(alias))

    return {alias for alias in aliases if alias}


def normalize_db_input(db: Any) -> Any:
    if hasattr(db, "dataframe"):
        return db.dataframe
    return db


def infer_field_from_dataframe(df: Any, question: str) -> str | None:
    q_normalized = normalize_search_text(question)
    q_tokens = set(q_normalized.split())
    candidates: list[tuple[int, int, int, str]] = []

    for field_name in df.columns:
        if field_name in INTERNAL_COLUMNS:
            continue

        best_score = 0
        for alias in build_field_aliases(str(field_name)):
            alias_normalized = normalize_search_text(alias)
            alias_tokens = alias_normalized.split()
            if not alias_tokens:
                continue
            if alias_normalized in q_normalized:
                best_score = max(best_score, 100 + len(alias_tokens))
            elif set(alias_tokens).issubset(q_tokens):
                best_score = max(best_score, 50 + len(alias_tokens))

        if best_score:
            candidates.append((best_score, len(normalize_search_text(str(field_name)).split()), len(str(field_name)), str(field_name)))

    if not candidates:
        return None

    candidates.sort(
        key=lambda candidate: candidate[0],
        reverse=True,
    )


def infer_service_from_dataframe(df: Any, question: str) -> tuple[str, str] | None:
    q_normalized = normalize_search_text(question)
    q_tokens = set(q_normalized.split())

    candidates: list[tuple[int, int, int, str, str]] = []
    service_pairs = df[["Service", "Service_Abbv"]].fillna("").drop_duplicates()

    for _, row in service_pairs.iterrows():
        service_name = str(row["Service"]).strip()
        service_abbv = str(row["Service_Abbv"]).strip().upper()
        if not service_name and not service_abbv:
            continue

        for service_value in [value.strip() for value in re.split(r"[;/,]", service_name) if value.strip()]:
            service_normalized = normalize_search_text(service_value)
            if service_normalized and service_normalized == q_normalized:
                return service_name, service_abbv

    for _, row in service_pairs.iterrows():
        service_name = str(row["Service"]).strip()
        service_abbv = str(row["Service_Abbv"]).strip().upper()
        if not service_name and not service_abbv:
            continue

        for abbv_value in [value.strip().upper() for value in re.split(r"[;/,]", service_abbv) if value.strip()]:
            abb_normalized = normalize_search_text(abbv_value)
            if abb_normalized and abb_normalized == q_normalized:
                return service_name, service_abbv

    for _, row in service_pairs.iterrows():
        service_name = str(row["Service"]).strip()
        service_abbv = str(row["Service_Abbv"]).strip().upper()
        if not service_name and not service_abbv:
            continue

        service_names = [value.strip() for value in re.split(r"[;/,]", service_name) if value.strip()]
        service_abbvs = [value.strip().upper() for value in re.split(r"[;/,]", service_abbv) if value.strip()]

        for abbv_value in service_abbvs:
            best_score = 0
            has_token_match = False

            abb_normalized = normalize_search_text(abbv_value)
            abb_tokens = abb_normalized.split()
            if abb_tokens and set(abb_tokens).intersection(q_tokens):
                has_token_match = True
            if abb_normalized and abb_normalized in q_tokens:
                best_score = max(best_score, 120 + len(abb_tokens))
            elif abb_tokens and set(abb_tokens).issubset(q_tokens):
                best_score = max(best_score, 70 + len(abb_tokens))

            if best_score or has_token_match:
                candidates.append((best_score, len(normalize_search_text(abbv_value).split()), len(abbv_value), service_name, service_abbv))

        for service_value in service_names:
            best_score = 0
            has_token_match = False

            service_normalized = normalize_search_text(service_value)
            service_tokens = service_normalized.split()
            shared_tokens = set(service_tokens).intersection(q_tokens)
            if shared_tokens:
                has_token_match = True
            if service_normalized and service_normalized in q_normalized:
                best_score = max(best_score, 110 + len(service_tokens))
            elif service_tokens and set(service_tokens).issubset(q_tokens):
                best_score = max(best_score, 60 + len(service_tokens))
            elif shared_tokens:
                best_score = max(best_score, 40 + len(shared_tokens))

            if best_score or has_token_match:
                candidates.append((best_score, len(normalize_search_text(service_value).split()), len(service_value), service_name, service_abbv))

    if not candidates:
        return None

    candidates.sort(key=lambda c: c[0], reverse=True)
    candidates.sort(reverse=True)
    _, _, _, service_name, service_abbv = candidates[0]
    return service_name, service_abbv


def infer_service_from_parsed_value(df: Any, parsed_service: str | None) -> tuple[str, str] | None:
    if not parsed_service:
        return None

    parsed_normalized = normalize_search_text(parsed_service)
    service_pairs = df[["Service", "Service_Abbv"]].fillna("").drop_duplicates()
    for _, row in service_pairs.iterrows():
        service_name = str(row["Service"]).strip()
        service_abbv = str(row["Service_Abbv"]).strip().upper()
        if normalize_search_text(service_name) == parsed_normalized or normalize_search_text(service_abbv) == parsed_normalized:
            return service_name, service_abbv

    return None


def filter_rows_for_service(df: Any, service_match: tuple[str, str] | None) -> Any:
    if service_match is None:
        return df.iloc[0:0]

    service_name, service_abbv = service_match
    rows = df.iloc[0:0]
    if service_abbv:
        rows = df[df["Service_Abbv"].astype(str).str.upper().str.strip() == service_abbv]
    if rows.empty and service_name:
        rows = df[df["Service"].astype(str).str.strip().str.upper() == service_name.upper()]
    return rows


def search(db: Any, question: str) -> dict[str, Any]:
    df = normalize_db_input(db)
    parsed = parse_question(question)
    size = parsed["size"]

    # If parser didn't find a field, allow "spec" or "specification" queries
    q_lower = question.lower()
    wants_specification = bool(
        re.search(r"\bspecs?\b", q_lower)
        or re.search(r"\bspecifications?\b", q_lower)
    )

    field = None if wants_specification else (infer_field_from_dataframe(df, question) or parsed["field"])

    service_match = infer_service_from_dataframe(df, question) or infer_service_from_parsed_value(df, parsed["service"])

    if field is None and wants_specification:
        # Treat as a request for the full specification for the given service/size
        if service_match is None:
            return {"success": False, "message": "I cannot determine the piping service."}

        debug_rows = filter_rows_for_service(df, service_match)
        print(
            f"[search debug] question={question!r} "
            f"parsed_service={parsed['service']!r} "
            f"service_match={service_match!r} "
            f"filtered_row_count={len(debug_rows)}"
        )
        rows = debug_rows
        if rows.empty:
            return {"success": False, "message": "Service not found."}

        matched_rows = []
        for _, row in rows.iterrows():
            if size_matches(row["Size"], size):
                matched_rows.append(
                    {
                        "success": True,
                        "field": None,
                        "value": None,
                        "spec": row["Spec"],
                        "service": row["Service"],
                        "size_rule": row["Size"],
                        **{k: row.get(k, "") for k in df.columns if k not in INTERNAL_COLUMNS},
                    }
                )

        if matched_rows:
            if len(matched_rows) == 1:
                return matched_rows[0]
            return {
                "success": True,
                "field": None,
                "value": None,
                "message": f"Found {len(matched_rows)} matching specifications.",
                "results": matched_rows,
                "service": matched_rows[0].get("service", ""),
            }

        return {"success": False, "message": "No size rule matched."}

    if field is None:
        return {
            "success": False,
            "message": "I don't know what information you are requesting.",
        }

    if service_match is None:
        return {
            "success": False,
            "message": "I cannot determine the piping service.",
        }

    debug_rows = filter_rows_for_service(df, service_match)
    print(
        f"[search debug] question={question!r} "
        f"parsed_service={parsed['service']!r} "
        f"service_match={service_match!r} "
        f"filtered_row_count={len(debug_rows)}"
    )
    rows = debug_rows
    if rows.empty:
        return {
            "success": False,
            "message": "Service not found.",
        }

    for _, row in rows.iterrows():
        if size_matches(row["Size"], size):
            return {
                "success": True,
                "field": field,
                "value": row.get(field, ""),
                "spec": row["Spec"],
                "service": row["Service"],
                "size_rule": row["Size"],
            }

    return {
        "success": False,
        "message": "No size rule matched.",
    }
