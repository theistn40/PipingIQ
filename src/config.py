"""
Central configuration for the PipingIQ Phase 1 application.

This module defines the frozen application paths, runtime file locations,
application metadata, and UI presentation constants required by the approved
PipingIQ architecture. It intentionally contains configuration data only.
"""

from __future__ import annotations

import base64
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parent.parent

# Frozen project directories
ASSETS: Path = ROOT / "assets"
CALCULATIONS: Path = ROOT / "calculations"
DATA: Path = ROOT / "data"
DATABASES: Path = ROOT / "databases"
KNOWLEDGE: Path = ROOT / "knowledge"
OUTPUT: Path = ROOT / "output"
PROJECTS: Path = ROOT / "projects"
SRC: Path = ROOT / "src"

# Controlled subdirectories from the approved blueprint
DATABASE_BACKUPS: Path = DATABASES / "backups"
DATA_IMPORTS: Path = DATA / "imports"
DATA_REJECTED: Path = DATA / "rejected"
IMPORT_LOG_OUTPUT: Path = OUTPUT / "logs" / "imports"

# Engineering master and runtime database locations
PIPE_SPEC_MASTER_WORKBOOK: Path = DATA / "PipeSpec_Master.xlsx"
RUNTIME_DATABASE: Path = DATABASES / "PipingIQ.db"

# Backward-compatible aliases currently used by existing modules
PIPE_SPEC_DATABASE: Path = PIPE_SPEC_MASTER_WORKBOOK
SQLITE_DATABASE: Path = RUNTIME_DATABASE

# Future-ready workbook references retained for planned expansion
VALVES_DB: Path = DATABASES / "Valves.xlsx"
FLANGES_DB: Path = DATABASES / "Flanges.xlsx"
FITTINGS_DB: Path = DATABASES / "Fittings.xlsx"
SUPPORTS_DB: Path = DATABASES / "Supports.xlsx"
MATERIALS_DB: Path = DATABASES / "Materials.xlsx"
PRESSURE_DB: Path = DATABASES / "PressureRatings.xlsx"

# Knowledge and output aliases used by the current application
KNOWLEDGE_LIBRARY: Path = KNOWLEDGE
REPORT_OUTPUT: Path = OUTPUT

# Application metadata
APP_NAME: str = "PipingIQ"
VERSION: str = "1.0.0"
AUTHOR: str = "Todd Theis"
PAGE_TITLE: str = APP_NAME
WINDOW_TITLE: str = f"{APP_NAME} {VERSION}"

# Visual asset paths
LOGO: Path = ASSETS / "PipingIQ_Logo.png"
BANNER_IMAGE: Path = ASSETS / "banner.png"
BACKGROUND: Path = BANNER_IMAGE


def _build_image_data_uri(image_path: Path) -> str:
    """Return a PNG image as a base64 data URI when the asset exists."""
    if not image_path.is_file():
        return ""

    encoded_bytes = base64.b64encode(image_path.read_bytes())
    encoded_text = encoded_bytes.decode("ascii")
    return f"data:image/png;base64,{encoded_text}"


BACKGROUND_DATA_URI: str = _build_image_data_uri(BACKGROUND)

# UI palette
BUTTON_COLOR: str = "#0F4C93"
BUTTON_TEXT_COLOR: str = "#FFFFFF"
CARD_BACKGROUND: str = "#10223E"
LABEL_COLOR: str = "#A8D1FF"
VALUE_COLOR: str = "#E9F4FF"
ANSWER_COLOR: str = "#A2D9FF"
TEXT_COLOR: str = "#EDF5FF"
SECTION_HEADER_COLOR: str = "#69A5FF"

__all__ = [
    "ANSWER_COLOR",
    "APP_NAME",
    "ASSETS",
    "AUTHOR",
    "BACKGROUND",
    "BANNER_IMAGE",
    "BACKGROUND_DATA_URI",
    "BUTTON_COLOR",
    "BUTTON_TEXT_COLOR",
    "CALCULATIONS",
    "CARD_BACKGROUND",
    "DATA",
    "DATABASE_BACKUPS",
    "DATABASES",
    "DATA_IMPORTS",
    "DATA_REJECTED",
    "FITTINGS_DB",
    "FLANGES_DB",
    "IMPORT_LOG_OUTPUT",
    "KNOWLEDGE",
    "KNOWLEDGE_LIBRARY",
    "LABEL_COLOR",
    "LOGO",
    "MATERIALS_DB",
    "OUTPUT",
    "PAGE_TITLE",
    "PIPE_SPEC_DATABASE",
    "PIPE_SPEC_MASTER_WORKBOOK",
    "PRESSURE_DB",
    "PROJECTS",
    "REPORT_OUTPUT",
    "ROOT",
    "RUNTIME_DATABASE",
    "SECTION_HEADER_COLOR",
    "SRC",
    "SQLITE_DATABASE",
    "SUPPORTS_DB",
    "TEXT_COLOR",
    "VALVES_DB",
    "VALUE_COLOR",
    "VERSION",
    "WINDOW_TITLE",
]
