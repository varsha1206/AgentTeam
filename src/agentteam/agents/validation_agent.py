# src/agentteam/agents/validator_agent.py

"""
Validator Agent: inspects retrieval output, infers schema, generates and
executes a validation script, and reports structured errors into GraphState.
"""

import logging
import warnings
from pathlib import Path

import hydra
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage
from omegaconf import DictConfig

from agentteam.tools.validation_agent.validator_tools import ValidatorTools

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from langgraph.prebuilt import create_react_agent

logger = logging.getLogger(__name__)


class ValidationAgent:
    """
    Agent responsible for validating data produced by the Retrieval Agent.
    Infers schema from data, generates a validation script, executes it,
    and writes a structured report into the workspace.
    """

    def __init__(self, llm_model: BaseChatModel, workspace: Path):
        if not workspace.exists():
            raise FileNotFoundError(f"Workspace not found at {workspace}")

        self.workspace = workspace
        self.llm_model = llm_model
        self.cfg: DictConfig = self._load_config()
        self.tools = ValidatorTools(
            bronze_dir=workspace / "output/bronze",
            silver_dir=workspace / "output/silver",
            generated_dir=workspace / "generated",
            logs_dir=workspace / "logs",
        )
        self.app = self._build_app()

    def _load_config(self) -> DictConfig:
        with hydra.initialize(version_base=None, config_path="../../../configs"):
            logger.info("Loading validation agent config...")
            cfg = hydra.compose(
                config_name="config",
                overrides=["agents/validation=default"],
            )
            logger.info("Validation agent config loaded successfully")
            return cfg.agents.validation

    def _build_prompt(self) -> SystemMessage:
        prompt = self.cfg.system_prompt.format(
            generated_dir=self.tools.generated_dir,
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
            name="validation_agent",
        )


def validation_agent_app(llm_model: BaseChatModel, workspace: Path):
    """Factory function — returns the compiled Pregel app."""
    return ValidationAgent(llm_model, workspace).app
