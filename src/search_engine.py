"""
=========================================================
PipingIQ V5.1
search_engine.py
Engineering Query Engine
=========================================================
"""

import re
from typing import Any

from database import size_matches


FIELD_WORDS = {
    "Pipe": ["pipe"],
    "Schedule": ["schedule", "sch"],
    "Coupling": ["coupling", "couplings"],
    "Fitting": ["fitting", "fittings"],
    "Joint": ["joint", "joints"],
    "Valve": ["valve", "valves"],
    "Flange": ["flange", "flanges"],
    "Bolts": ["bolt", "bolts"],
    "Clamps": ["clamp", "clamps"],
    "SOLDER": ["solder"],
    "Gasket": ["gasket", "gaskets"],
    "Insulation": ["insulation"],
    "Support Spacing": [
        "support",
        "supports",
        "support spacing",
        "hanger spacing",
    ],
    "Test Pressure": ["test pressure", "pressure test"],
    "Flexible Hose": ["flexible hose", "hose"],
    "Thread Compound": ["thread compound", "pipe dope", "thread sealant"],
    "Strainers": ["strainer", "strainers"],
    "Traps": ["trap", "traps", "steam trap"],
    "o'lets": ["olet", "olets", "weldolet", "sockolet", "threadolet"],
    "90 deg elbow": ["90", "90 elbow", "90 degree"],
    "45 deg elbow": ["45", "45 elbow", "45 degree"],
    "Tee": ["tee", "tees"],
}

SERVICE_ALIASES = {
    ("stm", "lp"): "STM LP",
    ("lp", "stm"): "STM LP",
    ("steam", "low", "pressure"): "STM LP",
    ("low", "pressure", "steam"): "STM LP",
    ("steam", "lp"): "STM LP",
    ("lp", "steam"): "STM LP",
    ("chws",): "CHWS",
    ("chilled", "water", "supply"): "CHWS",
    ("chwr",): "CHWR",
    ("chilled", "water", "return"): "CHWR",
    ("ca",): "CA",
    ("compressed", "air"): "CA",
    ("iw",): "IW",
    ("instrument", "water"): "IW",
}


def parse_question(question: str) -> dict[str, Any]:
    q = question.lower()
    words = re.findall(r"[a-z0-9\.]+", q)

    result = {
        "field": None,
        "service": None,
        "size": None,
    }

    for field, keys in FIELD_WORDS.items():
        for key in keys:
            if key in q:
                result["field"] = field
                break
        if result["field"]:
            break

    match = re.search(r"(\d+(?:\.\d+)?)", q)
    if match:
        result["size"] = float(match.group(1))

    wordset = set(words)
    for pattern, service in SERVICE_ALIASES.items():
        if all(part in wordset for part in pattern):
            result["service"] = service
            break

    return result


def normalize_db_input(db: Any) -> Any:
    if hasattr(db, "dataframe"):
        return db.dataframe
    return db


def search(db: Any, question: str) -> dict[str, Any]:
    df = normalize_db_input(db)
    parsed = parse_question(question)
    field = parsed["field"]
    service = parsed["service"]
    size = parsed["size"]

    if field is None:
        return {
            "success": False,
            "message": "I don't know what information you are requesting.",
        }

    if service is None:
        return {
            "success": False,
            "message": "I cannot determine the piping service.",
        }

    rows = df[df["Service_Abbv"].str.upper() == service]
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
