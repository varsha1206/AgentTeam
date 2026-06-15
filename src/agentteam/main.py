"""
main.py - Test entrypoint for the AgentTeam pipeline
"""

import logging
from pathlib import Path

from langchain_core.runnables import RunnableConfig

from agentteam.agents.orchestrator_agent import build_app

logging.basicConfig(level=logging.INFO)
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
        "outputs",
        "logs",
        "temp",
    ]

    for d in required_dirs:
        (workspace / d).mkdir(parents=True, exist_ok=True)

    return workspace


def stream_pipeline(app, initial_state: dict, config: RunnableConfig) -> dict:
    """
    Stream pipeline execution, logging each agent message as it arrives.
    Returns the final state.
    """

    logger.info("===== STREAMING PIPELINE =====\n")

    final_chunk = {}

    for chunk in app.stream(initial_state, config=config, stream_mode="values"):
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
    """
    Run the AgentTeam pipeline.
    """

    # -----------------------------
    # Workspace
    # -----------------------------
    workspace_path = get_project_root() / "workspace"
    logger.info(f"Workspace: {workspace_path}")

    # -----------------------------
    # Build app
    # -----------------------------
    app = build_app(workspace=workspace_path)

    # -----------------------------
    # Initial graph state
    # -----------------------------
    initial_state = {
        "messages": [
            {
                "role": "user",
                "content": (
                    "Retrieve the dataset from the input folder. "
                    "Read all available CSV files, summarise their contents, "
                    "and write the raw data to the outputs folder."
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

    config: RunnableConfig = {"configurable": {"thread_id": "test-thread-001"}}

    # -----------------------------
    # Run + stream
    # -----------------------------
    result = stream_pipeline(app, initial_state, config)

    # -----------------------------
    # Final state
    # -----------------------------
    log_final_state(result)


if __name__ == "__main__":
    main()
