# src/agentteam/agents/retrieval_agent.py

"""
Retrieval Agent: locates, reads, and surfaces raw data from the workspace.
"""

import logging
import warnings
from pathlib import Path

import hydra
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage
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
            bronze_dir=workspace / "output" / "bronze",
            generated_dir=workspace / "generated",
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

    def _build_prompt(self) -> SystemMessage:
        prompt = self.cfg.system_prompt.format(
            input_dir=self.tools.input_dir,
            output_dir=self.tools.bronze_dir,
            generated_dir=self.tools.generated_dir,
        )
        return SystemMessage(
            content=[
                {"type": "text", "text": prompt, "cache_control": {"type": "ephemeral"}}
            ]
        )

    # -----------------------------
    # App
    # -----------------------------

    def _build_app(self):
        return create_react_agent(
            model=self.llm_model,
            tools=self.tools.as_tools(),
            prompt=self._build_prompt(),
            name="retrieval_agent",
        )


def retrieval_agent_app(llm_model: BaseChatModel, workspace: Path):
    """
    Factory function — returns the compiled Pregel app.
    Kept as a plain function so create_supervisor receives the app directly.
    """
    return RetrievalAgent(llm_model, workspace).app
