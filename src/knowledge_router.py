"""
=========================================================
PipingIQ Professional v6.0
knowledge_router.py
Phase 1 module routing.
=========================================================
"""

from typing import Any

from search_engine import search

PIPE_SPECIFICATIONS_MODULE = "Pipe Specifications"


def route_query(question: str, selected_module: str, db: Any) -> dict[str, Any]:
    if selected_module == PIPE_SPECIFICATIONS_MODULE:
        return search(db, question)

    return {
        "success": False,
        "message": (
            f"{selected_module} is coming soon. "
            "Phase 1 supports Standard Pipe Specification lookup only."
        ),
    }
