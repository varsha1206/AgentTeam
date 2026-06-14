"""
Orchestrator agent acts as the supervisor agent and manages the entire workflow of the
data pipeline
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph_supervisor import create_supervisor

from agentteam.agents.retrieval_agent import retrieval_agent
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

    # Sub-agents list
    agents = [
        retrieval_agent,
    ]

    workflow = create_supervisor(
        agents,
        model=llm_model,  # can be None for now in some setups
        state_schema=GraphState,
        prompt="You are a supervisor routing requests to agents.",
        output_mode="full_history",
        add_handoff_back_messages=True,
    )

    app = workflow.compile(
        checkpointer=MemorySaver(),
        name="AgentTeam_Main",
    )

    return app
