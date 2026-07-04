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
    BACKGROUND_DATA_URI,
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
    st.set_page_config(page_title=APP_NAME, layout="wide", initial_sidebar_state="expanded")
    st.markdown(
        f"""
        <style>
            /* ── Hide Streamlit chrome ── */
            #MainMenu {{ visibility: hidden !important; }}
            footer {{ visibility: hidden !important; }}
            header[data-testid="stHeader"] {{ display: none !important; }}
            [data-testid="stDecoration"] {{ display: none !important; }}
            [data-testid="stToolbar"] {{ display: none !important; }}
            [data-testid="stSidebarCollapseButton"] {{ display: none !important; }}
            [data-testid="stSidebarResizeHandle"] {{ display: none !important; }}
            [data-testid="collapsedControl"] {{ display: none !important; }}

            /* ── Background: Banner.png at 100% width, scales proportionally ── */
            .stApp {{
                background: url('{BACKGROUND_DATA_URI}') top left / 100% auto no-repeat !important;
                background-color: #010c22 !important;
            }}
            
            .sidebar-module {{
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 8px;
                padding: 12px 8px;
                margin-bottom: 8px;
                background: rgba(70, 130, 220, 0.15);
                border: 1.5px solid rgba(70, 130, 220, 0.4);
                border-radius: 12px;
                text-align: center;
                font-weight: 600;
                color: #7EC8FF;
                font-size: 11px;
                letter-spacing: 0.5px;
            }}
            
            .sidebar-label {{
                font-size: 10px;
                line-height: 1.2;
                text-transform: uppercase;
            }}
            
            .module-card {{
                background: rgba(10, 28, 60, 0.8);
                padding: 12px;
                border-radius: 12px;
                border: 1px solid rgba(112, 169, 255, 0.3);
                margin-bottom: 8px;
                background-image: linear-gradient(135deg, rgba(26, 95, 210, 0.1) 0%, rgba(112, 169, 255, 0.05) 100%);
            }}
            
            .answer-modal {{
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: rgba(5, 15, 35, 0.98);
                border: 2px solid rgba(70, 130, 220, 0.5);
                border-radius: 20px;
                padding: 32px;
                max-height: 85vh;
                max-width: 900px;
                width: 90%;
                z-index: 9999;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.8), inset 0 1px 0 rgba(255, 255, 255, 0.1);
                overflow-y: auto;
            }}
            
            .modal-overlay {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.7);
                z-index: 9998;
            }}
            
            .modal-close-btn {{
                position: absolute;
                top: 16px;
                right: 16px;
                background: rgba(70, 130, 220, 0.2);
                border: 1px solid rgba(70, 130, 220, 0.4);
                color: #70A9FF;
                padding: 8px 12px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                font-weight: bold;
                transition: all 0.3s ease;
            }}
            
            .modal-close-btn:hover {{
                background: rgba(70, 130, 220, 0.3);
                border-color: rgba(70, 130, 220, 0.6);
            }}
            
            .result-card {{
                background: rgba(10, 30, 60, 0.6);
                border: 1px solid rgba(70, 130, 220, 0.3);
                border-radius: 16px;
                padding: 20px;
                margin-bottom: 16px;
            }}
            
            .result-spec {{
                color: #70A9FF;
                font-weight: 700;
                font-size: 15px;
                margin-bottom: 12px;
            }}
            
            .result-field {{
                color: rgba(255, 255, 255, 0.9);
                margin-bottom: 8px;
                font-size: 13px;
                line-height: 1.6;
            }}
            
            .result-label {{
                color: #A2D9FF;
                font-weight: 600;
                display: inline-block;
                margin-right: 8px;
            }}
            
            /* ── Main content: aligned to image search row ── */
            /* Banner 1320×786; search input at y≈422 → (422/786)×59.55vw ≈ 32vw */
            .main, [data-testid="stMain"], .stMain,
            .appview-container .main,
            section.main {{
                padding-top: 0 !important;
                margin-top: 0 !important;
            }}
            .block-container {{
                padding-top: 25vw !important;
                padding-left: 1.5rem !important;
                padding-right: 1.5rem !important;
                padding-bottom: 2rem !important;
                max-width: 100% !important;
                background: transparent !important;
            }}

            /* Eliminate Streamlit's internal top spacing on columns */
            [data-testid="stHorizontalBlock"] {{
                align-items: flex-start !important;
            }}
            [data-testid="stColumn"] > div:first-child,
            [data-testid="stVerticalBlock"] > div:first-child {{
                margin-top: 0 !important;
                padding-top: 0 !important;
            }}
            .element-container:first-child {{
                margin-top: 0 !important;
            }}

            /* ── Sidebar: transparent, width matches image left panel (~18% of image width) ── */
            section[data-testid="stSidebar"] {{
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                width: 18vw !important;
                min-width: 180px !important;
                max-width: 280px !important;
            }}

            /* ── Sidebar first module starts at y≈90/786×59.55vw ≈ 6.8vw ── */
            section[data-testid="stSidebar"] > div:first-child {{
                background: transparent !important;
                padding: 0 !important;
                margin: 0 !important;
                padding-top: 6.8vw !important;
            }}

            /* Hide any markdown labels in sidebar */
            section[data-testid="stSidebar"] .stMarkdown {{ display: none !important; }}

            /* Remove gaps between module buttons */
            section[data-testid="stSidebar"] .element-container {{
                padding: 0 !important;
                margin: 0 !important;
            }}
            section[data-testid="stSidebar"] .stButton {{
                padding: 0 !important;
                margin: 0 !important;
            }}

            /* ── Module buttons: invisible transparent hotspots over image entries ── */
            /* Each entry ≈ 80px/800 × 62.5vw ≈ 6.25vw tall */
            section[data-testid="stSidebar"] .stButton > button {{
                height: 6.5vw !important;
                min-height: 50px !important;
                max-height: 90px !important;
                width: 100% !important;
                background: transparent !important;
                border: none !important;
                border-radius: 0 !important;
                color: transparent !important;
                font-size: 0 !important;
                line-height: 0 !important;
                padding: 0 !important;
                margin: 0 !important;
                box-shadow: none !important;
                cursor: pointer !important;
                display: block !important;
                outline: none !important;
                transition: background 0.15s ease, box-shadow 0.15s ease !important;
            }}

            section[data-testid="stSidebar"] .stButton > button:hover {{
                background: rgba(40, 110, 255, 0.28) !important;
                box-shadow: inset 4px 0 0 rgba(80, 160, 255, 0.9) !important;
            }}

            section[data-testid="stSidebar"] .stButton > button:focus {{
                outline: none !important;
                background: rgba(20, 80, 220, 0.35) !important;
                box-shadow: inset 5px 0 0 #5599ff !important;
            }}

            /* ── Search text input ── */
            .stTextInput > div > div > input {{
                background: rgba(255, 255, 255, 0.96) !important;
                border: 1.5px solid rgba(80, 140, 255, 0.3) !important;
                border-radius: 8px !important;
                color: #0b1830 !important;
                font-size: 15px !important;
                padding: 10px 16px !important;
            }}
            .stTextInput > label {{ display: none !important; }}

            /* ── Search & action buttons in main area ── */
            [data-testid="stMain"] .stButton > button {{
                background: #0f4c93 !important;
                color: #ffffff !important;
                border: none !important;
                border-radius: 8px !important;
                font-weight: 700 !important;
                font-size: 14px !important;
            }}
            [data-testid="stMain"] .stButton > button:hover {{
                background: #1a5fd4 !important;
            }}

            /* ── File uploader: match image's drag-drop box ── */
            /* Upload box height: (535-420)/786 × 59.55vw ≈ 8.7vw */
            /* Hide label - correct selector from DOM inspection */
            [data-testid="stFileUploader"] [data-testid="stWidgetLabel"] {{
                display: none !important;
            }}
            /* Style dropzone - DOM has section[data-testid="stFileUploaderDropzone"] */
            [data-testid="stFileUploader"] section[data-testid="stFileUploaderDropzone"],
            [data-testid="stFileUploader"] section[role="presentation"] {{
                background: rgba(4, 16, 52, 0.70) !important;
                border: 2px dashed rgba(80, 148, 255, 0.72) !important;
                border-radius: 10px !important;
                height: 8.7vw !important;
                min-height: 100px !important;
                width: 100% !important;
                box-sizing: border-box !important;
            }}
            [data-testid="stFileUploader"] {{
                height: 8.7vw !important;
                min-height: 100px !important;
            }}

            /* ── Answer/results container ── */
            [data-testid="stVerticalBlockBorderWrapper"] {{
                background: rgba(4, 14, 42, 0.90) !important;
                border: 1px solid rgba(70, 130, 255, 0.4) !important;
                border-radius: 12px !important;
            }}

            /* ── Alerts and status ── */
            .stAlert {{
                background: rgba(5, 18, 50, 0.88) !important;
                border-radius: 8px !important;
            }}

            /* ── Text colors ── */
            p, h1, h2, h3, h4, h5, label {{
                color: {TEXT_COLOR} !important;
            }}

            /* ── Selectbox ── */
            .stSelectbox > div > div {{
                background: rgba(255, 255, 255, 0.92) !important;
                color: #0b1830 !important;
            }}

            /* Legacy classes kept for result cards */
            .module-card {{
                background: rgba(10, 28, 60, 0.8);
                padding: 12px;
                border-radius: 12px;
                border: 1px solid rgba(112, 169, 255, 0.3);
                margin-bottom: 8px;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar():
    """Render left sidebar with module buttons and icons."""
    modules_html = '<div class="sidebar-container">'
    
    for module in MODULES:
        icon = ICONS.get(module, "📦")
        modules_html += f'''
        <div class="sidebar-module" title="{module}">
            <div class="sidebar-icon">{icon}</div>
            <div class="sidebar-label">{module.replace(" & ", "&<br/>")}</div>
        </div>
        '''
    
    modules_html += '</div>'
    st.markdown(modules_html, unsafe_allow_html=True)


def render_hero_section():
    """Render professional hero header section."""
    st.markdown(
        """
        <div class="main-content">
            <div class="hero-section">
                <div class="hero-logo">PipingIQ</div>
                <div class="hero-tagline">ENGINEERING INTELLIGENCE PLATFORM</div>
                <div class="hero-subtitle">Professional Engineering Application for Piping Design, Specifications, Codes & Estimating</div>
                <div class="hero-desc">ONE APPLICATION. COMPLETE PIPING ENGINEERING KNOWLEDGE.</div>
            </div>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    """Header is provided by the background image."""
    pass


def render_footer():
    """Footer is provided by the background image."""
    pass


def render_module_details(selected_module: str):
    """Render a compact module details card."""
    if selected_module == "Pipe Specifications":
        st.markdown(f"<div class='module-card'><strong style='color:#A2D9FF;'>{selected_module}</strong> • <span style='color:rgba(255,255,255,0.8); font-size:12px;'>Search database by service, size, and field</span><span style='display:inline-block; color:#70A9FF; font-weight:700; padding:2px 8px; border-radius:8px; background: rgba(112,169,255,0.15); border: 1px solid rgba(112,169,255,0.3); font-size:10px; margin-left:8px;'>Active</span></div>", unsafe_allow_html=True)
    elif selected_module == "Codes & Standards":
        st.markdown(f"<div class='module-card'><strong style='color:#A2D9FF;'>{selected_module}</strong> • <span style='color:rgba(255,255,255,0.8); font-size:12px;'>Lookup service-related standards</span><span style='display:inline-block; color:#70A9FF; font-weight:700; padding:2px 8px; border-radius:8px; background: rgba(112,169,255,0.15); border: 1px solid rgba(112,169,255,0.3); font-size:10px; margin-left:8px;'>Active</span></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='module-card'><strong style='color:#A2D9FF;'>{selected_module}</strong></div>", unsafe_allow_html=True)


def render_main_screen(service_options: list[tuple[str, str]] | None = None, dimension_item_options: list[str] | None = None):
    """Render main screen with sidebar and search panel."""
    
    # Initialize session state
    if "selected_module" not in st.session_state:
        st.session_state["selected_module"] = "Pipe Specifications"
    
    # Sidebar: module buttons as transparent hotspots over the image's left panel
    with st.sidebar:
        selected_module = st.session_state.get("selected_module", "Pipe Specifications")
        for i, module in enumerate(MODULES):
            if st.button(module, key=f"module_{i}", use_container_width=True):
                st.session_state["selected_module"] = module
                st.rerun()

    selected_module = st.session_state.get("selected_module", "Pipe Specifications")

    # Three-column layout: search | OR gap (transparent) | upload
    # Banner proportions: search≈55%, OR gap≈8%, upload≈35% of main area
    col_search, col_or, col_upload = st.columns([55, 8, 35])

    with col_search:
        # Input + Search button inline (8:1 ratio to match image's wide input)
        subcol_input, subcol_btn = st.columns([8, 1])
        with subcol_input:
            question = st.text_input(
                label="Search",
                placeholder="Ask a question about piping, codes, specs, supports, materials...",
                key="search_box",
                label_visibility="collapsed",
            )
        with subcol_btn:
            search_clicked = st.button("Search", use_container_width=True, key="search_btn")

    with col_or:
        pass  # transparent gap — image's "OR" text shows through

    with col_upload:
        uploaded_file = st.file_uploader(
            label="Upload a document",
            type=["pdf", "docx", "xlsx", "png", "jpg", "jpeg"],
            key="upload_file",
            label_visibility="collapsed",
        )

    # Additional inputs for specific modules (shown below search row)
    service_input = ""
    size_input = ""
    dimension_item = ""
    ai_lookup_clicked = False

    if selected_module == "Dimensions & Engineering Data":
        dcol1, dcol2 = st.columns([2, 1])
        with dcol1:
            dimension_item = st.selectbox(
                label="Dimension item",
                options=[""] + (dimension_item_options or []),
                key="dimension_item_input",
            )
        with dcol2:
            size_input = st.text_input(label="Size", key="dimension_size_input", placeholder="e.g. 1 1/2")
    
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


def render_results(results):
    """Render search results."""
    if not results:
        st.error("No matching specification found.")
        return
    
    # Store results in session state to show modal
    st.session_state["show_modal"] = True
    st.session_state["modal_results"] = results
    
    st.success(f"Found {len(results)} matching specifications.")


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


def render_answer_panel():
    """Display modal with search results if there are any, with proper close button functionality."""
    # Check session state
    show_modal = st.session_state.get("show_modal", False)
    modal_results = st.session_state.get("modal_results")
    
    # Only render if both conditions are true
    if not (show_modal and modal_results):
        return
    
    results = modal_results if isinstance(modal_results, list) else [modal_results]
    
    # Create modal container
    with st.container(border=True):
        # Title
        st.markdown(f"### 🔷 PipingIQ Answer - {len(results)} Result(s)")
        
        # Close button
        if st.button("Close Results"):
            st.session_state["show_modal"] = False
            st.session_state["modal_results"] = None
            st.rerun()
        
        st.divider()
        
        # Display results
        for i, result in enumerate(results):
            render_result_card(result)
            if i < len(results) - 1:
                st.divider()
