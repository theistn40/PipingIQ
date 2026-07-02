"""
=========================================================
PipingIQ V5.2
Main Application
=========================================================
"""

import streamlit as st

from database import DatabaseManager, DatabaseError
from search_engine import search
from ui import render_footer, render_header, render_results, render_search, setup_page


# ---------------------------------------------------------
# PAGE
# ---------------------------------------------------------

setup_page()
render_header()

# ---------------------------------------------------------
# LOAD DATABASE
# ---------------------------------------------------------

try:
    db = DatabaseManager()
except DatabaseError as exc:
    st.error(str(exc))
    st.stop()
except Exception as exc:
    st.error(f"Unable to initialize the database: {exc}")
    st.stop()


# ---------------------------------------------------------
# SEARCH
# ---------------------------------------------------------

question = render_search()


# ---------------------------------------------------------
# BUTTON
# ---------------------------------------------------------

if st.button("Search"):

    if question.strip() == "":

        st.warning("Please enter a question.")

        st.stop()

    result = search(db.dataframe, question)

    st.divider()

    # -----------------------------------------------------
    # SUCCESS
    # -----------------------------------------------------

    if result["success"]:

        st.success("Answer Found")

        render_results([result])

    # -----------------------------------------------------
    # FAILURE
    # -----------------------------------------------------

    else:

        st.error(result["message"])


render_footer()