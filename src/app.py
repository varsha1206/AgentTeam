import threading
import time
from pathlib import Path

import streamlit as st

from agentteam.main import run_pipeline

# -------------------------------------------------------
# CONFIG
# -------------------------------------------------------

st.set_page_config(
    page_title="AgentTeam",
    page_icon="🤖",
    layout="centered",
)

workspace = Path(__file__).resolve().parents[1] / "workspace"
print(f"Workspace path: {workspace}")
validation_rules_dir = workspace / "configs" / "validation_rules"


def save_uploaded_files(uploaded_files, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)

    for old_file in target_dir.glob("*"):
        old_file.unlink()

    for uploaded_file in uploaded_files:
        with open(target_dir / uploaded_file.name, "wb") as file_handle:
            file_handle.write(uploaded_file.getbuffer())


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

# -------------------------------------------------------
# STYLE
# -------------------------------------------------------

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
  --text-main: #e5f2ea;
  --text-muted: #b2cbbb;
  --border: rgba(143, 211, 170, 0.18);
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

.stButton>button{
background:linear-gradient(180deg, var(--accent-soft), var(--accent));
color:#0c1714;
border:none;
border-radius:0.9rem;
height:48px;
font-weight:bold;
box-shadow:0 10px 22px rgba(111, 191, 143, 0.18);
}

.stButton>button:hover{
background:linear-gradient(180deg, #b8ebc7, #89d9a7);
color:#08120f;
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

</style>
""",
    unsafe_allow_html=True,
)

# -------------------------------------------------------
# TITLE
# -------------------------------------------------------

st.title("🤖 AgentTeam")

st.caption("LLM-powered Multi-Agent Data Ingestion Pipeline")

st.divider()

st.info(
    "Name each validation YAML using the same base name as the input file, for example "
    "`broken_employee_data.csv` -> `broken_employee_data.yaml`."
)

upload_tab, guide_tab = st.tabs(["Upload Files", "Validation Rules Guide"])

# -------------------------------------------------------
# FILE UPLOAD
# -------------------------------------------------------

with upload_tab:
    uploaded_files = st.file_uploader(
        "Upload your CSV and JSON files",
        type=["csv", "json"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        save_uploaded_files(uploaded_files, workspace / "input")
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
                    f"Validation rule '{uploaded_file.name}' does not match any uploaded "
                    "input file name. The YAML file should use the same base name as the "
                    "source file."
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
        "Each YAML file should describe the expected schema for one input file and any "
        "transformations or repair hints that should be applied. Keep the file name aligned "
        "with the dataset name so the pipeline can find the right rule automatically."
    )

    st.markdown(
        "**Derived example based on your existing `broken_employee_data.yaml`:**"
    )
    st.code(example_validation_rules, language="yaml")

    st.markdown(
        "**Recommended pattern**\n\n"
        "- `schema`: define each column, its type, and any constraints.\n"
        "- `transformations`: list the fixes or enrichments the repair agent should apply.\n"
        "- Match the YAML base name to the input file base name, for example `broken_employee_data.yaml`."
    )

# -------------------------------------------------------
# RUN BUTTON
# -------------------------------------------------------

loading_messages = [
    "🤖 Claude is assigning work...",
    "📂 Retrieval Agent is exploring your dataset...",
    "🔍 Validator is checking every record...",
    "🛠 Repair Agent is fixing inconsistencies...",
    "📦 Building Bronze, Silver and Quarantine layers...",
    "☕ Agents are debating the optimal solution...",
]

if st.button("Run Ingestion Pipeline", use_container_width=True):
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

    st.success("Pipeline completed successfully!")

    st.divider()

    st.subheader("Final Agent Summary")

    st.write(final_message)
