"""Validation agent node and router."""

import json
import logging
from pathlib import Path

from langchain_core.messages import HumanMessage

from agentteam.agents.validation_agent import validation_agent_app
from agentteam.graph.state import GraphState
from agentteam.models.structured_outputs import RoutingDecision, ValidatorResult
from agentteam.utils.base_node import BaseAgentNode, BaseRouter
from agentteam.utils.message_utils import extract_tool_outputs
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

    def _detect_repair_needed(
        self, messages: list, file_path: str
    ) -> tuple[str | None, str | None, str | None]:
        """
        Inspect agent messages to detect if repair is needed.
        Returns (repair_target, repair_error, repair_script_path) or (None, None, None).
        """
        tool_outputs = extract_tool_outputs(messages)

        # detect script crash
        crashed_output = next(
            (o for o in tool_outputs if "SCRIPT_FAILED" in str(o)), None
        )
        if crashed_output:
            script_path = self._find_transformation_script(file_path)
            logger.warning(f"Script crash detected for {file_path}")
            return "transformation", str(crashed_output), script_path

        # detect 100% quarantine by reading transformation report
        transformation_report_path = (
            self.workspace / "logs" / "transformation_report.json"
        )
        if transformation_report_path.exists():
            try:
                reports = json.loads(
                    transformation_report_path.read_text(encoding="utf-8")
                )
                if isinstance(reports, list):
                    report = reports[-1]
                else:
                    report = reports
                valid_rows = report.get("total_rows_output", 1)
                quarantined_rows = report.get("quarantined_rows", 0)
                if valid_rows == 0 and quarantined_rows > 0:
                    script_path = self._find_transformation_script(file_path)
                    logger.warning(
                        f"100% quarantine detected for {file_path} — {quarantined_rows} rows quarantined"
                    )
                    return (
                        "transformation",
                        f"100% of rows quarantined ({quarantined_rows} rows). Transformation rules are too strict.",
                        script_path,
                    )
            except Exception as e:
                logger.warning("Could not read transformation report: %s", e)
        validation_report_path = self.workspace / "logs" / "validation_report.json"
        if validation_report_path.exists():
            try:
                reports = json.loads(validation_report_path.read_text(encoding="utf-8"))
                if isinstance(reports, list):
                    report = reports[-1]
                else:
                    report = reports
                valid_status = report.get("status", "PASS")
                if valid_status == "FAIL":
                    script_path = self._find_validation_script(file_path)
                    logger.warning(
                        f"Validation failure detected for {file_path} — status: {valid_status}"
                    )
                    return (
                        "validation",
                        "Validation failed. Check validation report for details.",
                        script_path,
                    )
            except Exception as e:
                logger.warning("Could not read validation report: %s", e)

        return None, None, None

    def _find_transformation_script(self, file_path: str) -> str | None:
        """Find the transformation script for a given file."""
        stem = Path(file_path).stem
        script_path = self.workspace / "generated" / f"transformation_{stem}.py"
        return str(script_path) if script_path.exists() else None

    def _find_validation_script(self, file_path: str) -> str | None:
        """Find the validation script for a given file."""
        stem = Path(file_path).stem
        script_path = self.workspace / "generated" / f"validation_{stem}.py"
        return str(script_path) if script_path.exists() else None

    def build_instructions(self, state: GraphState) -> list[HumanMessage]:
        bronze_files = state.get("bronze_layer", [])
        revalidation = state.get("repair_target") is None and state.get("repaired_data")

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
                for f in bronze_files
            ]

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

            # only clear reports on first pass, not after repair
            if not state.get("repaired_data"):
                self._clear_stale_reports()

            instructions = self.build_instructions(state)
            all_messages = []
            all_results = []
            repair_target = None
            repair_error = None
            repair_script_path = None

            for instruction, file_path in zip(instructions, bronze_files):
                messages = self._invoke_agent(agent, instruction)
                all_messages.extend(messages)
                all_results.append(self.parse_result(messages))

                # detect repair need per file — use first file that needs repair
                if repair_target is None:
                    repair_target, repair_error, repair_script_path = (
                        self._detect_repair_needed(messages, file_path)
                    )

            state_update = self.update_state(state, all_results)
            state_update["messages"] = all_messages

            if repair_target:
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
                errors=["validated_data was empty."],
                summary="No validation data found.",
            )
        )

    def route(self, state: GraphState) -> str:
        if state.get("repair_target"):
            logger.info("Routing to repair_agent — repair needed")
            return "repair_agent"
        result = self.get_result(state)
        return decide_routing(
            result,
            self._build_structured_llm(RoutingDecision),
            self.routing_prompt,
        ).next_node
