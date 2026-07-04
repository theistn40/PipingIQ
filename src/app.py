"""
=========================================================
PipingIQ Professional v6.0
app.py
Application entry point for PipingIQ Professional.
=========================================================
"""

import streamlit as st

from database import DatabaseManager, DatabaseError, DimensionDatabase, _parse_numeric_size
from knowledge_router import route_query
from search_engine import search
from ui import (
    render_footer,
    render_header,
    render_main_screen,
    render_results,
    render_answer_panel,
    setup_page,
)


# ---------------------------------------------------------
# APP START
# ---------------------------------------------------------

# Initialize session state for modal
if "show_modal" not in st.session_state:
    st.session_state["show_modal"] = False
if "modal_results" not in st.session_state:
    st.session_state["modal_results"] = None

setup_page()
render_header()

try:
    db = DatabaseManager()
    dim_db = DimensionDatabase()
except DatabaseError as exc:
    st.error(str(exc))
    st.stop()
except Exception as exc:
    st.error(f"Unable to initialize the database: {exc}")
    st.stop()

dimension_item_options = []
try:
    if dim_db and dim_db.loaded:
        dimension_item_options = dim_db.item_options()
except Exception:
    dimension_item_options = []

selected_module, question, uploaded_file, search_clicked, service_input, size_input, dimension_item, ai_lookup_clicked = render_main_screen(
    service_options=None,
    dimension_item_options=dimension_item_options,
)

if search_clicked or ai_lookup_clicked:
    if selected_module == "Pipe Specifications":
        if question.strip():
            st.divider()
            result = search(db, question)
            if result["success"]:
                st.success(result.get("message") or "Answer Found")
                render_results(result.get("results", [result]))
            else:
                st.error(result["message"])
        else:
            st.warning("Enter a Pipe Specifications question with service and optional size.")
    elif selected_module == "Dimensions & Engineering Data":
        if ai_lookup_clicked:
            query_text = question.strip()
            if not query_text:
                if dimension_item and size_input:
                    query_text = f"Find non-standard dimensions for {dimension_item} at size {size_input}."
                else:
                    st.warning("Please enter a question or select a dimension item and size for AI lookup.")
                    query_text = None

            if query_text:
                st.divider()
                ai_result = search(db, query_text)
                if ai_result["success"]:
                    st.success("AI lookup returned a result")
                    render_results([ai_result])
                else:
                    st.error(ai_result["message"])
        elif search_clicked:
            if not dimension_item or not dimension_item.strip():
                st.warning("Please select a dimension item for the dimensions lookup.")
            elif not size_input or not size_input.strip():
                st.warning("Please enter a size for the dimensions lookup.")
            else:
                try:
                    requested_size = _parse_numeric_size(size_input)
                    dim_res = dim_db.query(item=dimension_item, size=requested_size)
                    st.divider()
                    if dim_res.success:
                        st.success(dim_res.message)
                        render_results(dim_res.records)
                    else:
                        st.error(dim_res.message)
                except Exception:
                    st.error("Unable to parse size. Use numeric or fraction (e.g. 1 1/2 or 3/4).")
        else:
            st.warning("Please use Search or AI Lookup for Dimensions & Engineering Data.")
    else:
        if not question.strip():
            st.warning("Please enter a question before searching.")
        else:
            result = route_query(question, selected_module, db)
            st.divider()
            if result["success"]:
                st.success(result.get("message") or "Answer Found")
                render_results(result.get("results", [result]))
            else:
                st.error(result["message"])

# Always render the answer panel at the end (shows modal if results exist)
render_answer_panel()
