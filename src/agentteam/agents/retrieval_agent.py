# src/agentteam/agents/retrieval_agent.py

"""
Retrieval Agent: locates, reads, and surfaces raw data from the workspace.
"""

import logging
import warnings
from pathlib import Path

import hydra
from langchain_core.language_models.chat_models import BaseChatModel
from omegaconf import DictConfig

from agentteam.tools.retrieval_agent.retrieval_tools import RetrievalTools

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from langgraph.prebuilt import create_react_agent

logger = logging.getLogger(__name__)


class RetrievalAgent:
    """
    Agent responsible for locating, reading, and writing data within the workspace.
    Wraps a LangGraph react agent with workspace-scoped tools.
    """

    def __init__(self, llm_model: BaseChatModel, workspace: Path):
        if not workspace.exists():
            raise FileNotFoundError(f"Workspace not found at {workspace}")

        self.workspace = workspace
        self.llm_model = llm_model
        self.cfg: DictConfig = self._load_config()
        self.tools = RetrievalTools(
            input_dir=workspace / "input",
            output_dir=workspace / "output",
        )
        self.app = self._build_app()

    # -----------------------------
    # Config
    # -----------------------------

    def _load_config(self) -> DictConfig:
        with hydra.initialize(version_base=None, config_path="../../../configs"):
            logger.info("Loading retrieval agent config...")
            cfg = hydra.compose(
                config_name="config",
                overrides=["agents/retrieval=default"],
            )
            logger.info("Retrieval agent config loaded successfully")
            return cfg.agents.retrieval

    # -----------------------------
    # App
    # -----------------------------

    def _build_app(self):
        return create_react_agent(
            model=self.llm_model,
            tools=self.tools.as_tools(),
            prompt=self.cfg.system_prompt,
            name="retrieval_agent",
        )


def retrieval_agent_app(llm_model: BaseChatModel, workspace: Path):
    """
    Factory function — returns the compiled Pregel app.
    Kept as a plain function so create_supervisor receives the app directly.
    """
    return RetrievalAgent(llm_model, workspace).app
