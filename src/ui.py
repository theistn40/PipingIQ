"""
PipingIQ engineering test interface.

This module is intentionally limited to Streamlit presentation. Backend search,
database access, parsing, and routing remain delegated to the existing modules.
"""

from __future__ import annotations

import html
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from config import APP_NAME, DATA_IMPORTS, KNOWLEDGE_LIBRARY, VERSION


NAVIGATION_ITEMS = [
    "Home",
    "Engineering Reference",
    "Engineering Calculations",
    "Pipe Supports",
    "Pipe Stress",
    "Estimating",
    "Projects",
    "AI Assistant",
    "Settings",
]

WORKSPACE_TABS = [
    "Specification",
    "Dimensions",
    "Calculations",
    "Standards",
    "Sources",
    "Notes",
]

ROUTE_MODULE_BY_NAV = {
    "Home": "Pipe Specifications",
    "Engineering Reference": "Pipe Specifications",
    "Engineering Calculations": "Engineering Calculators",
    "Pipe Supports": "Pipe Supports",
    "Pipe Stress": "Pipe Stress",
    "Estimating": "Estimating",
    "Projects": "Projects",
    "AI Assistant": "Knowledge Library",
    "Settings": "Settings",
}

PIPE_SPECIFICATIONS_MODULE = "Pipe Specifications"

INTERNAL_FIELDS = {
    "success",
    "results",
    "message",
    "library_name",
    "library_type",
    "client_name",
    "project_name",
    "import_batch_id",
    "is_active",
}

DISPLAY_LABELS = {
    "spec": "Specification",
    "Spec": "Specification",
    "service": "Service",
    "Service": "Service",
    "service_abbv": "Service Abbreviation",
    "Service_Abbv": "Service Abbreviation",
    "size_rule": "Size Rule",
    "Size": "Size Rule",
    "Fitting": "Fittings",
    "MAXIMUM PRESSURE (PSI)": "Maximum Pressure",
    "MAXIMUM TEMPERATURE (F)": "Maximum Temperature",
}

FULL_SPEC_EXCLUDED_FIELDS = {
    "service_abbv",
    "Service_Abbv",
    "size_rule",
    "Size",
    "field",
    "value",
}

SPEC_CODE_PATTERN = re.compile(r"^[A-Za-z0-9]+(?:[-_/][A-Za-z0-9]+)+$")


def setup_page() -> None:
    st.set_page_config(page_title=APP_NAME, layout="wide", initial_sidebar_state="collapsed")
    st.markdown(
        """
        <style>
            #MainMenu, footer, header[data-testid="stHeader"],
            [data-testid="stDecoration"], [data-testid="stToolbar"],
            [data-testid="collapsedControl"] {
                display: none !important;
            }

            .stApp {
                background: #f4f6f8;
                color: #17212b;
            }

            .block-container {
                max-width: 1500px;
                padding: 1.25rem 1.5rem 1rem;
            }

            h1, h2, h3, p, label {
                color: #17212b !important;
            }

            .piq-title {
                text-align: center;
                padding: 0.35rem 0 0.2rem;
                border-bottom: 1px solid #d4dae1;
                margin-bottom: 0.75rem;
            }

            .piq-title h1 {
                margin: 0;
                font-size: 2rem;
                line-height: 1.15;
                font-weight: 700;
            }

            .piq-title p {
                margin: 0.2rem 0 0.5rem;
                color: #52616f !important;
                font-size: 0.95rem;
            }

            .section-label {
                color: #334252;
                font-weight: 700;
                font-size: 0.85rem;
                letter-spacing: 0.02em;
                margin: 0.15rem 0 0.4rem;
            }

            .stButton > button {
                border-radius: 6px !important;
                border: 1px solid #b9c3cf !important;
                background: #ffffff !important;
                color: #17212b !important;
                font-weight: 600 !important;
            }

            .stButton > button:hover {
                border-color: #386fa4 !important;
                color: #173f66 !important;
            }

            div[data-testid="stTextInput"] input {
                border-radius: 6px;
                border: 1px solid #aeb8c3;
                background: #ffffff;
                color: #17212b;
            }

            div[data-testid="stVerticalBlockBorderWrapper"] {
                border-color: #d4dae1 !important;
                border-radius: 8px !important;
                background: #ffffff;
            }

            .status-bar {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 0.75rem;
                margin-top: 0.85rem;
                padding: 0.75rem;
                border: 1px solid #d4dae1;
                border-radius: 8px;
                background: #ffffff;
                color: #17212b;
                font-size: 0.85rem;
            }

            .status-item strong {
                color: #52616f;
                display: block;
                font-size: 0.72rem;
                text-transform: uppercase;
                letter-spacing: 0.04em;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<[^>]*>", "", text)
    return " ".join(text.replace("\xa0", " ").split())


def _result_to_mapping(result: Any) -> dict[str, Any]:
    if isinstance(result, Mapping):
        return dict(result)
    if hasattr(result, "as_dict"):
        return dict(result.as_dict())
    try:
        return dict(result)
    except Exception:
        return {"Answer": result}


def _display_label(key: str) -> str:
    cleaned = _clean_text(key)
    return DISPLAY_LABELS.get(cleaned, DISPLAY_LABELS.get(key, cleaned.replace("_", " ").title()))


def _is_full_spec_result(data: Mapping[str, Any]) -> bool:
    specification = _clean_text(data.get("spec") or data.get("Spec"))
    service = _clean_text(data.get("service") or data.get("Service"))
    if not specification or not service:
        return False

    for key, value in data.items():
        if key in INTERNAL_FIELDS or key in FULL_SPEC_EXCLUDED_FIELDS:
            continue
        if str(key).startswith("Unnamed") or key in {"spec", "Spec", "service", "Service"}:
            continue
        if _clean_text(value):
            return True
    return False


def _result_rows(result: Any) -> list[dict[str, str]]:
    data = _result_to_mapping(result)
    rows: list[dict[str, str]] = []

    if _is_full_spec_result(data):
        specification = _clean_text(data.get("spec") or data.get("Spec"))
        service = _clean_text(data.get("service") or data.get("Service"))
        if specification:
            rows.append({"Field": _display_label("spec"), "Value": specification})
        if service:
            rows.append({"Field": _display_label("service"), "Value": service})

        for key, value in data.items():
            if key in INTERNAL_FIELDS or key in FULL_SPEC_EXCLUDED_FIELDS:
                continue
            if str(key).startswith("Unnamed") or key in {"spec", "Spec", "service", "Service"}:
                continue
            cleaned = _clean_text(value)
            if cleaned:
                rows.append({"Field": _display_label(str(key)), "Value": cleaned})

        return rows or [{"Field": "Answer", "Value": "No displayable fields returned."}]

    primary_fields = [
        (_display_label("spec"), data.get("spec") or data.get("Spec")),
        (_display_label("service"), data.get("service") or data.get("Service")),
        (_display_label("service_abbv"), data.get("service_abbv") or data.get("Service_Abbv")),
        (_display_label("size_rule"), data.get("size_rule") or data.get("Size")),
        ("Requested Field", data.get("field")),
        ("Answer", data.get("value")),
    ]

    for label, value in primary_fields:
        cleaned = _clean_text(value)
        if cleaned:
            rows.append({"Field": label, "Value": cleaned})

    for key, value in data.items():
        if key in INTERNAL_FIELDS:
            continue
        if str(key).startswith("Unnamed"):
            continue
        if key in {"spec", "Spec", "service", "Service", "service_abbv", "Service_Abbv", "size_rule", "Size", "field", "value"}:
            continue
        cleaned = _clean_text(value)
        if cleaned:
            rows.append({"Field": _display_label(str(key)), "Value": cleaned})

    return rows or [{"Field": "Answer", "Value": "No displayable fields returned."}]


def _results_from_response(response: Mapping[str, Any] | None) -> list[Any]:
    if not response:
        return []
    results = response.get("results")
    if isinstance(results, list):
        return results
    if results:
        return [results]
    if response.get("success"):
        return [response]
    return []


def _query_result_to_response(result: Any) -> dict[str, Any]:
    specifications = list(getattr(result, "specifications", []) or [])
    message = _clean_text(getattr(result, "message", ""))
    if not specifications:
        return {"success": False, "message": message or "No result."}

    normalized_results: list[dict[str, Any]] = []
    for specification in specifications:
        data = _result_to_mapping(specification)
        normalized_results.append(
            {
                "spec": data.get("Spec") or data.get("spec"),
                "service": data.get("Service") or data.get("service"),
                "service_abbv": data.get("Service_Abbv") or data.get("service_abbv"),
                "size_rule": data.get("Size") or data.get("size_rule"),
                **{
                    str(key): value
                    for key, value in data.items()
                    if key not in {"Spec", "spec", "Service", "service", "Service_Abbv", "service_abbv", "Size", "size_rule"}
                },
            }
        )

    if len(normalized_results) == 1:
        response = {"success": True, **normalized_results[0]}
        if message:
            response["message"] = message
        return response

    response = {"success": True, "results": normalized_results}
    if message:
        response["message"] = message
    return response


def _lookup_pipe_specification(question: str, db: Any) -> dict[str, Any]:
    from knowledge_router import route_query

    query_text = " ".join(question.split())
    direct_response = route_query(query_text, PIPE_SPECIFICATIONS_MODULE, db)
    if _results_from_response(direct_response):
        return direct_response

    service_lookup_response = _query_result_to_response(db.query(service=query_text))
    if _results_from_response(service_lookup_response):
        return service_lookup_response

    spec_lookup_response = _query_result_to_response(db.query(spec=query_text))
    if _results_from_response(spec_lookup_response):
        return spec_lookup_response

    specification_response = route_query(f"pipe spec for {query_text}", PIPE_SPECIFICATIONS_MODULE, db)
    if _results_from_response(specification_response):
        return specification_response

    if SPEC_CODE_PATTERN.fullmatch(query_text):
        return spec_lookup_response
    if service_lookup_response.get("message"):
        return service_lookup_response
    if specification_response.get("message"):
        return specification_response
    return direct_response


def _render_title() -> None:
    st.markdown(
        """
        <div class="piq-title">
            <h1>PipingIQ</h1>
            <p>Engineering Test Interface</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_search_bar() -> tuple[str, bool, bool]:
    st.markdown('<div class="section-label">Search</div>', unsafe_allow_html=True)
    input_col, search_col, calc_col = st.columns([8, 1.4, 1.8], vertical_alignment="bottom")
    with input_col:
        question = st.text_input(
            "Search",
            key="search_box",
            label_visibility="collapsed",
            placeholder='Ask a pipe specification question, for example: What flange do I use for 3" STM LP?',
        )
    with search_col:
        search_clicked = st.button("Search", key="search_button", use_container_width=True)
    with calc_col:
        calculations_clicked = st.button("Calculations", key="calculations_button", use_container_width=True)
    return question or "", search_clicked, calculations_clicked


def _render_navigation() -> str:
    st.markdown('<div class="section-label">Navigation</div>', unsafe_allow_html=True)
    selected = st.radio(
        "Navigation",
        NAVIGATION_ITEMS,
        key="navigation",
        label_visibility="collapsed",
    )
    return str(selected)


def _render_workspace(response: Mapping[str, Any] | None) -> None:
    st.markdown('<div class="section-label">Engineering Workspace</div>', unsafe_allow_html=True)
    tabs = st.tabs(
        WORKSPACE_TABS,
        default=st.session_state.get("workspace_tab", WORKSPACE_TABS[0]),
        key="engineering_workspace_tabs",
        on_change="rerun",
    )
    results = _results_from_response(response)

    with tabs[0]:
        if response and not response.get("success"):
            st.info(_clean_text(response.get("message", "No result.")))
        elif results:
            for index, result in enumerate(results, start=1):
                if len(results) > 1:
                    st.caption(f"Result {index}")
                st.dataframe(
                    pd.DataFrame(_result_rows(result)),
                    hide_index=True,
                    use_container_width=True,
                )
        else:
            st.info("Search results will appear here.")

    with tabs[1]:
        dimension_results = [
            result for result in results if _clean_text(_result_to_mapping(result).get("Item"))
        ]
        if dimension_results:
            for result in dimension_results:
                st.dataframe(pd.DataFrame(_result_rows(result)), hide_index=True, use_container_width=True)
        else:
            st.info("Dimension query results will appear here.")

    with tabs[2]:
        st.info("Calculation outputs will appear here when supported by the backend.")

    with tabs[3]:
        st.info("Standards references will appear here when returned by the backend.")

    with tabs[4]:
        if results:
            source_rows = []
            for result in results:
                data = _result_to_mapping(result)
                source_rows.append(
                    {
                        "Library": _clean_text(data.get("library_name")),
                        "Type": _clean_text(data.get("library_type")),
                        "Project": _clean_text(data.get("project_name")),
                        "Import Batch": _clean_text(data.get("import_batch_id")),
                    }
                )
            st.dataframe(pd.DataFrame(source_rows), hide_index=True, use_container_width=True)
        else:
            st.info("Source information will appear here.")

    with tabs[5]:
        st.text_area("Notes", key="engineering_notes", label_visibility="collapsed", height=180)


def _save_upload(uploaded_file: Any) -> Path:
    DATA_IMPORTS.mkdir(parents=True, exist_ok=True)
    target = DATA_IMPORTS / Path(uploaded_file.name).name
    target.write_bytes(uploaded_file.getbuffer())
    return target


def _render_upload_panel(db: Any) -> None:
    st.markdown('<div class="section-label">Upload</div>', unsafe_allow_html=True)
    with st.container(border=True):
        pdf_file = st.file_uploader("Upload PDF", type=["pdf"], key="pdf_upload")
        if pdf_file is not None:
            saved_pdf = _save_upload(pdf_file)
            st.info(f"PDF staged: {saved_pdf.name}")

        excel_file = st.file_uploader("Upload Excel", type=["xls", "xlsx"], key="excel_upload")
        dataset_name = st.selectbox(
            "Excel Dataset",
            ["pipe_specs", "service_aliases", "field_aliases", "standards_references"],
            key="excel_dataset",
        )
        if excel_file is not None and st.button("Import Excel", key="import_excel", use_container_width=True):
            from database import import_excel_dataset, load_runtime_dataframe

            saved_excel = _save_upload(excel_file)
            try:
                batch_id = import_excel_dataset(dataset_name, saved_excel, sqlite_path=db.sqlite_path)
                dataframe = load_runtime_dataframe(db.sqlite_path)
                db._build_indexes(dataframe)
                db._df = dataframe
                st.success(f"Imported {dataset_name}: {batch_id}")
            except Exception as exc:
                st.error(f"Excel import failed: {_clean_text(exc)}")


def _render_status_bar(db: Any, selected_nav: str) -> None:
    try:
        stats = db.statistics()
        database_status = f"{stats.get('record_count', 0)} records"
    except Exception:
        database_status = "Unavailable"

    knowledge_status = "Available" if KNOWLEDGE_LIBRARY.exists() else "Missing"
    project = selected_nav or "Home"
    st.markdown(
        f"""
        <div class="status-bar">
            <div class="status-item"><strong>Database</strong>{_clean_text(database_status)}</div>
            <div class="status-item"><strong>Knowledge Base</strong>{_clean_text(knowledge_status)}</div>
            <div class="status-item"><strong>Version</strong>{_clean_text(VERSION)}</div>
            <div class="status-item"><strong>Current Project</strong>{_clean_text(project)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def run_application() -> None:
    from database import DatabaseError, DatabaseManager

    setup_page()
    _render_title()

    try:
        db = DatabaseManager()
    except DatabaseError as exc:
        st.error(str(exc))
        st.stop()
    except Exception as exc:
        st.error(f"Unable to initialize the database: {exc}")
        st.stop()

    if "last_response" not in st.session_state:
        st.session_state["last_response"] = None

    question, search_clicked, calculations_clicked = _render_search_bar()
    st.divider()

    if calculations_clicked:
        st.session_state["navigation"] = "Engineering Calculations"

    if search_clicked:
        if not question.strip():
            st.session_state["last_response"] = {
                "success": False,
                "message": "Please enter an engineering question before searching.",
            }
        else:
            st.session_state["workspace_tab"] = "Specification"
            st.session_state["last_response"] = _lookup_pipe_specification(question, db)

    nav_col, workspace_col, upload_col = st.columns([1.25, 3.7, 1.55], gap="large")
    with nav_col:
        selected_nav = _render_navigation()

    with workspace_col:
        _render_workspace(st.session_state.get("last_response"))

    with upload_col:
        _render_upload_panel(db)

    _render_status_bar(db, selected_nav)
