"""
test_injection.py

Deterministic failure injection state for the evaluation harness.
Fully decoupled from validation_rules.yaml — this is evaluation
infrastructure, not user-facing pipeline configuration, and must
never be mistaken for one by a real pipeline user.

The injection marker lives in a dedicated file inside the workspace,
written by the experiment runner before a run and read by the
script-writing tools after generation, before execution. The LLM
never sees this file or is made aware of its contents.
"""

import json
from pathlib import Path

INJECTION_FILENAME = ".eval_injection.json"


def set_injection(
    workspace_path: Path, target_filename: str, failure_type: str
) -> None:
    """
    Marks `target_filename` (e.g. 'eval_dataset_1.csv') for deterministic
    script corruption on its next generated script.

    failure_type must be one of: syntax_error, import_error, runtime_type_error.
    """
    path = workspace_path / INJECTION_FILENAME
    path.write_text(
        json.dumps({"target_filename": target_filename, "failure_type": failure_type}),
        encoding="utf-8",
    )


def clear_injection(workspace_path: Path) -> None:
    """Removes any active injection marker. Safe to call if none exists."""
    path = workspace_path / INJECTION_FILENAME
    if path.exists():
        path.unlink()


def get_injection(workspace_path: Path, filename: str) -> str | None:
    """
    Returns the failure_type configured for `filename`, or None.
    `filename` is the target CSV name the generated script operates on.
    """
    path = Path(workspace_path / INJECTION_FILENAME)
    if not path.exists():
        print(f"No injection marker found for {filename} in {workspace_path}")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        print(f"Error reading injection marker for {filename} in {workspace_path}")
        return None
    if data.get("target_filename") != filename:
        return None
    return data.get("failure_type")
