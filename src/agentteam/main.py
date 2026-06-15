"""
main.py - Test entrypoint for the AgentTeam pipeline
"""

import logging
from pathlib import Path

from langchain_core.runnables import RunnableConfig

from agentteam.agents.orchestrator_agent import build_app

logging.basicConfig()
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


def main():
    """
    Run the AgentTeam pipeline.
    """

    # -----------------------------
    # Workspace
    # -----------------------------
    workspace_path = create_workspace()

    # -----------------------------
    # Build app
    # -----------------------------
    app = build_app()

    # -----------------------------
    # Initial graph state
    # -----------------------------
    initial_state = {
        "messages": [
            {
                "role": "user",
                "content": (
                    "Read the CSV file in the workspace input folder "
                    "and store the first five rows in a new CSV."
                ),
            }
        ],
        "raw_input": (
            "Read the CSV file in workspace/input "
            "and save the first five rows into "
            "workspace/outputs."
        ),
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

    logger.info("===== INVOKING AGENT PIPELINE =====")

    result = app.invoke(
        initial_state,
        config=config,
    )

    logger.info("\n===== FINAL STATE =====")

    for key, value in result.items():
        logger.info(f"\n[{key}]")
        logger.info(value)


if __name__ == "__main__":
    main()
