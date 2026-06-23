"""
Orchestrator: manages the entire workflow of the data pipeline.
Uses a custom StateGraph for full control over state transitions.
"""

import logging
from pathlib import Path

import hydra
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from omegaconf import DictConfig

from agentteam.agents.retrieval_agent import retrieval_agent_app
from agentteam.graph.state import GraphState
from agentteam.models.structured_outputs import RetrievalResult, RoutingDecision

logger = logging.getLogger(__name__)

PHASE = 1


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
        return last_ai.content if last_ai else ""

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
            result: RetrievalResult = extraction_llm.invoke(
                [
                    HumanMessage(
                        content=(
                            f"Extract the retrieval result from the following agent output.\n\n"
                            f"Agent summary:\n{summary}\n\n"
                            f"Tool outputs:\n{chr(10).join(tool_outputs)}\n\n"
                            f"Extract: status, summary, script_path, output_path, errors."
                        )
                    )
                ]
            )
            return result
        except Exception as e:
            logger.warning(f"Structured extraction failed, using fallback: {e}")
            return self._fallback_parse(summary, tool_outputs)

    def _fallback_parse(self, summary: str, tool_outputs: list[str]) -> RetrievalResult:
        """Rule-based fallback extraction if LLM parsing fails."""
        script_path = self._extract_path_from_outputs(tool_outputs, "generated", ".py")
        output_path = self._extract_path_from_outputs(tool_outputs, "output", ".csv")
        status = "complete" if output_path else "failed"
        return RetrievalResult(
            status=status,
            summary=summary,
            script_path=script_path,
            output_path=output_path,
            errors=[] if status == "complete" else ["No output CSV produced."],
        )

    def _decide_routing(self, result: RetrievalResult) -> RoutingDecision:
        """Uses structured LLM output to decide the next node."""
        try:
            routing_llm = self._build_structured_llm(RoutingDecision)
            decision: RoutingDecision = routing_llm.invoke(
                [
                    HumanMessage(
                        content=self.cfg.routing_prompt.format(
                            status=result.status,
                            summary=result.summary,
                            errors=result.errors,
                        )
                    )
                ]
            )
            logger.info(f"Routing decision: {decision.next_node} — {decision.reason}")
            return decision
        except Exception as e:
            logger.warning(f"Structured routing failed, using fallback: {e}")
            return self._fallback_routing(result)

    def _fallback_routing(self, result: RetrievalResult) -> RoutingDecision:
        """Rule-based fallback routing if LLM routing fails."""
        if result.status == "complete":
            return RoutingDecision(
                next_node="end",
                reason="Retrieval completed successfully.",
            )
        return RoutingDecision(
            next_node="end",
            reason=f"Retrieval failed: {result.errors}",
        )

    def _make_retrieval_node(self):
        """Runs the retrieval agent and writes structured results to GraphState."""
        agent = retrieval_agent_app(self.llm_model, self.workspace)

        def retrieval_node(state: GraphState) -> dict:
            logger.info("Running retrieval agent...")
            result = agent.invoke({"messages": state["messages"]})
            messages = result.get("messages", [])
            retrieval_result = self._parse_retrieval_result(messages)
            logger.info(f"Retrieval status: {retrieval_result.status}")
            return {
                "messages": messages,
                "retrieved_data": retrieval_result.model_dump(),
                "errors": retrieval_result.errors,
            }

        return retrieval_node

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

    def _build_app(self):
        graph = StateGraph(GraphState)
        graph.add_node("retrieval_agent", self._make_retrieval_node())
        graph.set_entry_point("retrieval_agent")
        graph.add_conditional_edges(
            "retrieval_agent",
            self._route_after_retrieval,
            {
                "validator_agent": "validator_agent" if PHASE >= 2 else END,
                "repair_agent": "repair_agent" if PHASE >= 3 else END,
                "end": END,
            },
        )
        return graph.compile(checkpointer=MemorySaver(), name="AgentTeam_Main")

    def invoke(self, state: dict, thread_id: str = "default") -> dict:
        config = {"configurable": {"thread_id": thread_id}}
        return self.app.invoke(state, config=config)

    def stream(self, state: dict, thread_id: str = "default"):
        config = {"configurable": {"thread_id": thread_id}}
        return self.app.stream(state, config=config, stream_mode="values")
