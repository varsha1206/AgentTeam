# src/agentteam/tools/retrieval_agent/retrieval_tools.py

"""
Tools for the Retrieval Agent.
Responsible for file discovery, reading, and writing within the workspace.
"""

import logging
from pathlib import Path

import pandas as pd
from langchain.tools import tool

logger = logging.getLogger(__name__)


class RetrievalTools:
    """
    Tool suite for the Retrieval Agent.
    All tools operate within the provided workspace directories.
    """

    def __init__(self, input_dir: Path, output_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self._validate_dirs()

    # -----------------------------
    # Validation
    # -----------------------------

    def _validate_dirs(self) -> None:
        if not self.input_dir.exists():
            raise FileNotFoundError(f"Input directory not found at {self.input_dir}")
        if not self.output_dir.exists():
            raise FileNotFoundError(f"Output directory not found at {self.output_dir}")

    # -----------------------------
    # Tools
    # -----------------------------

    def list_input_files(self) -> str:
        """
        ALWAYS call this first before doing anything else.
        Lists all files in the input directory.
        Do NOT assume the directory is empty or missing without calling this tool.
        """
        files = [f for f in self.input_dir.rglob("*") if f.is_file()]
        if not files:
            return f"No files found in {self.input_dir}"
        return "\n".join(str(f) for f in files)

    def read_csv(self, file_path: str) -> str:
        """
        Read a CSV file and return its contents as a string.
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

    def write_output(self, filename: str, content: str) -> str:
        """
        Write content to the outputs directory.
        Args:
            filename: filename only, e.g. 'result.csv'
            content: string content to write
        """
        out_path = self.output_dir / filename
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content)
        logger.info(f"Written to {out_path}")
        return f"Written to {out_path}"

    # -----------------------------
    # LangChain tool bindings
    # -----------------------------

    def as_tools(self) -> list:
        """
        Returns all tools as LangChain-compatible @tool callables,
        bound to this instance's workspace directories.
        """
        _self = self

        @tool
        def list_input_files() -> str:
            """
            ALWAYS call this first before doing anything else.
            Lists all files in the input directory.
            Do NOT assume the directory is empty or missing without calling this tool.
            """
            return _self.list_input_files()

        @tool
        def read_csv(file_path: str) -> str:
            """
            Read a CSV file and return its contents as a string.
            Args:
                file_path: absolute path as returned by list_input_files
            """
            return _self.read_csv(file_path)

        @tool
        def write_output(filename: str, content: str) -> str:
            """
            Write content to the outputs directory.
            Args:
                filename: filename only, e.g. 'result.csv'
                content: string content to write
            """
            return _self.write_output(filename, content)

        return [list_input_files, read_csv, write_output]
