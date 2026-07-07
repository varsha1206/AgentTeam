"""
Orchestrator: manages the entire workflow of the data pipeline.
"""

import logging
from pathlib import Path

import hydra
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from omegaconf import DictConfig

from agentteam.graph.state import GraphState
from agentteam.nodes.retrieval_node import RetrievalNode, RetrievalRouter
from agentteam.nodes.validation_node import ValidationNode, ValidationRouter

logger = logging.getLogger(__name__)

PHASE = 2


class Orchestrator:
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

    def _build_app(self):
        retrieval = RetrievalNode(self.llm_model, self.workspace)
        validation = ValidationNode(self.llm_model, self.workspace)
        retrieval_router = RetrievalRouter(self.llm_model, self.cfg.routing_prompt)
        validation_router = ValidationRouter(self.llm_model, self.cfg.routing_prompt)

        graph = StateGraph(GraphState)
        graph.add_node("retrieval_agent", retrieval.as_node())
        graph.add_node("validation_agent", validation.as_node())
        graph.set_entry_point("retrieval_agent")
        graph.add_conditional_edges(
            "retrieval_agent",
            retrieval_router.route,
            {
                "validation_agent": "validation_agent" if PHASE >= 2 else END,
                "repair_agent": "repair_agent" if PHASE >= 3 else END,
                "end": END,
            },
        )
        graph.add_conditional_edges(
            "validation_agent",
            validation_router.route,
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
