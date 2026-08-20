"""Validation agent node and router."""

import logging
from pathlib import Path

from langchain_core.messages import HumanMessage

from agentteam.agents.validation_agent import validation_agent_app
from agentteam.graph.state import GraphState
from agentteam.models.structured_outputs import (
    ErrorReport,
    RoutingDecision,
    ValidatorResult,
)
from agentteam.utils.base_node import BaseAgentNode, BaseRouter
from agentteam.utils.result_parser import parse_validator_result
from agentteam.utils.routing_utils import decide_routing

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
        staged_input_dir = self.workspace / "staged_input"
        staged_input_files = list(staged_input_dir.glob("*"))
        # revalidation = state.get("repair_target") is None and state.get("repaired_data")
        repair_target = state.get("repair_target")
        if repair_target == "validation" and state.get("repaired_data"):
            revalidation = True
        else:
            print(f"repaired target: {repair_target}")
            revalidation = False

        if revalidation:
            # after repair — validate only, skip transformation
            return [
                self._build_agent_instruction(
                    task="validate_only",
                    target_file=str(
                        self.workspace / "temp" / f"transformed_{Path(f).name}"
                    ),
                    context=f"filename for rules lookup: {Path(f).name}",
                )
                for f in staged_input_files
            ]

        return [
            self._build_agent_instruction(
                task="transform_and_validate",
                target_file=file_path,
                context=f"filename for rules lookup: {Path(file_path).name}",
            )
            for file_path in staged_input_files
        ]

    def parse_result(self, messages: list) -> ValidatorResult:
        return parse_validator_result(
            messages, self._build_structured_llm(ValidatorResult)
        )

    def update_state(
        self, state: GraphState, results: list[ValidatorResult]
    ) -> tuple[dict, bool]:
        silver_dir = self.workspace / "output" / "silver"
        all_errors = [e for r in results for e in r.errors]
        silver_files = []
        staged_input_dir = self.workspace / "staged_input"
        staged_input_files = list(staged_input_dir.glob("*"))

        for file_path, result in zip(staged_input_files, results):
            if result.validation_outcome == "PASS":
                stem = Path(file_path).stem
                matches = list(silver_dir.glob(f"*{stem}*"))
                if matches:
                    silver_files.append(str(matches[0]))
                    logger.info(f"Silver file found: {matches[0]}")
                else:
                    logger.warning(f"No silver file found for {file_path}")

        overall_outcome = (
            "PASS" if all(r.validation_outcome == "PASS" for r in results) else "FAIL"
        )
        combined = ValidatorResult(
            status="complete",
            validation_outcome=overall_outcome,
            errors=all_errors,
            summary=f"Validated {len(results)} files — {len(silver_files)} passed.",
        )
        can_repair = False
        if overall_outcome == "FAIL":
            can_repair = any(e.should_repair for e in all_errors)

        logger.info(f"Validation complete — outcome: {overall_outcome}")
        return (
            {
                "validated_data": combined.model_dump(),
                "silver_layer": silver_files,
                "errors": all_errors,
            },
            can_repair,
        )

    def as_node(self):
        agent = self.get_agent()

        def node(state: GraphState) -> dict:
            staged_input_dir = self.workspace / "staged_input"
            staged_input_files = list(staged_input_dir.glob("*"))
            staged_input_filenames = [f.name for f in staged_input_files]

            if not staged_input_files:
                logger.warning("No staged input files to validate")
                empty = ValidatorResult(
                    status="failed",
                    validation_outcome="FAIL",
                    errors=[
                        ErrorReport(
                            stage="no_error",
                            error=None,
                            error_type=None,
                            should_repair=False,
                        )
                    ],
                    summary="No files to validate.",
                )
                return {
                    "validated_data": empty.model_dump(),
                    "silver_layer": [],
                    "errors": empty.errors,
                    "messages": [],
                }

            # only clear reports on first pass, not after repair
            if not state.get("repaired_data"):
                self._clear_stale_reports()

            instructions = self.build_instructions(state)
            all_messages = []
            all_results = []
            repair_target = None
            needs_repair = state.get("needs_repair")
            repair_error = None
            repair_script_path = None

            for instruction, file_path in zip(instructions, staged_input_filenames):
                messages = self._invoke_agent(agent, instruction)
                all_messages.extend(messages)
                all_results.append(self.parse_result(messages))

                # detect repair need per file — use first file that needs repair
                if needs_repair is None:
                    repair_target, repair_error, repair_script_path = (
                        self._detect_repair_needed(messages, file_path)
                    )
                    if repair_target:
                        needs_repair = True
                    else:
                        needs_repair = False

            state_update, can_repair = self.update_state(state, all_results)
            state_update["messages"] = all_messages

            if (
                can_repair and needs_repair
            ):  # Validation failed with OUTCOME: FAIL and repairable errors
                state_update["repair_error"] = state_update.get("errors")

            if (repair_target == "validation") or (
                repair_target == "transformation"
            ):  # Validation failed with SCRIPT_FAILED
                state_update["repair_target"] = repair_target
                state_update["repair_error"] = repair_error
                state_update["repair_script_path"] = repair_script_path
                logger.info(f"Repair needed — target: {repair_target}")

            return state_update

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
                errors=[
                    ErrorReport(
                        error="validated_data was empty.",
                        stage="validation",
                        error_type=None,
                        should_repair=True,
                    )
                ],
                summary="No validation data found.",
            )
        )

    def route(self, state: GraphState) -> str:
        if state.get("needs_repair") is True:
            logger.info("Routing to repair_agent — repair needed")
            return "repair_agent"
        result = self.get_result(state)
        return decide_routing(
            result,
            self._build_structured_llm(RoutingDecision),
            self.routing_prompt,
        ).next_node
