"""
Retrieval agent: Responsible for retrieving data from external sources (APIs, databases, web scraping, etc.) and storing it in the graph state for downstream processing.
"""

import csv
import logging
from datetime import datetime

from agentteam.graph.state import GraphState

logging.basicConfig()
logger = logging.getLogger(__name__)


def retrieval_agent(state: GraphState) -> GraphState:
    """
    Dummy retrieval agent:
    - extracts input
    - writes to CSV
    - stores result in state
    """

    input_data = state.raw_input

    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "input": str(input_data),
        "status": "retrieved",
    }

    file_path = "retrieved_output.csv"

    # append to CSV
    file_exists = False
    try:
        with open(file_path, "r"):
            file_exists = True
    except FileNotFoundError:
        file_exists = False

    with open(file_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())

        if not file_exists:
            writer.writeheader()

        writer.writerow(row)

    # update state
    state.set_artifact("retrieval_csv", row)
    state.retrieved_data = row
    logger.info(f"Data retrieved and written to {file_path}: {row}")

    state.add_trace(
        step="retrieval_agent",
        agent="retrieval",
        action="write_csv",
        output_preview=str(row),
    )

    return state
