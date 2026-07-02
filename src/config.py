"""
=========================================================
PipingIQ Professional v6.0
config.py
---------------------------------------------------------
Global configuration and application paths.
=========================================================
"""

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

# -------------------------------------------------------
# Display
# -------------------------------------------------------

WINDOW_TITLE = f"{APP_NAME} {VERSION}"

LOGO = ASSETS / "PipingIQ_Logo.png"

BACKGROUND = ASSETS / "background.jpg"