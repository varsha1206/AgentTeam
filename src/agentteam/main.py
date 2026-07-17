"""
main.py - Test entrypoint for the AgentTeam pipeline
"""

import logging
import uuid
from pathlib import Path

import colorlog

from agentteam.agents.orchestrator_agent import Orchestrator
from agentteam.storage.sqlite_store import SQLiteStore
from agentteam.utils.plugin_registry import PluginRegistry


def get_project_root() -> Path:
    """
    Returns project root (AgentTeam/).
    src/agentteam/main.py -> goes up 3 levels
    """
    return Path(__file__).resolve().parents[2]


def setup_logging():
    workspace = get_project_root() / "workspace"
    logs_dir = workspace / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_file = logs_dir / "execution.log"

    # overwrite log on every run
    file_handler = logging.FileHandler(
        log_file,
        mode="w",
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
    )

    console_handler = colorlog.StreamHandler()
    console_handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s %(levelname)-8s %(name)s: %(message)s%(reset)s",
            datefmt="%H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # quiet down noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)


setup_logging()
logger = logging.getLogger(__name__)


def create_workspace() -> Path:
    """
    Ensure workspace structure exists.
    """
    root = get_project_root()
    workspace = root / "workspace"

    required_dirs = [
        "input",
        "generated",
        "output/bronze",
        "output/silver",
        "output/quarantine",
        "plugins",
        "logs",
        "temp",
        "staged_input",
    ]

    for d in required_dirs:
        (workspace / d).mkdir(parents=True, exist_ok=True)

    return workspace


def stream_pipeline(stream) -> dict:
    """
    Consume a pipeline stream, logging each agent message as it arrives.
    Returns the final state.
    """
    print("===== STREAMING PIPELINE =====\n")
    final_chunk = {}

    for chunk in stream:
        final_chunk = chunk
        messages = chunk.get("messages", [])
        if not messages:
            continue

        msg = messages[-1]
        role = getattr(msg, "type", "unknown")
        content = getattr(msg, "content", "")
        name = getattr(msg, "name", "")
        label = f"{role}/{name}" if name else role

        if isinstance(content, str) and content.strip():
            print(f"[{label}]\n{content}\n")
        elif isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and block.get("text", "").strip():
                    print(f"[{label}]\n{block['text']}\n")
                elif block.get("type") == "tool_use":
                    print(
                        f"[tool_call/{block['name']}] input={block.get('input', {})}\n"
                    )
                elif block.get("type") == "tool_result":
                    print(f"[tool_result]\n{block.get('content', '')}\n")

    return final_chunk


def log_final_state(result: dict) -> None:
    """
    Log the final graph state after pipeline completion.
    """
    print("===== FINAL STATE =====\n")

    skip_keys = {"messages"}

    for key, value in result.items():
        if key in skip_keys:
            continue
        print(f"[{key}]\n{value}\n")


def main():
    workspace_path = get_project_root() / "workspace"

    registry = PluginRegistry(workspace_path / "plugins")
    registry.load_all()

    if not workspace_path.exists():
        raise FileNotFoundError(f"Workspace not found at {workspace_path}")

    orchestrator = Orchestrator(workspace=workspace_path)

    initial_state = {
        "messages": [
            {
                "role": "user",
                "content": (
                    "Retrieve the dataset from the input folder. "
                    "Read all available files, summarise their contents, "
                    "and write the raw data to the output folder."
                ),
            }
        ],
        "raw_input": str(workspace_path / "input" / "employee_data.csv"),
        "workspace_path": workspace_path,
        "execution_plan": [],
        "final_output": None,
        "retrieved_data": {},
        "validated_data": {},
        "repaired_data": {},
        "bronze_layer": [],
        "silver_layer": [],
        "quarantine_layer": [],
        "repair_target": None,
        "repair_error": None,
        "repair_attempts": 0,
        "errors": [],
        "artifacts": {},
        "metadata": {
            "run_id": str(uuid.uuid4()),
            "environment": "local",
        },
        "repair_script_path": None,
    }

    result = stream_pipeline(
        orchestrator.stream(initial_state, thread_id="test-thread-001")
    )

    log_final_state(result)

    # Persist the run to SQLite
    store = SQLiteStore(
        db_path=workspace_path / "agentteam.db",
        llm=orchestrator.llm_model,  # reuse the same LLM instance
    )
    store.run_persistance(
        workspace_path=workspace_path,
        repair_attempts=result.get("repair_attempts", 0),
        repaired_data=result.get("repaired_data", {}),
        run_id=result.get("metadata", {}).get("run_id", "unknown"),
        started_at=result.get("metadata", {}).get("started_at", "unknown"),
    )
    summary = store.query_run_summary(
        result.get("metadata", {}).get("run_id", "unknown")
    )
    logger.info(f"Run summary: {summary}")


if __name__ == "__main__":
    main()
