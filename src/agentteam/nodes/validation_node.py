"""Validation agent node and router."""

import logging
from pathlib import Path

from langchain_core.messages import HumanMessage

from agentteam.agents.validation_agent import validation_agent_app
from agentteam.graph.state import GraphState
from agentteam.models.structured_outputs import ValidatorResult
from agentteam.utils.base_node import BaseAgentNode, BaseRouter
from agentteam.utils.result_parser import parse_validator_result

logger = logging.getLogger(__name__)


class ValidationNode(BaseAgentNode):
    def get_agent(self):
        return validation_agent_app(self.llm_model, self.workspace)

    def _clear_stale_reports(self):
        for report in ["validation_report.json", "transformation_report.json"]:
            path = self.workspace / "logs" / report
            if path.exists():
                path.unlink()
        logger.info("Cleared stale reports")

    def build_instructions(self, state: GraphState) -> list[HumanMessage]:
        bronze_files = state.get("bronze_layer", [])
        return [
            self._build_agent_instruction(
                task="transform_and_validate",
                target_file=file_path,
                context=f"filename for rules lookup: {Path(file_path).name}",
            )
            for file_path in bronze_files
        ]

    def parse_result(self, messages: list) -> ValidatorResult:
        return parse_validator_result(
            messages, self._build_structured_llm(ValidatorResult)
        )

    def update_state(self, state: GraphState, results: list[ValidatorResult]) -> dict:
        silver_dir = self.workspace / "output" / "silver"
        all_errors = [e for r in results for e in r.errors]
        silver_files = []
        bronze_files = state.get("bronze_layer", [])

        for file_path, result in zip(bronze_files, results):
            if result.validation_outcome == "PASS":
                silver_path = silver_dir / Path(file_path).name
                if silver_path.exists():
                    silver_files.append(str(silver_path))

        overall_outcome = (
            "PASS" if all(r.validation_outcome == "PASS" for r in results) else "FAIL"
        )
        combined = ValidatorResult(
            status="complete",
            validation_outcome=overall_outcome,
            errors=all_errors,
            summary=f"Validated {len(results)} files — {len(silver_files)} passed.",
        )
        logger.info(f"Validation complete — outcome: {overall_outcome}")
        return {
            "validated_data": combined.model_dump(),
            "silver_layer": silver_files,
            "errors": all_errors,
        }

    def as_node(self):
        """Override to clear stale reports before running."""
        agent = self.get_agent()

        def node(state: GraphState) -> dict:
            bronze_files = state.get("bronze_layer", [])
            if not bronze_files:
                logger.warning("No bronze layer files to validate")
                empty = ValidatorResult(
                    status="failed",
                    validation_outcome="FAIL",
                    errors=["No bronze layer files found."],
                    summary="No files to validate.",
                )
                return {
                    "validated_data": empty.model_dump(),
                    "silver_layer": [],
                    "errors": empty.errors,
                    "messages": [],
                }

            self._clear_stale_reports()
            instructions = self.build_instructions(state)
            all_messages = []
            all_results = []

            for instruction in instructions:
                messages = self._invoke_agent(agent, instruction)
                all_messages.extend(messages)
                all_results.append(self.parse_result(messages))

            return self.update_state(state, all_results) | {"messages": all_messages}

        return node


class ValidationRouter(BaseRouter):
    def get_result(self, state: GraphState) -> ValidatorResult:
        validated = state.get("validated_data", {})
        return (
            ValidatorResult(**validated)
            if validated
            else ValidatorResult(
                status="failed",
                validation_outcome="FAIL",
                errors=["validated_data was empty."],
                summary="No validation data found.",
            )
        )
