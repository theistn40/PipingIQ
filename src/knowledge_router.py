"""
=========================================================
PipingIQ Professional v6.0
knowledge_router.py
Route user queries to the correct engine.
=========================================================
"""

from typing import Any

from search_engine import (
    filter_rows_for_service,
    infer_service_from_dataframe,
    infer_service_from_parsed_value,
    normalize_db_input,
    search,
)
from parser import parse_question
from database import size_matches


MODULE_MAP = {
    "Pipe Specifications": "specifications",
    "Codes & Standards": "knowledge",
    "Pipe Supports": "supports",
    "Dimensions & Engineering Data": "data",
    "Material Takeoffs": "takeoffs",
    "Cost Estimating": "estimating",
    "AI Search & Knowledge Base": "ai",
    "Engineering Calculations": "calculations",
}


def route_query(question: str, selected_module: str, db: Any) -> dict[str, Any]:
    module_key = MODULE_MAP.get(selected_module, "specifications")

    if module_key == "specifications":
        return search(db, question)

    if module_key == "knowledge":
        df = normalize_db_input(db)
        parsed = parse_question(question)
        service_match = infer_service_from_dataframe(df, question) or infer_service_from_parsed_value(df, parsed.get("service"))
        if service_match is None:
            return {"success": False, "message": "I cannot determine the piping service."}

        rows = filter_rows_for_service(df, service_match)
        if rows.empty:
            return {"success": False, "message": "Service not found."}

        requested_size = parsed.get("size")
        matched_rows = []
        for _, row in rows.iterrows():
            if not size_matches(row["Size"], requested_size):
                continue
            pipe_value = str(row.get("Pipe", "")).strip()
            if not pipe_value:
                continue
            matched_rows.append(
                {
                    "field": "Pipe",
                    "value": pipe_value,
                    "spec": row.get("Spec", ""),
                    "service": row.get("Service", ""),
                    "service_abbv": row.get("Service_Abbv", ""),
                    "size_rule": row.get("Size", ""),
                }
            )

        if not matched_rows:
            return {"success": False, "message": "No Pipe values found for that service."}

        return {
            "success": True,
            "message": f"Found {len(matched_rows)} Pipe value(s).",
            "results": matched_rows,
        }

    return {
        "success": False,
        "message": (
            f"{selected_module} is not yet implemented. "
            "Please use Pipe Specifications for Version 1."
        ),
    }
