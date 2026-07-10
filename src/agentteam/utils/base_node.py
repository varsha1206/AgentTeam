"""
Base class for all agent nodes in the orchestrator.
Provides standard patterns for agent invocation, result parsing, and routing.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

from agentteam.graph.state import GraphState
from agentteam.models.structured_outputs import AgentInstruction, RoutingDecision
from agentteam.utils.routing_utils import decide_routing

logger = logging.getLogger(__name__)


class BaseAgentNode(ABC):
    """
    Base class for all orchestrator agent nodes.
    Subclasses implement build_instruction, parse_result, and update_state.
    The orchestrator calls as_node() to get the callable node function.
    """

    def __init__(self, llm_model: BaseChatModel, workspace: Path):
        self.llm_model = llm_model
        self.workspace = workspace

    def _build_structured_llm(self, schema):
        """Returns an LLM bound to a specific structured output schema."""
        return self.llm_model.with_structured_output(schema)

    def _build_agent_instruction(self, **kwargs) -> HumanMessage:
        """Builds a typed AgentInstruction and serialises it as a HumanMessage."""
        instruction = AgentInstruction(**kwargs)
        return HumanMessage(content=instruction.model_dump_json(indent=2))

    def _invoke_agent(self, agent, instruction: HumanMessage) -> list:
        """Invokes an agent with a single instruction and returns its messages."""
        result = agent.invoke({"messages": [instruction]})
        return result.get("messages", [])

    @abstractmethod
    def build_instructions(self, state: GraphState) -> list[HumanMessage]:
        """
        Build the list of AgentInstructions for this invocation.
        One instruction per file or task unit.
        """
        ...

    @abstractmethod
    def parse_result(self, messages: list) -> Any:
        """
        Parse agent messages into a structured result model.
        Returns a Pydantic model (RetrievalResult, ValidatorResult, etc.)
        """
        ...

    @abstractmethod
    def update_state(self, state: GraphState, results: list) -> dict:
        """
        Build the GraphState update dict from a list of parsed results.
        """
        ...

    @abstractmethod
    def get_agent(self):
        """Return the compiled Pregel agent app for this node."""
        ...

    def as_node(self):
        """
        Returns a callable node function for use in StateGraph.
        This is what the orchestrator registers via graph.add_node().
        """
        agent = self.get_agent()

        def node(state: GraphState) -> dict:
            instructions = self.build_instructions(state)
            all_messages = []
            all_results = []

            for instruction in instructions:
                messages = self._invoke_agent(agent, instruction)
                all_messages.extend(messages)
                result = self.parse_result(messages)
                all_results.append(result)

            return self.update_state(state, all_results) | {"messages": all_messages}

        return node


class BaseRouter(ABC):
    """
    Base class for all routing decisions in the orchestrator.
    Subclasses implement get_result and next_node_map.
    """

    def __init__(self, llm_model: BaseChatModel, routing_prompt: str):
        self.llm_model = llm_model
        self.routing_prompt = routing_prompt

    def _build_structured_llm(self, schema):
        return self.llm_model.with_structured_output(schema)

    @abstractmethod
    def get_result(self, state: GraphState) -> Any:
        """Extract the relevant result from state to base the routing decision on."""
        ...

    def route(self, state: GraphState) -> str:
        """Called by conditional_edges. Returns the next node name."""
        result = self.get_result(state)
        return decide_routing(
            result,
            self._build_structured_llm(RoutingDecision),
            self.routing_prompt,
        ).next_node
