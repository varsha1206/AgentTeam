# retrieval_agent.py

import logging
import warnings
from pathlib import Path

import hydra
import pandas as pd
from langchain.tools import tool
from langchain_core.language_models.chat_models import BaseChatModel

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from langgraph.prebuilt import create_react_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def retrieval_agent_app(llm_model: BaseChatModel, workspace: Path | None = None):

    if workspace is None:
        workspace = Path.cwd()

    input_dir = workspace / "input"
    output_dir = workspace / "output"
    logger.info(f"Retrieval agent input_dir: {input_dir}")
    logger.info(f"Retrieval agent input_dir exists: {input_dir.exists()}")
    logger.info(f"Retrieval agent output_dir: {output_dir}")
    logger.info(f"Retrieval agent output_dir exists: {output_dir.exists()}")

    def get_configs():
        """
        Load retrieval agent config.
        """
        with hydra.initialize(
            version_base=None,
            config_path="../../../configs",
        ):
            logger.info("Loading retrieval agent config...")
            cfg = hydra.compose(
                config_name="config",
                overrides=["agents/retrieval=default"],
            )
            retrieval_cfg = cfg.agents.retrieval
            logger.info("Retrieval agent config loaded successfully")
            return retrieval_cfg

    @tool
    def list_input_files() -> str:
        """List all files available in the input directory.
            ALWAYS call this first before doing anything else.
        Lists all files in the input directory.
        Do NOT assume the directory is empty or missing without calling this tool."""
        if not input_dir.exists():
            return f"ERROR: input directory not found at {input_dir}"
        files = [f for f in input_dir.rglob("*") if f.is_file()]
        if not files:
            return f"No files found in {input_dir}"
        return "\n".join(str(f) for f in files)

    @tool
    def read_csv(file_path: str) -> str:
        """
        Read a CSV file and return its contents.
        Args:
            file_path: absolute path as returned by list_input_files
        """
        path = Path(file_path)
        if not path.exists():
            return f"ERROR: File not found at {path}"
        try:
            df = pd.read_csv(path)
            logger.info(f"Read {path} — {len(df)} rows, {len(df.columns)} cols")
            return df.to_string(index=False)
        except Exception as e:
            return f"ERROR reading {path}: {e}"

    @tool
    def write_output(filename: str, content: str) -> str:
        """
        Write content to the outputs directory.
        Args:
            filename: filename only, e.g. 'result.csv'
            content: string content to write
        """
        out_path = output_dir / filename
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content)
        return f"Written to {out_path}"

    cfg = get_configs()
    agent = create_react_agent(
        model=llm_model,
        tools=[read_csv, list_input_files, write_output],
        prompt=cfg.system_prompt,
        name="retrieval_agent",
    )

    return agent
