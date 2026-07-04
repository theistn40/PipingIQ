"""
=========================================================
PipingIQ Professional v6.0
config.py
---------------------------------------------------------
Global configuration and application paths.
=========================================================
"""

import base64
from pathlib import Path

# -------------------------------------------------------
# Root
# -------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent

# -------------------------------------------------------
# Directories
# -------------------------------------------------------

ASSETS = ROOT / "assets"
CALCULATIONS = ROOT / "calculations"
DATA = ROOT / "data"
DATABASES = ROOT / "databases"
KNOWLEDGE = ROOT / "knowledge"
OUTPUT = ROOT / "output"
PROJECTS = ROOT / "projects"
SRC = ROOT / "src"

# -------------------------------------------------------
# Primary Engineering Database
# -------------------------------------------------------

PIPE_SPEC_DATABASE = DATA / "PipeSpec_Master.xlsx"

# -------------------------------------------------------
# Future Databases
# -------------------------------------------------------

PIPE_DIMENSIONS_DB = DATABASES / "PipeDimensions.xlsx"
VALVES_DB = DATABASES / "Valves.xlsx"
FLANGES_DB = DATABASES / "Flanges.xlsx"
FITTINGS_DB = DATABASES / "Fittings.xlsx"
SUPPORTS_DB = DATABASES / "Supports.xlsx"
MATERIALS_DB = DATABASES / "Materials.xlsx"
PRESSURE_DB = DATABASES / "PressureRatings.xlsx"

# -------------------------------------------------------
# Knowledge Library
# -------------------------------------------------------

KNOWLEDGE_LIBRARY = KNOWLEDGE

# -------------------------------------------------------
# Output
# -------------------------------------------------------

REPORT_OUTPUT = OUTPUT

# -------------------------------------------------------
# Application
# -------------------------------------------------------

APP_NAME = "PipingIQ Professional"
VERSION = "6.0"
AUTHOR = "Todd Theis"
PAGE_TITLE = "PipingIQ Professional"

# -------------------------------------------------------
# Display
# -------------------------------------------------------

WINDOW_TITLE = f"{APP_NAME} {VERSION}"

LOGO = ASSETS / "PipingIQ_Logo.png"
BACKGROUND = ASSETS / "Banner.png"


def get_background_image_base64():
    """Load background image and encode as base64 data URI."""
    try:
        bg_path = ASSETS / "Banner.png"
        if bg_path.exists():
            with open(bg_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode()
            return f"data:image/png;base64,{img_data}"
    except Exception:
        pass
    # Return empty string if image not found
    return ""


BACKGROUND_DATA_URI = get_background_image_base64()

BUTTON_COLOR = "#0F4C93"
BUTTON_TEXT_COLOR = "#FFFFFF"
CARD_BACKGROUND = "#10223E"
LABEL_COLOR = "#A8D1FF"
VALUE_COLOR = "#E9F4FF"
ANSWER_COLOR = "#A2D9FF"
TEXT_COLOR = "#EDF5FF"
SECTION_HEADER_COLOR = "#69A5FF"
