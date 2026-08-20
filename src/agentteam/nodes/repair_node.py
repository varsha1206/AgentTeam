"""Repair agent node and router."""

import logging
from pathlib import Path

from langchain_core.messages import HumanMessage

from agentteam.agents.repair_agent import repair_agent_app
from agentteam.graph.state import GraphState
from agentteam.models.structured_outputs import ErrorReport, RepairResult
from agentteam.utils.base_node import BaseAgentNode, BaseRouter
from agentteam.utils.result_parser import parse_repair_result

logger = logging.getLogger(__name__)


class RepairNode(BaseAgentNode):
    def get_agent(self):
        return repair_agent_app(self.llm_model, self.workspace)

    def build_instructions(self, state: GraphState) -> list[HumanMessage]:
        repair_target = state.get("repair_target")
        repair_error = state.get("repair_error", [])
        script_path = state.get("repair_script_path", "")
        bronze_files = state.get("bronze_layer", [])
        filename = Path(bronze_files[0]).name if bronze_files else ""

        task = (
            "repair_transformation"
            if repair_target == "transformation"
            else "repair_retrieval"
        )

        return [
            self._build_agent_instruction(
                task=task,
                script_to_repair=script_path,
                errors=repair_error,
                context=f"filename: {filename}",
            )
        ]

    def parse_result(self, messages: list) -> RepairResult:
        return parse_repair_result(messages, self._build_structured_llm(RepairResult))

    def update_state(self, state: GraphState, results: list[RepairResult]) -> dict:
        repair_attempts = state.get("repair_attempts", 0) + 1

        result = (
            results[0]
            if results
            else RepairResult(
                status="failed",
                errors=[
                    ErrorReport(
                        error="Repair produced no result.",
                        stage="repair",
                        error_type=None,
                        should_repair=True,
                    )
                ],
                summary="Repair produced no result.",
                script_path=None,
            )
        )
        logger.info(f"Repair status: {result.status} — attempt {repair_attempts}")
        return {
            "repaired_data": result.model_dump(),
            "repair_attempts": repair_attempts,
            "repair_error": result.errors,
            "repair_script_path": result.script_path,
            "errors": result.errors,
        }


class RepairRouter(BaseRouter):
    def get_result(self, state: GraphState) -> RepairResult:
        repaired = state.get("repaired_data", {})
        return (
            RepairResult(**repaired)
            if repaired
            else RepairResult(
                status="failed",
                errors=[
                    ErrorReport(
                        error="No repair data found.",
                        stage="repair",
                        error_type=None,
                        should_repair=False,
                    )
                ],
                summary="No repair data found.",
            )
        )

    def route(self, state: GraphState) -> str:
        repair_attempts = state.get("repair_attempts", 0)
        if repair_attempts > 2:
            logger.warning(
                f"Max repair attempts reached ({repair_attempts}), ending pipeline"
            )
            return "end"
        result = self.get_result(state)
        next_stage = ""
        if result.status == "complete":
            state["needs_repair"] = False
            if state["repair_target"] == "retrieval":
                logger.info("Repair complete for retrieval stage")
                next_stage = "retrieval_agent"
            elif state["repair_target"] == "transformation":
                logger.info("Repair complete for transformation stage")
                next_stage = "validation_agent"
            else:
                logger.info("Repair complete for validation stage")
                next_stage = "end"
        return next_stage
