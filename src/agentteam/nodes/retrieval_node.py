"""Retrieval agent node and router."""

import logging

from langchain_core.messages import HumanMessage

from agentteam.agents.retrieval_agent import retrieval_agent_app
from agentteam.graph.state import GraphState
from agentteam.models.structured_outputs import (
    DataSource,
    ErrorReport,
    RetrievalResult,
    RoutingDecision,
)
from agentteam.utils.base_node import BaseAgentNode, BaseRouter
from agentteam.utils.result_parser import parse_retrieval_result
from agentteam.utils.routing_utils import decide_routing

logger = logging.getLogger(__name__)


class RetrievalNode(BaseAgentNode):
    def get_agent(self):
        return retrieval_agent_app(self.llm_model, self.workspace)

    def build_instructions(self, state: GraphState) -> list[HumanMessage]:
        input_files = list((self.workspace / "input").glob("*.csv"))
        return [
            self._build_agent_instruction(
                task="full_pipeline",
                source=DataSource(
                    source_type="csv",
                    path=str(f),
                    output_filename=f.name,
                ),
            )
            for f in input_files
        ]

    def parse_result(self, messages: list) -> RetrievalResult:
        return parse_retrieval_result(
            messages, self._build_structured_llm(RetrievalResult)
        )

    def update_state(self, state: GraphState, results: list[RetrievalResult]) -> dict:
        bronze_files = [
            str(f) for f in (self.workspace / "output" / "bronze").glob("*.csv")
        ]
        errors = [e for r in results for e in r.errors]
        last = (
            results[-1]
            if results
            else RetrievalResult(status="failed", summary="No results.", errors=errors)
        )
        return {
            "retrieved_data": last.model_dump(),
            "bronze_layer": bronze_files,
            "errors": errors,
        }

    def as_node(self):
        """Override to add repair detection after each file retrieval."""
        agent = self.get_agent()

        def node(state: GraphState) -> dict:
            logger.info("Running retrieval agent...")
            input_files = list((self.workspace / "input").glob("*.csv"))
            all_messages = []
            all_results = []
            repair_target = None
            repair_error = None
            repair_script_path = None

            for input_file in input_files:
                instruction = self._build_agent_instruction(
                    task="full_pipeline",
                    source=DataSource(
                        source_type="csv",
                        path=str(input_file),
                        output_filename=input_file.name,
                    ),
                )
                messages = self._invoke_agent(agent, instruction)
                all_messages.extend(messages)
                all_results.append(self.parse_result(messages))

                if repair_target is None:
                    repair_target, repair_error, repair_script_path = (
                        self._detect_repair_needed(messages, str(input_file))
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


class RetrievalRouter(BaseRouter):
    def get_result(self, state: GraphState) -> RetrievalResult:
        retrieved = state.get("retrieved_data", {})
        return (
            RetrievalResult(**retrieved)
            if retrieved
            else RetrievalResult(
                status="failed",
                summary="No retrieval data found.",
                errors=[
                    ErrorReport(
                        error="retrieved_data was empty.",
                        stage="retrieval",
                        error_type=None,
                        should_repair=True,
                    )
                ],
            )
        )

    def route(self, state: GraphState) -> str:
        if state.get("repair_target") == "retrieval":
            logger.info("Routing to repair_agent — retrieval script crashed")
            return "repair_agent"
        result = self.get_result(state)
        return decide_routing(
            result,
            self._build_structured_llm(RoutingDecision),
            self.routing_prompt,
        ).next_node
