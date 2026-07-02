import os

import pandas as pd
import streamlit as st

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_FILE = os.path.join(DATA_DIR, "PipeSpec_Master.xlsx")

st.set_page_config(page_title="PipingIQ V4", layout="wide")
st.title("PipingIQ V4")

FIELD_MAP = {
    "SPEC": "Spec",
    "PIPE": "Pipe",
    "SIZE": "Size",
    "SCHEDULE": "Schedule",
    "COUPLING": "Coupling",
    "FITTING": "Fitting",
    "JOINT": "Joint",
    "VALVE": "Valve",
    "FLANGE": "Flange",
    "BOLT": "Bolts",
    "CLAMP": "Clamps",
    "SOLDER": "SOLDER",
    "GASKET": "Gasket",
    "INSULATION": "Insulation",
    "SUPPORT": "Support Spacing",
    "TEST": "Test Pressure",
    "FLEXIBLE": "Flexible Hose",
    "TEMP": "MAXIMUM TEMPERATURE (F):                                                                  MAXIMUM PRESSURE (PSI)(1):  "
}


def load_db() -> pd.DataFrame:
    """Load the PipeSpec master spreadsheet from the data folder."""
    df = pd.read_excel(DB_FILE)
    df.columns = df.columns.str.strip()
    return df


@st.cache_data
def cached_load_db() -> pd.DataFrame:
    return load_db()


def extract_size(text: str) -> float | None:
    for token in text.replace('"', " ").split():
        try:
            return float(token)
        except ValueError:
            continue
    return None


def build_response_rows(df: pd.DataFrame, query: str) -> list[dict]:
    q = query.upper().strip()
    words = set(q.replace('"', " ").split())
    size = extract_size(q)

    requested = None
    for key, field in FIELD_MAP.items():
        if key in q:
            requested = field
            break

    matches = []
    for _, row in df.iterrows():
        service = str(row.get("Service", "")).upper().strip()
        abbv = str(row.get("Service_Abbv", "")).upper().strip()

        service_match = bool(service and service in q)
        abbv_match = bool(abbv and abbv in words)
        if not (service_match or abbv_match):
            continue

        if size is not None:
            rule = str(row.get("Size", "")).replace(" ", "")
            if "<=" in rule or "<" in rule:
                if size > 2:
                    continue
            elif ">" in rule:
                if size <= 2:
                    continue

        matches.append({"row": row, "requested": requested})

    return matches


def render_match(row: pd.Series, requested: str | None) -> None:
    st.markdown("---")
    st.subheader(f"Specification: {row.get('Spec', '')}")
    st.write(f"**Service:** {row.get('Service', '')} ({row.get('Service_Abbv', '')})")
    st.write(f"**Size:** {row.get('Size', '')}")

    if requested:
        st.write(f"**{requested}:** {row.get(requested, '')}")
    else:
        for col in row.index:
            val = row.get(col, "")
            if pd.notna(val) and str(val).strip():
                st.write(f"**{col}:** {val}")


def main() -> None:
    st.sidebar.header("PipingIQ Controls")
    st.sidebar.markdown("Place `PipeSpec_Master.xlsx` in the `data` folder.")
    st.sidebar.markdown(f"Data file path: `{DB_FILE}`")

    if not os.path.exists(DB_FILE):
        st.error(f"Data file not found: {DB_FILE}")
        st.stop()

    try:
        df = cached_load_db()
    except Exception as exc:
        st.error(f"Cannot open {DB_FILE}: {exc}")
        st.stop()

    question = st.text_input("Ask a question about piping specs:")
    if st.button("Ask"):
        if not question.strip():
            st.warning("Please enter a question before asking.")
            return

        matches = build_response_rows(df, question)
        if not matches:
            st.error("No matching specifications found.")
            return

        st.success(f"{len(matches)} specification(s) found")
        for match in matches:
            render_match(match["row"], match["requested"])


if __name__ == "__main__":
    main()
