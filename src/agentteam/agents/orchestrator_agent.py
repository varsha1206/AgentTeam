"""
Orchestrator: manages the entire workflow of the data pipeline.
Uses a custom StateGraph for full control over state transitions.
"""

import logging
from pathlib import Path
from typing import cast

import hydra
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from omegaconf import DictConfig

from agentteam.agents.retrieval_agent import retrieval_agent_app
from agentteam.agents.validation_agent import validation_agent_app
from agentteam.graph.state import GraphState
from agentteam.models.structured_outputs import (
    RetrievalResult,
    RoutingDecision,
    ValidatorResult,
)

logger = logging.getLogger(__name__)

PHASE = 2


class Orchestrator:
    """
    Supervisor that manages the entire workflow of the data pipeline.
    Uses a custom StateGraph for full control over state transitions.
    """

    def __init__(self, workspace: Path, llm_model: BaseChatModel | None = None):
        if not workspace.exists():
            raise FileNotFoundError(f"Workspace not found at {workspace}")

        self.workspace = workspace
        self.cfg: DictConfig = self._load_config()
        self.llm_model: BaseChatModel = llm_model or self._build_llm()
        self.app = self._build_app()

    def _load_config(self) -> DictConfig:
        with hydra.initialize(version_base=None, config_path="../../../configs"):
            logger.info("Loading orchestrator config...")
            cfg = hydra.compose(
                config_name="config",
                overrides=["agents/orchestrator=default"],
            )
            logger.info("Orchestrator config loaded successfully")
            return cfg.agents.orchestrator

    def _build_llm(self) -> BaseChatModel:
        return ChatAnthropic(
            model_name="claude-haiku-4-5-20251001",
            timeout=10,
            stop=["end of response"],
            model_kwargs={
                "extra_headers": {"anthropic-beta": "prompt-caching-2024-07-31"}
            },
        )

    def _build_structured_llm(self, schema):
        """Returns an LLM bound to a specific structured output schema."""
        return self.llm_model.with_structured_output(schema)

    def _extract_tool_outputs(self, messages: list) -> list[str]:
        """Extract all tool output contents from a message list."""
        return [m.content for m in messages if hasattr(m, "type") and m.type == "tool"]

    def _extract_last_ai_message(self, messages: list) -> str:
        """Extract the content of the last AI message."""
        last_ai = next(
            (m for m in reversed(messages) if isinstance(m, AIMessage)),
            None,
        )
        if last_ai is None:
            return ""
        content = last_ai.content
        if isinstance(content, str):
            return content
        return "\n".join(
            item if isinstance(item, str) else str(item) for item in content
        )

    def _current_turn_messages(self, state: GraphState, result: dict) -> list:
        """Return only the messages added by the current agent invocation."""
        messages = result.get("messages", [])
        previous_count = len(state.get("messages", []))
        return messages[previous_count:] if previous_count < len(messages) else messages

    def _extract_path_from_outputs(
        self, tool_outputs: list[str], *keywords: str
    ) -> str | None:
        """Find the first tool output containing all keywords that looks like a file path."""
        for output in tool_outputs:
            output_str = str(output).strip()
            if (
                all(kw in output_str for kw in keywords)
                and "\n" not in output_str
                and len(output_str) < 300
            ):
                return output_str
        return None

    def _parse_retrieval_result(self, messages: list) -> RetrievalResult:
        """Uses structured LLM output to extract RetrievalResult from agent messages."""
        tool_outputs = self._extract_tool_outputs(messages)
        summary = self._extract_last_ai_message(messages)
        try:
            extraction_llm = self._build_structured_llm(RetrievalResult)
            result = cast(
                RetrievalResult,
                extraction_llm.invoke(
                    [
                        HumanMessage(
                            content=(
                                f"Extract the retrieval result from the following agent output.\n\n"
                                f"Agent summary:\n{summary}\n\n"
                                f"Tool outputs:\n{chr(10).join(tool_outputs)}\n\n"
                                f"Extract: status, summary, script_path, output_path, errors."
                                f'errors must be a JSON array of strings, e.g. [] or ["error1"].\n'
                                f"Never return errors as a plain string."
                            )
                        )
                    ],
                ),
            )
            return result
        except Exception as e:
            logger.warning(f"Structured extraction failed, using fallback: {e}")
            return self._fallback_parse_retrieval(summary, tool_outputs)

    def _fallback_parse_retrieval(
        self, summary: str, tool_outputs: list[str]
    ) -> RetrievalResult:
        """Rule-based fallback extraction if LLM parsing fails."""
        script_path = self._extract_path_from_outputs(
            tool_outputs, "generated", "retrieval", ".py"
        )
        output_path = self._extract_path_from_outputs(tool_outputs, "output", ".csv")
        status = "complete" if output_path else "failed"
        return RetrievalResult(
            status=status,
            summary=summary,
            script_path=script_path,
            output_path=output_path,
            errors=[] if status == "complete" else ["No output CSV produced."],
        )

    def _parse_validator_result(self, messages: list) -> ValidatorResult:
        """Uses structured LLM output to extract ValidatorResult from agent messages."""
        tool_outputs = self._extract_tool_outputs(messages)
        summary = self._extract_last_ai_message(messages)
        try:
            extraction_llm = self._build_structured_llm(ValidatorResult)
            result = cast(
                ValidatorResult,
                extraction_llm.invoke(
                    [
                        HumanMessage(
                            content=(
                                f"Extract the validation result from the following agent output.\n\n"
                                f"Agent summary:\n{summary}\n\n"
                                f"Tool outputs:\n{chr(10).join(tool_outputs)}\n\n"
                                f"Extract: status, validation_outcome, script_path, report_path, errors, summary."
                            )
                        )
                    ],
                ),
            )
            logger.info(f"Structured validator result entire: {result}")
            return result
        except Exception as e:
            logger.warning(
                f"Structured validator extraction failed, using fallback: {e}"
            )
            return self._fallback_parse_validator(summary, tool_outputs)

    def _fallback_parse_validator(
        self, summary: str, tool_outputs: list[str]
    ) -> ValidatorResult:
        """Rule-based fallback extraction if LLM parsing fails."""
        script_path = self._extract_path_from_outputs(
            tool_outputs, "generated", "validation", ".py"
        )
        report_path = self._extract_path_from_outputs(
            tool_outputs, "logs", "validation_report.json"
        )
        validation_outcome = (
            "FAIL" if any("ERROR" in o or "FAIL" in o for o in tool_outputs) else "PASS"
        )
        return ValidatorResult(
            status="complete",
            validation_outcome=validation_outcome,
            script_path=script_path,
            report_path=report_path,
            errors=[],
            summary=summary,
        )

    def _decide_routing(
        self, result: RetrievalResult | ValidatorResult
    ) -> RoutingDecision:
        """Uses structured LLM output to decide the next node."""
        try:
            routing_llm = self._build_structured_llm(RoutingDecision)
            decision = cast(
                RoutingDecision,
                routing_llm.invoke(
                    [
                        HumanMessage(
                            content=self.cfg.routing_prompt.format(
                                status=result.status,
                                summary=result.summary,
                                errors=result.errors,
                            )
                        )
                    ],
                ),
            )
            logger.info(f"Routing decision: {decision.next_node} — {decision.reason}")
            return decision
        except Exception as e:
            logger.warning(f"Structured routing failed, using fallback: {e}")
            return self._fallback_routing(result)

    def _fallback_routing(
        self, result: RetrievalResult | ValidatorResult
    ) -> RoutingDecision:
        """Rule-based fallback routing if LLM routing fails."""
        if result.status == "complete":
            return RoutingDecision(
                next_node="end",
                reason="Agent completed successfully.",
            )
        return RoutingDecision(
            next_node="end",
            reason=f"Agent failed: {result.errors}",
        )

    def _make_retrieval_node(self):
        """Runs the retrieval agent and writes structured results to GraphState."""
        agent = retrieval_agent_app(self.llm_model, self.workspace)

        def retrieval_node(state: GraphState) -> dict:
            logger.info("Running retrieval agent...")
            result = agent.invoke({"messages": state["messages"]})
            messages = self._current_turn_messages(state, result)
            retrieval_result = self._parse_retrieval_result(messages)

            bronze_dir = self.workspace / "output" / "bronze"
            bronze_files = [str(f) for f in bronze_dir.glob("*.csv")]

            logger.info(
                f"Retrieval status: {retrieval_result.status}— bronze files: {bronze_files}"
            )
            return {
                "messages": messages,
                "retrieved_data": retrieval_result.model_dump(),
                "bronze_layer": bronze_files,
                "errors": retrieval_result.errors,
            }

        return retrieval_node

    def _make_validator_node(self):
        """Runs the validator agent once per bronze layer file and writes structured results to GraphState."""
        agent = validation_agent_app(self.llm_model, self.workspace)

        def validator_node(state: GraphState) -> dict:
            logger.info("Running validation agent...")
            bronze_files = state.get("bronze_layer", [])

            if not bronze_files:
                logger.warning("No bronze layer files to validate")
                empty_result = ValidatorResult(
                    status="failed",
                    validation_outcome="FAIL",
                    errors=["No bronze layer files found."],
                    summary="No files to validate.",
                )
                return {
                    "validated_data": empty_result.model_dump(),
                    "silver_layer": [],
                    "errors": empty_result.errors,
                }

            silver_dir = self.workspace / "output" / "silver"
            all_errors = []
            silver_files = []
            per_file_results = []
            all_messages = []

            for idx, file_path in enumerate(bronze_files, start=1):
                logger.info(f"Validating: {file_path}")

                file_stem = Path(file_path).stem  # e.g. "sample" from "sample.csv"

                validation_instruction = HumanMessage(
                    content=(
                        f"Validate the file at: {file_path}\n"
                        f"This is the only file you should validate in this call. "
                        f"Use this exact path with read_sample.\n"
                        f"Name your validation script 'validation_{file_stem}.py' "
                        f"(e.g. if validating sample.csv, name it validation_sample.py)."
                    )
                )

                result = agent.invoke({"messages": [validation_instruction]})
                messages = result.get("messages", [])
                all_messages.extend(messages)

                file_result = self._parse_validator_result(messages)
                per_file_results.append(file_result)
                all_errors.extend(file_result.errors)

                if file_result.validation_outcome == "PASS":
                    src_name = Path(file_path).name
                    silver_path = silver_dir / src_name
                    if silver_path.exists():
                        silver_files.append(str(silver_path))

            overall_outcome = (
                "PASS"
                if all(r.validation_outcome == "PASS" for r in per_file_results)
                else "FAIL"
            )

            combined_result = ValidatorResult(
                status="complete",
                validation_outcome=overall_outcome,
                errors=all_errors,
                summary=f"Validated {len(bronze_files)} files — {len(silver_files)} passed.",
            )

            logger.info(
                f"Validation complete — outcome: {overall_outcome} — silver files: {silver_files}"
            )

            return {
                "messages": all_messages,
                "validated_data": combined_result.model_dump(),
                "silver_layer": silver_files,
                "errors": all_errors,
            }

        return validator_node

    def _route_after_retrieval(self, state: GraphState) -> str:
        """Determines next node after retrieval using structured LLM decision."""
        retrieved = state.get("retrieved_data", {})
        result = (
            RetrievalResult(**retrieved)
            if retrieved
            else RetrievalResult(
                status="failed",
                summary="No retrieval data found.",
                errors=["retrieved_data was empty."],
            )
        )
        decision = self._decide_routing(result)
        return decision.next_node

    def _route_after_validation(self, state: GraphState) -> str:
        """Determines next node after validation using structured LLM decision."""
        validated = state.get("validated_data", {})
        result = (
            ValidatorResult(**validated)
            if validated
            else ValidatorResult(
                status="failed",
                validation_outcome="FAIL",
                errors=["validated_data was empty."],
                summary="No validation data found.",
            )
        )
        decision = self._decide_routing(result)
        return decision.next_node

    def _build_app(self):
        graph = StateGraph(GraphState)
        graph.add_node("retrieval_agent", self._make_retrieval_node())
        graph.add_node("validation_agent", self._make_validator_node())
        graph.set_entry_point("retrieval_agent")
        graph.add_conditional_edges(
            "retrieval_agent",
            self._route_after_retrieval,
            {
                "validation_agent": "validation_agent" if PHASE >= 2 else END,
                "repair_agent": "repair_agent" if PHASE >= 3 else END,
                "end": END,
            },
        )
        graph.add_conditional_edges(
            "validation_agent",
            self._route_after_validation,
            {
                "repair_agent": "repair_agent" if PHASE >= 3 else END,
                "end": END,
            },
        )
        return graph.compile(checkpointer=MemorySaver(), name="AgentTeam_Main")

    def invoke(self, state: GraphState, thread_id: str = "default") -> dict:
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        return self.app.invoke(state, config=config)

    def stream(self, state: GraphState, thread_id: str = "default"):
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        return self.app.stream(state, config=config, stream_mode="values")
