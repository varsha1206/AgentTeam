import json
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from agentteam.main import run_pipeline

# =========================================================
# CONFIG
# =========================================================
# NOTE: adjust the paths in this block if your pipeline writes
# the database / reports somewhere different — everything below
# reads from these constants only.

workspace = Path(__file__).resolve().parents[1] / "workspace"
input_dir = workspace / "input"
validation_rules_dir = workspace / "configs" / "validation_rules"
output_dir = workspace / "output"

DB_PATH = workspace / "agentteam.db"
VALIDATION_REPORT_PATH = workspace / "logs" / "validation_report.json"
TRANSFORMATION_REPORT_PATH = workspace / "logs" / "transformation_report.json"

SILVER_TABLE_PREFIX = "silver_"
QUARANTINE_TABLE_PREFIX = "quarantine_"

NON_DEV_GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScsTXei6AVvJ6bdAst1EY8rbgBmaWu3DcNRGFGm1bBGb2DZYQ/viewform?usp=sharing&ouid=105111568914025434899"

st.set_page_config(
    page_title="AgentTeam",
    page_icon="🤖",
    layout="centered",
)

example_validation_rules = """schema:
    id:
        type: int
        nullable: false

    salary:
        type: float
        nullable: false
        min: 0

transformations:
    - operation: create_unique_employee_id
        selection: infer
        description: Create a hash id
"""

# =========================================================
# STYLE
# =========================================================

st.markdown(
    """
<style>

:root {
  --bg: #0f1f1b;
  --bg-elevated: #152823;
  --bg-panel: #19312a;
  --bg-panel-2: #1f3a33;
  --accent: #6fbf8f;
  --accent-soft: #8fd3aa;
  --accent-bright: #b7e5cd;
  --amber: #e8b86d;
  --amber-soft: #f0d2a0;
  --text-main: #e5f2ea;
  --text-muted: #b2cbbb;
  --border: rgba(143, 211, 170, 0.18);

  /* Secondary / navigation accent — a muted steel-blue that pairs with the
     green primary accent without competing with it. */
  --nav-bg: #1b2f36;
  --nav-bg-hover: #223a42;
  --nav-text: #bcd7de;
  --nav-border: rgba(126, 178, 194, 0.30);
  --nav-active-start: #7fb2c7;
  --nav-active-end: #5a93a9;
}

.stApp{
background:
    radial-gradient(circle at top, rgba(111, 191, 143, 0.14), transparent 32%),
    linear-gradient(180deg, #10211d 0%, #0f1f1b 55%, #0b1513 100%);
color:var(--text-main);
}

h1,h2,h3{
color:var(--accent-bright);
letter-spacing:0.01em;
}

.stCaption, .stSubheader, .stMarkdown, .stText, .stMetric, .stMarkdownContainer p, .stMarkdownContainer li {
color:var(--text-main);
}

.stTabs [data-baseweb="tab-list"] {
gap:0.5rem;
border-bottom:1px solid var(--border);
}

.stTabs [data-baseweb="tab"] {
background:var(--bg-panel);
color:var(--text-muted);
border:1px solid var(--border);
border-bottom:none;
border-radius:0.9rem 0.9rem 0 0;
font-weight:600;
}

.stTabs [aria-selected="true"] {
background:linear-gradient(180deg, var(--bg-panel-2), var(--bg-panel));
color:var(--accent-bright);
}

.stFileUploader {
background:linear-gradient(180deg, rgba(31, 58, 51, 0.96), rgba(21, 40, 35, 0.96));
border:1px solid var(--border);
border-radius:1rem;
padding:0.9rem;
box-shadow:0 10px 30px rgba(0, 0, 0, 0.18);
}

.stFileUploader label,
.stFileUploader span,
.stFileUploader p,
.stFileUploader div,
.stFileUploader button {
color:var(--text-main);
}

/* --- Primary buttons: the main call-to-action per page (green) --- */
.stButton button[kind="primary"],
.stLinkButton a[kind="primary"] {
background:linear-gradient(180deg, var(--accent-soft), var(--accent));
color:#0c1714;
border:none;
border-radius:0.9rem;
height:48px;
font-weight:bold;
box-shadow:0 10px 22px rgba(111, 191, 143, 0.18);
}

.stButton button[kind="primary"]:hover,
.stLinkButton a[kind="primary"]:hover {
background:linear-gradient(180deg, #b8ebc7, #89d9a7);
color:#08120f;
}

/* --- Secondary buttons: plain / "schlicht" navigation & back actions --- */
.stButton button[kind="secondary"] {
background:var(--nav-bg);
color:var(--nav-text);
border:1px solid var(--nav-border);
border-radius:0.7rem;
height:42px;
font-weight:600;
box-shadow:none;
}

.stButton button[kind="secondary"]:hover {
background:var(--nav-bg-hover);
color:var(--accent-bright);
border-color:var(--nav-border);
}

/* Disabled secondary button = the currently active page in the nav trail */
.stButton button[kind="secondary"]:disabled {
background:linear-gradient(180deg, var(--nav-active-start), var(--nav-active-end));
color:#0c1714;
border:none;
opacity:1;
cursor:default;
font-weight:700;
}

.stDownloadButton>button{
background:transparent;
color:var(--accent-bright);
border:1px solid var(--border);
border-radius:0.9rem;
font-weight:600;
}

.stDownloadButton>button:hover{
border-color:var(--accent-soft);
color:var(--accent-bright);
background:rgba(111, 191, 143, 0.10);
}

.block-container{
padding-top:2rem;
padding-bottom:2.5rem;
}

hr {
border-color:var(--border);
}

.stInfo, .stWarning {
background:rgba(111, 191, 143, 0.08);
border-color:var(--border);
color:var(--text-main);
}

.stCodeBlock, pre, code {
background:#13251f !important;
color:var(--accent-bright) !important;
border:1px solid var(--border);
}

.stTextInput input,
.stTextArea textarea,
.stSelectbox div,
.stMultiSelect div {
background:var(--bg-panel);
color:var(--text-main);
border-color:var(--border);
border-radius:0.75rem;
}

.stMetric {
background:linear-gradient(180deg, rgba(31, 58, 51, 0.72), rgba(21, 40, 35, 0.72));
border:1px solid var(--border);
border-radius:1rem;
padding:1rem;
box-shadow:0 8px 24px rgba(0, 0, 0, 0.14);
}

.stMetric label,
.stMetric span {
color:var(--text-main) !important;
}

.stAlert,
.stAlert p,
.stAlert div {
color:inherit;
}

.stTabs [data-baseweb="tab"]:hover {
color:var(--accent-bright);
}

/* --- custom components --- */

.nav-trail {
margin-bottom:0.6rem;
}

.card {
background:linear-gradient(180deg, rgba(31, 58, 51, 0.85), rgba(21, 40, 35, 0.85));
border:1px solid var(--border);
border-radius:1.1rem;
padding:1.4rem 1.5rem;
box-shadow:0 10px 26px rgba(0, 0, 0, 0.16);
margin-bottom:1.1rem;
}

.step-card {
display:flex;
gap:0.9rem;
align-items:flex-start;
background:var(--bg-panel);
border:1px solid var(--border);
border-radius:1rem;
padding:1rem 1.1rem;
margin-bottom:0.8rem;
}

.step-number {
flex-shrink:0;
width:2rem;
height:2rem;
border-radius:50%;
background:linear-gradient(180deg, var(--accent-soft), var(--accent));
color:#0c1714;
font-weight:800;
display:flex;
align-items:center;
justify-content:center;
}

.step-text {
color:var(--text-main);
line-height:1.45;
}

.badge-silver {
display:inline-block;
padding:0.2rem 0.7rem;
border-radius:999px;
background:rgba(111, 191, 143, 0.18);
color:var(--accent-bright);
font-weight:700;
font-size:0.8rem;
}

.badge-quarantine {
display:inline-block;
padding:0.2rem 0.7rem;
border-radius:999px;
background:rgba(232, 184, 109, 0.18);
color:var(--amber-soft);
font-weight:700;
font-size:0.8rem;
}

</style>
""",
    unsafe_allow_html=True,
)

# =========================================================
# SESSION STATE / NAVIGATION
# =========================================================

if "page" not in st.session_state:
    st.session_state.page = "home"

if "pipeline_result" not in st.session_state:
    st.session_state.pipeline_result = None


def goto(page: str) -> None:
    st.session_state.page = page


PAGE_ORDER = [
    ("home", "1 · Home"),
    ("run", "2 · Try it out"),
    ("results", "3 · Results"),
    ("survey", "4 · Survey"),
]


def render_nav_trail() -> None:
    """Renders the page trail as clickable (but understated) nav buttons.
    The current page shows as a highlighted, disabled pill."""
    current = st.session_state.page
    st.markdown('<div class="nav-trail">', unsafe_allow_html=True)
    cols = st.columns(len(PAGE_ORDER))
    for col, (key, label) in zip(cols, PAGE_ORDER):
        with col:
            is_current = key == current
            if st.button(
                label,
                key=f"navtrail_{key}",
                use_container_width=True,
                disabled=is_current,
            ):
                goto(key)
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# HELPERS
# =========================================================


def save_uploaded_files(uploaded_files, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)

    for old_file in target_dir.glob("*"):
        old_file.unlink()

    for uploaded_file in uploaded_files:
        with open(target_dir / uploaded_file.name, "wb") as file_handle:
            file_handle.write(uploaded_file.getbuffer())


def read_latest_report_entry(path: Path) -> dict | None:
    """Reads a JSON report and returns the latest entry only."""
    try:
        if path.exists():
            payload = json.loads(path.read_text())
            if isinstance(payload, list):
                if not payload:
                    return None
                latest = payload[-1]
                return latest if isinstance(latest, dict) else None
            if isinstance(payload, dict):
                return payload
            return None
    except Exception as exc:  # pragma: no cover - defensive
        return {"_error": f"Could not read {path.name}: {exc}"}
    return None


def quote_identifier(identifier: str) -> str:
    """Safely quotes a SQLite identifier such as a table name."""
    return '"' + identifier.replace('"', '""') + '"'


def normalize_dataset_key(table_name: str) -> str:
    """Derives a stable dataset key from dynamic silver/quarantine table names."""
    key = table_name
    for prefix in (SILVER_TABLE_PREFIX, QUARANTINE_TABLE_PREFIX):
        if key.startswith(prefix):
            key = key[len(prefix) :]

    # Be tolerant of historical names like quarantine_quarantine_<dataset>.
    for duplicate_prefix in ("quarantine_", "silver_"):
        if key.startswith(duplicate_prefix):
            key = key[len(duplicate_prefix) :]

    return key


def list_dataset_tables() -> tuple[list[str], list[str]]:
    """Returns all silver_* and quarantine_* tables found in the SQLite DB."""
    if not DB_PATH.exists():
        return [], []

    try:
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
    except Exception:
        return [], []

    table_names = [row[0] for row in rows]
    silver_tables = sorted(
        [name for name in table_names if name.startswith(SILVER_TABLE_PREFIX)]
    )
    quarantine_tables = sorted(
        [name for name in table_names if name.startswith(QUARANTINE_TABLE_PREFIX)]
    )
    return silver_tables, quarantine_tables


def build_dataset_table_map() -> list[dict[str, str | None]]:
    """Builds dataset-wise mapping between silver and quarantine table names."""
    silver_tables, quarantine_tables = list_dataset_tables()

    silver_by_key: dict[str, str] = {}
    quarantine_by_key: dict[str, str] = {}

    for table_name in silver_tables:
        key = normalize_dataset_key(table_name)
        silver_by_key.setdefault(key, table_name)

    for table_name in quarantine_tables:
        key = normalize_dataset_key(table_name)
        quarantine_by_key.setdefault(key, table_name)

    dataset_keys = sorted(set(silver_by_key) | set(quarantine_by_key))
    return [
        {
            "dataset": key,
            "silver_table": silver_by_key.get(key),
            "quarantine_table": quarantine_by_key.get(key),
        }
        for key in dataset_keys
    ]


def table_row_count(table_name: str) -> int | None:
    if not DB_PATH.exists():
        return None
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute(
                f"SELECT COUNT(*) FROM {quote_identifier(table_name)}"
            )
            return cursor.fetchone()[0]
    except Exception:
        return None


def load_table_sample(table_name: str, limit: int = 5) -> pd.DataFrame | None:
    if not DB_PATH.exists():
        return None
    try:
        with sqlite3.connect(DB_PATH) as conn:
            query = f"SELECT * FROM {quote_identifier(table_name)} LIMIT {int(limit)}"
            return pd.read_sql(query, conn)
    except Exception:
        return None


# =========================================================
# PAGE: HOME
# =========================================================


def page_home() -> None:
    st.title("🤖 AgentTeam")
    st.caption("LLM-powered Multi-Agent Data Ingestion Pipeline")
    render_nav_trail()

    st.markdown(
        """
<div class="card">
AgentTeam turns messy CSV and JSON files into a clean, queryable SQLite database.
A team of agents retrieves, validates, and repairs your data against rules you
define — every row that passes ends up in a <span class="badge-silver">Silver</span>
table, and every row that fails ends up in a <span class="badge-quarantine">Quarantine</span>
table so nothing silently disappears.
</div>
""",
        unsafe_allow_html=True,
    )

    st.subheader("How it works")

    steps = [
        "Upload your <b>CSV / JSON</b> input files.",
        "Upload a <b>validation rules YAML</b> for each input file, using the "
        "same base name — for example <code>broken_employee_data.csv</code> → "
        "<code>broken_employee_data.yaml</code>.",
        "The agent team retrieves, validates, and repairs your data. Rows that "
        "pass validation land in the <b>Silver</b> table; rows that fail land in "
        "the <b>Quarantine</b> table, both inside a single SQLite database.",
        "Review a summary and sample rows on the Results page, then tell us "
        "what you thought on the Survey page.",
    ]

    for i, step in enumerate(steps, start=1):
        st.markdown(
            f"""
<div class="step-card">
    <div class="step-number">{i}</div>
    <div class="step-text">{step}</div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.subheader("Sample validation rules YAML")
    st.write(
        "Each YAML file describes the expected schema for one input file and any "
        "transformations or repair hints the repair agent should apply. Keep the "
        "file name aligned with the dataset name so the pipeline can find the "
        "right rule automatically."
    )
    st.code(example_validation_rules, language="yaml")
    st.download_button(
        "⬇️ Download sample YAML",
        data=example_validation_rules,
        file_name="sample_validation_rules.yaml",
        mime="text/yaml",
    )

    st.divider()

    if st.button("🚀 Try it out", use_container_width=True, type="primary"):
        goto("run")
        st.rerun()


# =========================================================
# PAGE: UPLOAD & RUN
# =========================================================

loading_messages = [
    "🤖 Claude is assigning work to the team...",
    "📂 Retrieval Agent is sniffing out your dataset...",
    "🔍 Validator is interrogating every record...",
    "🛠 Repair Agent is patching up the messy rows...",
    "📦 Building Silver and Quarantine tables...",
    "☕ Agents are arguing about the optimal fix...",
    "🧭 Cross-checking against your validation rules...",
    "🗃 Writing everything neatly into SQLite...",
]


def page_run() -> None:
    st.title("🚀 Try it out")
    render_nav_trail()

    if st.button("← Back to Home"):
        goto("home")
        st.rerun()

    st.info(
        "Name each validation YAML using the same base name as the input file, "
        "for example `broken_employee_data.csv` → `broken_employee_data.yaml`."
    )

    upload_tab, guide_tab = st.tabs(["Upload Files", "Validation Rules Guide"])

    with upload_tab:
        uploaded_files = st.file_uploader(
            "Upload your CSV and JSON files",
            type=["csv", "json"],
            accept_multiple_files=True,
        )

        if uploaded_files:
            save_uploaded_files(uploaded_files, input_dir)
            st.success(f"{len(uploaded_files)} file(s) uploaded.")

        validation_rules_uploaded = st.file_uploader(
            "Upload your validation rules YAML files",
            type=["yaml", "yml"],
            accept_multiple_files=True,
        )

        if validation_rules_uploaded:
            validation_rules_dir.mkdir(parents=True, exist_ok=True)

            uploaded_stems = {Path(file.name).stem for file in uploaded_files or []}

            for uploaded_file in validation_rules_uploaded:
                uploaded_stem = Path(uploaded_file.name).stem

                if uploaded_stems and uploaded_stem not in uploaded_stems:
                    st.warning(
                        f"Validation rule '{uploaded_file.name}' does not match "
                        "any uploaded input file name. The YAML file should use "
                        "the same base name as the source file."
                    )

                with open(
                    validation_rules_dir / f"{uploaded_stem}.yaml", "wb"
                ) as file_handle:
                    file_handle.write(uploaded_file.getbuffer())

            st.success(
                f"{len(validation_rules_uploaded)} validation rule file(s) uploaded."
            )

    with guide_tab:
        st.subheader("How to structure validation rules")
        st.write(
            "Each YAML file should describe the expected schema for one input "
            "file and any transformations or repair hints that should be "
            "applied. Keep the file name aligned with the dataset name so the "
            "pipeline can find the right rule automatically."
        )
        st.markdown("**Derived example based on `broken_employee_data.yaml`:**")
        st.code(example_validation_rules, language="yaml")
        st.markdown(
            "**Recommended pattern**\n\n"
            "- `schema`: define each column, its type, and any constraints.\n"
            "- `transformations`: list the fixes or enrichments the repair "
            "agent should apply.\n"
            "- Match the YAML base name to the input file base name, for "
            "example `broken_employee_data.yaml`."
        )

    st.divider()

    if st.button("Run Ingestion Pipeline", use_container_width=True, type="primary"):
        placeholder = st.empty()
        result_holder = {}

        def worker():
            result_holder["value"] = run_pipeline()

        thread = threading.Thread(target=worker)
        thread.start()

        i = 0
        while thread.is_alive():
            placeholder.info(loading_messages[i % len(loading_messages)])
            i += 1
            time.sleep(3)

        thread.join()
        placeholder.empty()

        result, summary, final_message = result_holder["value"]
        st.session_state.pipeline_result = {
            "result": result,
            "summary": summary,
            "final_message": final_message,
            "completed_at": datetime.now().isoformat(timespec="seconds"),
        }

        st.success("Pipeline completed successfully!")

    if st.session_state.pipeline_result:
        st.divider()
        st.subheader("Final Agent Summary")
        st.write(st.session_state.pipeline_result["final_message"])

        if st.button("📊 View Results", use_container_width=True, type="primary"):
            goto("results")
            st.rerun()


# =========================================================
# PAGE: RESULTS
# =========================================================


def page_results() -> None:
    st.title("📊 Results")
    render_nav_trail()

    if st.button("← Back to Upload & Run"):
        goto("run")
        st.rerun()

    if not st.session_state.pipeline_result:
        st.warning(
            "No pipeline run found yet. Head back to the previous page and run "
            "the pipeline first."
        )
        return

    dataset_tables = build_dataset_table_map()
    if not dataset_tables:
        st.warning(
            "No dataset-specific silver/quarantine tables were found in the database yet."
        )
        return

    total_silver_rows = 0
    total_quarantine_rows = 0
    for dataset in dataset_tables:
        silver_table = dataset["silver_table"]
        quarantine_table = dataset["quarantine_table"]

        silver_count = table_row_count(silver_table) if silver_table else 0
        quarantine_count = table_row_count(quarantine_table) if quarantine_table else 0

        total_silver_rows += silver_count or 0
        total_quarantine_rows += quarantine_count or 0

    st.divider()

    st.subheader("Reports")
    report_col1, report_col2 = st.columns(2)

    with report_col1:
        st.markdown("**Validation Report**")
        validation_report = read_latest_report_entry(VALIDATION_REPORT_PATH)
        if validation_report:
            if validation_report.get("_error"):
                st.info(validation_report["_error"])
            else:
                validated_passed_rows = validation_report.get("row_count", "—")
                quarantine_rows = validation_report.get(
                    "quarantined_rows",
                    validation_report.get("quarantine_rows", "—"),
                )

                st.metric("Validated passed rows", validated_passed_rows)
                st.metric("Quarantine rows", quarantine_rows)
        else:
            st.info(f"No report found at `{VALIDATION_REPORT_PATH}`.")

    with report_col2:
        st.markdown("**Transformation Report**")
        transformation_report = read_latest_report_entry(TRANSFORMATION_REPORT_PATH)
        if transformation_report:
            if transformation_report.get("_error"):
                st.info(transformation_report["_error"])
            else:
                transformations = transformation_report.get(
                    "transformations_applied", []
                )
                operation_names = [
                    operation.get("operation")
                    for operation in transformations
                    if isinstance(operation, dict) and operation.get("operation")
                ]
                rows_affected = sum(
                    operation.get("rows_affected", 0)
                    for operation in transformations
                    if isinstance(operation, dict) and operation.get("rows_affected")
                )

                if operation_names:
                    st.metric("Transformations applied", len(operation_names))
                    st.metric("Rows affected", rows_affected)
                else:
                    st.info("No transformations were recorded for the latest run.")
        else:
            st.info(f"No report found at `{TRANSFORMATION_REPORT_PATH}`.")

    st.divider()

    st.subheader("Dataset Snapshots")

    tab_labels: list[str] = [str(dataset["dataset"]) for dataset in dataset_tables]
    dataset_tabs = st.tabs(tab_labels)

    for dataset, dataset_tab in zip(dataset_tables, dataset_tabs):
        dataset_name = str(dataset["dataset"])
        silver_table = dataset["silver_table"]
        quarantine_table = dataset["quarantine_table"]

        with dataset_tab:
            summary_col1, summary_col2 = st.columns(2)
            with summary_col1:
                silver_count = table_row_count(silver_table) if silver_table else None
                st.metric(
                    "✅ Silver rows",
                    silver_count if silver_count is not None else "—",
                )
            with summary_col2:
                quarantine_count = (
                    table_row_count(quarantine_table) if quarantine_table else None
                )
                st.metric(
                    "🚧 Quarantine rows",
                    quarantine_count if quarantine_count is not None else "—",
                )

            st.markdown(
                '<span class="badge-silver">Silver — first 5 rows</span>',
                unsafe_allow_html=True,
            )
            if silver_table:
                silver_sample = load_table_sample(silver_table, limit=5)
                if silver_sample is not None:
                    st.dataframe(silver_sample, use_container_width=True)
                else:
                    st.info(f"Could not load a sample from the `{silver_table}` table.")
            else:
                st.info(f"No silver table found for dataset `{dataset_name}`.")

            st.markdown(
                '<span class="badge-quarantine">Quarantine — first 5 rows</span>',
                unsafe_allow_html=True,
            )
            if quarantine_table:
                quarantine_sample = load_table_sample(quarantine_table, limit=5)
                if quarantine_sample is not None:
                    st.dataframe(quarantine_sample, use_container_width=True)
                else:
                    st.info(
                        f"Could not load a sample from the `{quarantine_table}` table."
                    )
            else:
                st.info(f"No quarantine table found for dataset `{dataset_name}`.")

    st.divider()

    if st.button("📝 Rate this tool", use_container_width=True, type="primary"):
        goto("survey")
        st.rerun()


# =========================================================
# PAGE: SURVEY
# =========================================================


def page_survey() -> None:
    st.title("📝 Quick Survey")
    st.caption("Your feedback helps evaluate AgentTeam.")
    render_nav_trail()

    if st.button("← Back to Results"):
        goto("results")
        st.rerun()

    st.markdown(
        '<div class="card">'
        "Thanks for trying AgentTeam! Please take a moment to fill out our survey.<br><br>"
        "We appreciate your time and feedback greatly!"
        "</div>",
        unsafe_allow_html=True,
    )

    st.link_button(
        "📝 Open Survey",
        NON_DEV_GOOGLE_FORM_URL,
        use_container_width=True,
        type="primary",
    )

    st.divider()
    if st.button("🏠 Back to Home", use_container_width=True):
        goto("home")
        st.rerun()


# =========================================================
# ROUTER
# =========================================================

PAGES = {
    "home": page_home,
    "run": page_run,
    "results": page_results,
    "survey": page_survey,
}

PAGES.get(st.session_state.page, page_home)()
