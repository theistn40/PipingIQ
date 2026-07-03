"""
=========================================================
PipingIQ Professional v6.0
parser.py
Natural language parser for user questions.
=========================================================
"""

import re
from typing import Any

from database import _parse_numeric_size

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
    "Support Spacing": ["support", "supports", "support spacing", "hanger spacing"],
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


def _extract_size_from_question(question: str) -> float | None:
    normalized = str(question).lower()
    normalized = re.sub(r"(?<=\d)\s*(?:\"|''|inches|inch|in\.)\b", "", normalized)
    normalized = re.sub(r"(?<=\d)-(?=inch|inches|in\b)", " ", normalized)

    size_patterns = [
        r"\b\d+\s+\d+/\d+\b",
        r"\b\d+-\d+/\d+\b",
        r"\b\d+/\d+\b",
        r"\b\d+(?:\.\d+)?\b",
    ]
    for pattern in size_patterns:
        match = re.search(pattern, normalized)
        if not match:
            continue
        try:
            return _parse_numeric_size(match.group(0))
        except ValueError:
            continue
    return None


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

    result["size"] = _extract_size_from_question(q)

    wordset = set(words)
    for pattern, service in SERVICE_ALIASES.items():
        if all(part in wordset for part in pattern):
            result["service"] = service
            break

    return result
