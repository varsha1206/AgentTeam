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
from langchain_core.messages import SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph_supervisor import create_supervisor
from omegaconf import DictConfig

from agentteam.agents.retrieval_agent import retrieval_agent_app
from agentteam.graph.state import GraphState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Supervisor agent that manages the entire workflow of the data pipeline.
    Responsible for building, configuring, and running the LangGraph supervisor system.
    """

    def __init__(
        self,
        workspace: Path,
        llm_model: BaseChatModel | None = None,
    ):
        if not workspace.exists():
            raise FileNotFoundError(f"Workspace not found at {workspace}")

        self.workspace = workspace
        self.cfg: DictConfig = self._load_config()
        self.llm_model: BaseChatModel = llm_model or self._build_llm()
        self.app = self._build_app()

    # -----------------------------
    # Config
    # -----------------------------

    def _load_config(self) -> DictConfig:
        with hydra.initialize(version_base=None, config_path="../../../configs"):
            logger.info("Loading orchestrator config...")
            cfg = hydra.compose(
                config_name="config",
                overrides=["agents/orchestrator=default"],
            )
            logger.info("Orchestrator config loaded successfully")
            return cfg.agents.orchestrator

    # -----------------------------
    # LLM
    # -----------------------------

    def _build_llm(self) -> BaseChatModel:
        return ChatAnthropic(
            model_name="claude-haiku-4-5-20251001",
            timeout=10,
            stop=["end of response"],
            model_kwargs={
                "extra_headers": {"anthropic-beta": "prompt-caching-2024-07-31"}
            },
        )

    # -----------------------------
    # Agents
    # -----------------------------

    def _build_agents(self) -> list:
        return [
            retrieval_agent_app(self.llm_model, self.workspace),
        ]

    def _build_prompts(self) -> SystemMessage:
        """Build system prompt for the supervisor agent."""
        return SystemMessage(
            content=[
                {
                    "type": "text",
                    "text": self.cfg.system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        )

    # -----------------------------
    # App
    # -----------------------------

    def _build_app(self):
        agents = self._build_agents()

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*remaining_steps.*")
            workflow = create_supervisor(
                agents,  # type: ignore
                model=self.llm_model,
                state_schema=GraphState,
                prompt=self._build_prompts(),
                add_handoff_back_messages=True,
            )

        return workflow.compile(
            checkpointer=MemorySaver(),
            name="AgentTeam_Main",
        )

    # -----------------------------
    # Public interface
    # -----------------------------

    def invoke(self, state: dict, thread_id: str = "default") -> dict:
        config = {"configurable": {"thread_id": thread_id}}
        return self.app.invoke(state, config=config)

    def stream(self, state: dict, thread_id: str = "default"):
        config = {"configurable": {"thread_id": thread_id}}
        return self.app.stream(state, config=config, stream_mode="values")
