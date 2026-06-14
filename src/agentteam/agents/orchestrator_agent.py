"""
Orchestrator agent acts as the supervisor agent and manages the entire workflow of the
data pipeline
"""

from typing import Sequence

from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import MemorySaver
from langgraph_supervisor import create_supervisor

from agentteam.agents.retrieval_agent import retrieval_agent_app
from agentteam.graph.state import GraphState


# -----------------------------
# Simple routing logic
# -----------------------------
def router(state: GraphState):
    """
    Minimal supervisor logic (non-LLM version first)
    """
    return "retrieval"


def build_app(llm_model=None):
    """
    Builds LangGraph supervisor system
    """
    llm_model = ChatAnthropic(
        model_name="claude-haiku-4-5-20251001",
        timeout=10,
        stop=["end of response"],
    )
    # Sub-agents list
    agents: Sequence = [
        retrieval_agent_app(
            llm_model
        )  # state will be passed in by supervisor at runtime,
    ]

    workflow = create_supervisor(
        agents,  # type: ignore
        model=llm_model,  # can be None for now in some setups
        state_schema=GraphState,
        prompt="You are a supervisor routing requests to agents.Always finish with 'end of response'",
        output_mode="full_history",
        add_handoff_back_messages=True,
    )

    app = workflow.compile(
        checkpointer=MemorySaver(),
        name="AgentTeam_Main",
    )

    return app
