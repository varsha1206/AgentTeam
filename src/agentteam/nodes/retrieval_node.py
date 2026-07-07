"""Retrieval agent node and router."""

from langchain_core.messages import HumanMessage

from agentteam.agents.retrieval_agent import retrieval_agent_app
from agentteam.graph.state import GraphState
from agentteam.models.structured_outputs import DataSource, RetrievalResult
from agentteam.utils.base_node import BaseAgentNode, BaseRouter
from agentteam.utils.result_parser import parse_retrieval_result


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


class RetrievalRouter(BaseRouter):
    def get_result(self, state: GraphState) -> RetrievalResult:
        retrieved = state.get("retrieved_data", {})
        return (
            RetrievalResult(**retrieved)
            if retrieved
            else RetrievalResult(
                status="failed",
                summary="No retrieval data found.",
                errors=["retrieved_data was empty."],
            )
        )
