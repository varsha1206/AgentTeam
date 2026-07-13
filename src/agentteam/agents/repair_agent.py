"""
Repair Agent: reads failing scripts and error context, generates patched
scripts, executes them, and routes back to the appropriate agent.
"""

import logging
import warnings
from pathlib import Path

import hydra
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage
from omegaconf import DictConfig

from agentteam.tools.repair_agent.repair_tools import RepairTools

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from langgraph.prebuilt import create_react_agent

logger = logging.getLogger(__name__)


class RepairAgent:
    """
    Agent responsible for patching failing pipeline scripts.
    Reads the failing script and error context, generates a patched version,
    and executes it.
    """

    def __init__(self, llm_model: BaseChatModel, workspace: Path):
        if not workspace.exists():
            raise FileNotFoundError(f"Workspace not found at {workspace}")

        self.workspace = workspace
        self.llm_model = llm_model
        self.cfg: DictConfig = self._load_config()
        self.tools = RepairTools(
            generated_dir=workspace / "generated",
            logs_dir=workspace / "logs",
            temp_dir=workspace / "temp",
        )
        self.app = self._build_app()

    def _load_config(self) -> DictConfig:
        with hydra.initialize(version_base=None, config_path="../../../configs"):
            logger.info("Loading repair agent config...")
            cfg = hydra.compose(
                config_name="config",
                overrides=["agents/repair=default"],
            )
            logger.info("Repair agent config loaded successfully")
            return cfg.agents.repair

    def _build_prompt(self) -> SystemMessage:
        prompt = self.cfg.system_prompt.format(
            generated_dir=self.tools.generated_dir,
            temp_dir=self.tools.temp_dir,
            logs_dir=self.tools.logs_dir,
        )
        return SystemMessage(
            content=[
                {"type": "text", "text": prompt, "cache_control": {"type": "ephemeral"}}
            ]
        )

    def _build_app(self):
        return create_react_agent(
            model=self.llm_model,
            tools=self.tools.as_tools(),
            prompt=self._build_prompt(),
            name="repair_agent",
        )


def repair_agent_app(llm_model: BaseChatModel, workspace: Path):
    """Factory function — returns the compiled Pregel app."""
    return RepairAgent(llm_model, workspace).app
