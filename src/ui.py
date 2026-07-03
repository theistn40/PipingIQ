"""
=========================================================
PipingIQ Professional v6.0
User Interface Layer
=========================================================
"""

import streamlit as st
from collections.abc import Mapping
from config import (
    APP_NAME,
    BACKGROUND,
    BUTTON_COLOR,
    BUTTON_TEXT_COLOR,
    CARD_BACKGROUND,
    LABEL_COLOR,
    VALUE_COLOR,
    ANSWER_COLOR,
    TEXT_COLOR,
    SECTION_HEADER_COLOR,
    VERSION,
)

MODULES = [
    "Pipe Specifications",
    "Codes & Standards",
    "Pipe Supports",
    "Dimensions & Engineering Data",
    "Material Takeoffs",
    "Cost Estimating",
    "AI Search & Knowledge Base",
    "Engineering Calculations",
]


def setup_page():
    st.set_page_config(page_title=APP_NAME, layout="wide")
    st.markdown(
        f"""
        <style>
            .stApp {{
                background: radial-gradient(circle at top, rgba(18, 42, 86, 0.92), rgba(3, 8, 22, 0.96) 60%);
                color: {TEXT_COLOR};
            }}
            .page-background {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-image: url('{BACKGROUND.as_posix()}');
                background-size: cover;
                background-position: center;
                opacity: 0.14;
                z-index: -1;
            }}
            .module-button {{
                background-color: {BUTTON_COLOR};
                color: {BUTTON_TEXT_COLOR};
                border-radius: 16px;
                padding: 14px 18px;
                margin-bottom: 10px;
                width: 100%;
                text-align: left;
                font-weight: 600;
                border: 1px solid rgba(255,255,255,0.08);
            }}
            /* Streamlit native buttons global override to ensure readable text */
            .stButton>button, .stButton > button {{
                background-color: {BUTTON_COLOR} !important;
                color: {BUTTON_TEXT_COLOR} !important;
                border-radius: 12px !important;
                padding: 8px 12px !important;
                border: 1px solid rgba(255,255,255,0.08) !important;
                box-shadow: none !important;
            }}
            .stButton>button:hover, .stButton > button:hover {{
                background-color: #1B5DC8 !important;
                color: {BUTTON_TEXT_COLOR} !important;
            }}
            /* file uploader and other buttons */
            div.stButton > button[title] {{
                background-color: {BUTTON_COLOR} !important;
                color: {BUTTON_TEXT_COLOR} !important;
            }}
            .module-button:hover {{
                background-color: #1B5DC8;
            }}
            .selected-module {{
                background-color: #173F73;
                border: 1px solid #70A9FF;
            }}
            .top-panel {{
                border-radius: 24px;
                background: rgba(5, 18, 41, 0.95);
                padding: 26px;
                border: 1px solid rgba(255,255,255,0.08);
            }}
            .answer-card {{
                border-radius: 24px;
                background: rgba(255,255,255,0.06);
                padding: 24px;
                border: 1px solid rgba(255,255,255,0.12);
            }}
            .section-title {{
                color: {SECTION_HEADER_COLOR};
                margin-bottom: 8px;
            }}
            .small-muted {{
                color: rgba(255,255,255,0.72);
                font-size: 14px;
            }}
        </style>
        <div class="page-background"></div>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    st.markdown(
        f"""
        <div style="padding:24px 0 12px 0; max-width:100%;">
            <div style="display:flex; align-items:flex-start; justify-content:space-between; flex-wrap:wrap; gap:16px;">
                <div style="max-width:760px;">
                    <h1 style="color:white; margin:0; letter-spacing:0.06em;">{APP_NAME}</h1>
                    <p style="color:#C6D9FF; margin:8px 0 0 0; font-size:18px; line-height:1.5;">
                        Engineering Intelligence Platform for piping design, specifications, codes, estimation, and engineering knowledge.
                    </p>
                    <p style="color:#7EA7DD; margin:10px 0 0 0; font-size:14px; letter-spacing:0.08em;">
                        ONE APPLICATION. COMPLETE PIPING ENGINEERING KNOWLEDGE.
                    </p>
                </div>
                <div style="min-width:220px; text-align:right;">
                    <div style="display:inline-block; background: rgba(255,255,255,0.08); padding:12px 18px; border-radius:16px; border:1px solid rgba(255,255,255,0.12);">
                        <strong style="color:#E4F2FF;">VERSION {VERSION}</strong><br>
                        <span style="color:#B8D7FF; font-size:13px;">BUILD 2026.06</span>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_module_card(title: str, description: str, status: str = "Coming Soon"):
    st.markdown(
        f"""
        <div style="
            background: rgba(255,255,255,0.05);
            padding:18px;
            border-radius:18px;
            border:1px solid rgba(255,255,255,0.12);
            margin-top:18px;
        ">
            <h3 style='color:{ANSWER_COLOR}; margin:0 0 8px 0;'>{title}</h3>
            <p style='color:rgba(255,255,255,0.78); margin:0 0 12px 0;'>{description}</p>
            <span style='display:inline-block; color:{VALUE_COLOR}; font-weight:700; padding:6px 12px; border-radius:999px; background: rgba(162,217,255,0.12);'>{status}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_module_details(selected_module: str):
    if selected_module == "Pipe Specifications":
        render_module_card(
            "Pipe Specifications",
            "Search the pipe specification database by service, size, and engineering field. This is the Version 1 flagship feature.",
            status="Active",
        )
    elif selected_module == "Codes & Standards":
        render_module_card(
            "Codes & Standards",
            "Lookup service-related standards data from PipeSpec_Master using Service and Service_Abbv, returning Pipe values for matching rows.",
            status="Active",
        )
    elif selected_module == "Pipe Supports":
        render_module_card(
            "Pipe Supports",
            "Support spacing, hangers, and loading guidance are coming soon in a future release.",
        )
    elif selected_module == "Dimensions & Engineering Data":
        render_module_card(
            "Dimensions & Engineering Data",
            "Access pipe, valve, flange, and fitting dimension libraries. Use AI lookup for non-standard items.",
            status="Active",
        )
    elif selected_module == "Material Takeoffs":
        render_module_card(
            "Material Takeoffs",
            "Takeoff generation and material quantity reporting are on the roadmap for later versions.",
        )
    elif selected_module == "Cost Estimating":
        render_module_card(
            "Cost Estimating",
            "Estimate equipment, materials, and labor in a future release.",
        )
    elif selected_module == "AI Search & Knowledge Base":
        render_module_card(
            "AI Search & Knowledge Base",
            "AI-powered engineering search and knowledge discovery will be introduced after Version 1.",
        )
    elif selected_module == "Engineering Calculations":
        render_module_card(
            "Engineering Calculations",
            "Pipe sizing and additional calculators will be added in future releases.",
        )
    else:
        render_module_card(
            selected_module,
            "This module is coming soon.",
        )


def render_main_screen(service_options: list[tuple[str, str]] | None = None, dimension_item_options: list[str] | None = None):
    left_column, right_column = st.columns([1, 3], gap="large")

    with left_column:
        st.markdown("<div style='padding:8px 0 16px 0; color:#DCEAFF; font-size:16px; font-weight:700;'>MODULES</div>", unsafe_allow_html=True)
        selected_module = None
        for module in MODULES:
            is_selected = st.session_state.get("selected_module", "Pipe Specifications") == module
            if st.button(module, key=f"module_{module}"):
                st.session_state["selected_module"] = module
            if is_selected:
                selected_module = module

    if selected_module is None:
        selected_module = st.session_state.get("selected_module", "Pipe Specifications")

    with right_column:
        st.markdown("<div class='top-panel'>", unsafe_allow_html=True)
        st.markdown("<h2 style='color:white; margin-bottom:10px;'>Ask PipingIQ</h2>", unsafe_allow_html=True)
        st.markdown("<p class='small-muted'>Search engineering knowledge, codes, specifications and more...</p>", unsafe_allow_html=True)

        question = st.text_input(
            label="",
            placeholder="Ask a question about piping, codes, specs, supports, materials...",
            key="search_box",
            label_visibility="hidden",
        )

        service_input = ""
        size_input = ""
        dimension_item = ""
        ai_lookup_clicked = False
        if selected_module == "Pipe Specifications":
            st.markdown(
                "<p class='small-muted' style='margin-top:10px;'>Ask using full service names or abbreviations and include the size in the same question, for example: <em>What pipe spec for Fuel Oil 2 inch</em>, <em>What pipe spec for Fuel Oil 2\&quot;</em>, or <em>STM LP flange for 1 1/2 inch</em>.</p>",
                unsafe_allow_html=True,
            )
        elif selected_module == "Dimensions & Engineering Data":
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            cols = st.columns([2, 1], gap="small")
            with cols[0]:
                dimension_item = st.selectbox(
                    label="Dimension item",
                    options=[""] + (dimension_item_options or []),
                    key="dimension_item_input",
                )
                st.markdown("<p class='small-muted' style='margin-top:6px;'>Select a standard dimension type, or use the AI lookup button for non-standard items.</p>", unsafe_allow_html=True)
            with cols[1]:
                size_input = st.text_input(label="Size (in)", key="dimension_size_input", placeholder="e.g. 1 1/2 or 2")
            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
            ai_lookup_clicked = st.button("AI Lookup Non-Standard Item", use_container_width=True, key="ai_lookup_button")

        file_column, button_column = st.columns([2, 1], gap="small")
        with file_column:
            uploaded_file = st.file_uploader(
                label="Upload a document",
                type=["pdf", "docx", "xlsx", "png", "jpg", "jpeg"],
                key="upload_file",
            )
        with button_column:
            search_clicked = st.button("Search", use_container_width=True)

        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        render_module_details(selected_module)

    return (
        selected_module,
        question or "",
        uploaded_file,
        search_clicked,
        service_input or "",
        size_input or "",
        dimension_item or "",
        ai_lookup_clicked,
    )


def render_answer_panel():
    st.markdown("<div class='answer-card'>", unsafe_allow_html=True)
    st.markdown("<div style='display:flex; justify-content:space-between; align-items:flex-start; gap:12px;'>", unsafe_allow_html=True)
    st.markdown("<div>")
    st.markdown("<h3 style='color:#B8D4FF; margin:0;'>PipingIQ Answer</h3>", unsafe_allow_html=True)
    st.markdown("<p class='small-muted' style='max-width:720px;'>Your answer will appear here once you search. PipingIQ uses verified engineering sources, codes, and specifications to deliver accurate, reliable answers for piping professionals.</p>", unsafe_allow_html=True)
    st.markdown("</div>")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_result_card(result):
    data = result
    if isinstance(result, Mapping):
        data = result
    else:
        data = result.as_dict() if hasattr(result, "as_dict") else dict(result)

    st.markdown(
        f"""
        <div style="
            background-color:{CARD_BACKGROUND};
            padding:18px;
            border-radius:18px;
            margin-bottom:16px;
            border:1px solid rgba(255,255,255,0.12);
        ">
        """,
        unsafe_allow_html=True,
    )

    spec_value = data.get("Spec") or data.get("spec") or ""
    service_value = data.get("Service") or data.get("service") or ""
    service_abbv = data.get("Service_Abbv") or data.get("service_abbv") or ""
    size_value = data.get("Size") or data.get("size_rule") or ""
    answer_field = data.get("field")
    answer_value = data.get("value")
    item_name = data.get("Item") or data.get("item")

    if item_name:
        item_value = data.get(item_name, "")
        st.markdown(
            f"<h3 style='color:{ANSWER_COLOR}; margin-bottom:8px;'>Dimension: {item_name} = {item_value}</h3>",
            unsafe_allow_html=True,
        )
    elif answer_field and answer_value is not None:
        st.markdown(
            f"<h3 style='color:{ANSWER_COLOR}; margin-bottom:8px;'>Result: {answer_field} = {answer_value}</h3>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<h3 style='color:{ANSWER_COLOR}; margin-bottom:8px;'>Specification: {spec_value}</h3>",
            unsafe_allow_html=True,
        )

    if item_name:
        st.markdown(f"<strong style='color:{LABEL_COLOR};'>Dimension Item:</strong> <span style='color:{VALUE_COLOR};'>{item_name}</span>", unsafe_allow_html=True)
    if service_value:
        st.markdown(f"<strong style='color:{LABEL_COLOR};'>Service:</strong> <span style='color:{VALUE_COLOR};'>{service_value}</span>", unsafe_allow_html=True)
    if service_abbv:
        st.markdown(f"<strong style='color:{LABEL_COLOR};'>Service Abbrev:</strong> <span style='color:{VALUE_COLOR};'>{service_abbv}</span>", unsafe_allow_html=True)
    if size_value:
        st.markdown(f"<strong style='color:{LABEL_COLOR};'>Size Rule:</strong> <span style='color:{VALUE_COLOR};'>{size_value}</span>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color: rgba(255,255,255,0.14);'>", unsafe_allow_html=True)

    for key, value in data.items():
        if key in {"Spec", "spec", "Service", "service", "Service_Abbv", "service_abbv", "Size", "size_rule", "field", "value", "Item", item_name}:
            continue
        if str(key).startswith("Unnamed"):
            continue
        if str(value).strip() == "":
            continue
        # Humanize the key for display (e.g., SERVICE_ABBV -> Service Abbv)
        display_key = str(key).replace("_", " ").title()
        display_value = value
        # Format numeric values nicely
        try:
            if isinstance(value, (int, float)):
                display_value = f"{value:.3f}" if isinstance(value, float) else str(value)
        except Exception:
            display_value = str(value)

        st.markdown(
            f"<div style='margin-bottom:6px;'><span style='color:{LABEL_COLOR};'>{display_key}:</span> <span style='color:{VALUE_COLOR};'>{display_value}</span></div>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


def render_results(results):
    if not results:
        st.error("No matching specification found.")
        return

    st.markdown(f"<div style='margin-top:18px; margin-bottom:12px;'><strong style='color:{SECTION_HEADER_COLOR};'>Search Results</strong></div>", unsafe_allow_html=True)
    for r in results:
        render_result_card(r)


def render_footer():
    st.markdown(
        """
        <div style='padding-top:18px;'>
            <hr style='border:1px solid rgba(255,255,255,0.08);'>
            <div style='display:flex; justify-content:space-between; flex-wrap:wrap; gap:12px;'>
                <span style='color:rgba(255,255,255,0.6); font-size:12px;'>PipingIQ Professional</span>
                <span style='color:rgba(255,255,255,0.6); font-size:12px;'>© 2026 PipingIQ. All Rights Reserved.</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
