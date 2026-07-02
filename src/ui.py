"""
=========================================================
PipingIQ V5.1
User Interface Layer (Clean Engineering UI)
=========================================================
"""

import streamlit as st
from collections.abc import Mapping
from config import (
    LABEL_COLOR,
    VALUE_COLOR,
    ANSWER_COLOR,
    CARD_BACKGROUND,
)


# ---------------------------------------------------------
# PAGE SETUP
# ---------------------------------------------------------

def setup_page():
    """
    Configure Streamlit page
    """

    st.set_page_config(
        page_title="PipingIQ",
        layout="wide"
    )


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------

def render_header():
    """
    Clean header (NO logo, NO background image)
    """

    st.markdown(
        """
        <div style="
            padding:10px 0px;
            border-bottom:1px solid #2A3B4D;
            margin-bottom:15px;
        ">
            <h2 style="color:white; margin:0;">
                PipingIQ
            </h2>
            <p style="color:#7CC7FF; margin:0;">
                Engineering Specification Search
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


# ---------------------------------------------------------
# SEARCH BAR (MUST BE AT TOP)
# ---------------------------------------------------------

def render_search():
    """
    Main search input
    """

    st.markdown("### Search")

    query = st.text_input(
        label="",
        placeholder="Enter piping question (e.g. flange for STM LP)",
        key="search_box"
    )

    return query


# ---------------------------------------------------------
# RESULT CARD
# ---------------------------------------------------------

def render_result_card(result):
    """
    Displays a single search result.
    """

    data = result
    if isinstance(result, Mapping):
        data = result
    else:
        data = result.as_dict() if hasattr(result, "as_dict") else dict(result)

    st.markdown(
        f"""
        <div style="
            background-color:{CARD_BACKGROUND};
            padding:15px;
            border-radius:10px;
            margin-bottom:10px;
            border:1px solid #2C4F6B;
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

    if answer_field and answer_value is not None:
        st.markdown(
            f"### <span style='color:{ANSWER_COLOR}'>Result: {answer_field} = {answer_value}</span>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"### <span style='color:{ANSWER_COLOR}'>Specification: {spec_value}</span>",
            unsafe_allow_html=True,
        )

    if service_value:
        st.markdown(
            f"**Service:** <span style='color:{VALUE_COLOR}'>{service_value}</span>",
            unsafe_allow_html=True,
        )

    if service_abbv:
        st.markdown(
            f"**Service Abbrev:** <span style='color:{VALUE_COLOR}'>{service_abbv}</span>",
            unsafe_allow_html=True,
        )

    if size_value:
        st.markdown(
            f"**Size Rule:** <span style='color:{VALUE_COLOR}'>{size_value}</span>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    for key, value in data.items():
        if key in {"Spec", "spec", "Service", "service", "Service_Abbv", "service_abbv", "Size", "size_rule", "field", "value"}:
            continue
        if str(value).strip() == "":
            continue

        st.markdown(
            f"<span style='color:{LABEL_COLOR}'>{key}:</span> "
            f"<span style='color:{VALUE_COLOR}'>{value}</span>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# RESULTS LIST
# ---------------------------------------------------------

def render_results(results):
    """
    Render all results
    """

    if not results:
        st.error("No matching specification found.")
        return

    st.success(f"{len(results)} specification(s) found")

    for r in results:
        render_result_card(r)


# ---------------------------------------------------------
# FOOTER (MINIMAL)
# ---------------------------------------------------------

def render_footer():
    """
    Optional footer (no branding clutter)
    """

    st.markdown(
        """
        <hr style="border:1px solid #1F2E3D;">
        <p style="color:#5A7C99; font-size:12px;">
        PipingIQ V5.1
        </p>
        """,
        unsafe_allow_html=True
    )