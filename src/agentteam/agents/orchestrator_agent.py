"""
Orchestrator agent acts as the supervisor agent and manages the entire workflow of the
data pipeline
"""

import logging
import warnings
from pathlib import Path

import hydra
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.memory import MemorySaver
from langgraph_supervisor import create_supervisor

from agentteam.agents.retrieval_agent import retrieval_agent_app
from agentteam.graph.state import GraphState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_app(llm_model: BaseChatModel | None = None, workspace: Path | None = None):
    """
    Builds LangGraph supervisor system
    """

    # Load orchestrator config
    with hydra.initialize(
        version_base=None,
        config_path="../../../configs",
    ):
        logger.info("Loading orchestrator config...")
        cfg = hydra.compose(
            config_name="config",
            overrides=["agents/orchestrator=default"],
        )
        orchestrator_cfg = cfg.agents.orchestrator
        logger.info("Orchestrator config loaded successfully")

    if llm_model is None:
        llm_model = ChatAnthropic(
            model_name="claude-haiku-4-5-20251001",
            timeout=10,
            stop=["end of response"],
        )
    # Sub-agents list
    agents = [retrieval_agent_app(llm_model, workspace)]

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*remaining_steps.*")
        workflow = create_supervisor(
            agents,  # type: ignore
            model=llm_model,
            state_schema=GraphState,
            prompt=orchestrator_cfg.system_prompt,
            add_handoff_back_messages=True,
        )

    app = workflow.compile(
        checkpointer=MemorySaver(),
        name="AgentTeam_Main",
    )

    return app
