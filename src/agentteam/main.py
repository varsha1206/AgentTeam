"""
main.py - Test entrypoint for the AgentTeam pipeline
"""

import logging
from pathlib import Path

import colorlog

from agentteam.agents.orchestrator_agent import Orchestrator


def setup_logging():
    handler = colorlog.StreamHandler()
    handler.setFormatter(
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
    root_logger.handlers = [handler]

    # quiet down noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)


setup_logging()
logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """
    Returns project root (AgentTeam/).
    src/agentteam/main.py -> goes up 3 levels
    """

    return Path(__file__).resolve().parents[2]


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
        "logs",
        "temp",
    ]

    for d in required_dirs:
        (workspace / d).mkdir(parents=True, exist_ok=True)

    return workspace


def stream_pipeline(stream) -> dict:
    """
    Consume a pipeline stream, logging each agent message as it arrives.
    Returns the final state.
    """
    logger.info("===== STREAMING PIPELINE =====\n")
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
            logger.info(f"[{label}]\n{content}\n")
        elif isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and block.get("text", "").strip():
                    logger.info(f"[{label}]\n{block['text']}\n")
                elif block.get("type") == "tool_use":
                    logger.info(
                        f"[tool_call/{block['name']}] input={block.get('input', {})}\n"
                    )
                elif block.get("type") == "tool_result":
                    logger.info(f"[tool_result]\n{block.get('content', '')}\n")

    return final_chunk


def log_final_state(result: dict) -> None:
    """
    Log the final graph state after pipeline completion.
    """

    logger.info("===== FINAL STATE =====\n")

    skip_keys = {"messages"}  # already logged during streaming

    for key, value in result.items():
        if key in skip_keys:
            continue
        logger.info(f"[{key}]\n{value}\n")


def main():
    workspace_path = get_project_root() / "workspace"

    if not workspace_path.exists():
        raise FileNotFoundError(f"Workspace not found at {workspace_path}")

    # -----------------------------
    # Build orchestrator
    # -----------------------------
    orchestrator = Orchestrator(workspace=workspace_path)

    # -----------------------------
    # Initial state
    # -----------------------------
    initial_state = {
        "messages": [
            {
                "role": "user",
                "content": (
                    "Retrieve the dataset from the input folder. "
                    "Read all available CSV files, summarise their contents, "
                    "and write the raw data to the output folder."
                ),
            }
        ],
        "raw_input": str(workspace_path / "input" / "sample.csv"),
        "workspace_path": workspace_path,
        "execution_plan": [],
        "final_output": None,
        "retrieved_data": {},
        "validated_data": {},
        "repaired_data": {},
        "errors": [],
        "artifacts": {},
        "metadata": {
            "run_id": "test-run-001",
            "environment": "local",
        },
    }

    # -----------------------------
    # Run + stream
    # -----------------------------
    result = stream_pipeline(
        orchestrator.stream(initial_state, thread_id="test-thread-001")
    )
    log_final_state(result)


if __name__ == "__main__":
    main()
