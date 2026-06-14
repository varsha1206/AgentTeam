from __future__ import annotations

import logging
from typing import Callable, List

from agentteam.graph.state import GraphState

logging.basicConfig()
logger = logging.getLogger(__name__)

# Type alias for pipeline steps (agents)
PipelineStep = Callable[[GraphState], GraphState]


class Workflow:
    """
    Minimal execution engine for the agent pipeline.

    Responsibilities:
    - execute steps in order
    - pass shared GraphState
    - enforce traceability
    """

    def __init__(self, steps: List[PipelineStep]):
        self.steps = steps

    def run(self, state: GraphState) -> GraphState:
        """
        Execute full pipeline sequentially.
        """

        state.add_trace(step="workflow_start", agent="workflow")

        for step_fn in self.steps:
            step_name = step_fn.__name__

            state.add_trace(
                step="step_start",
                agent=step_name,
                input_preview=self._safe_preview(state),
            )

            try:
                state = step_fn(state)

                state.add_trace(
                    step="step_end",
                    agent=step_name,
                    output_preview=self._safe_preview(state),
                )
                logger.info("Added trace for step: %s", step_name)

            except Exception as e:
                state.add_error(f"{step_name}: {str(e)}")
                logger.error("Error in step %s: %s", step_name, str(e))
                state.add_trace(
                    step="step_error",
                    agent=step_name,
                    output_preview=str(e),
                )
                logger.info("Added trace for step: %s", step_name)

                # fail fast (you can switch this later to "continue mode")
                break

        state.add_trace(step="workflow_end", agent="workflow")

        return state

    # Utility
    def _safe_preview(self, state: GraphState, max_len: int = 300) -> str:
        """
        Avoid dumping full state into trace logs.
        Keeps debugging lightweight.
        """
        try:
            raw = state.model_dump()

            preview = {
                "raw_input": raw.get("raw_input"),
                "retrieved_data": raw.get("retrieved_data"),
                "validated_data": raw.get("validated_data"),
                "final_output": raw.get("final_output"),
                "errors": raw.get("errors"),
            }

            return str(preview)[:max_len]

        except Exception:
            return "<unserializable_state>"
