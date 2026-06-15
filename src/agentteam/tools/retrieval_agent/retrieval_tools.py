# src/agentteam/tools/retrieval_agent/retrieval_tools.py

"""
Tools for the Retrieval Agent.
Responsible for file discovery, reading, and writing within the workspace.
"""

import logging
import subprocess
from pathlib import Path

import pandas as pd
from langchain.tools import tool

from agentteam.models.structured_outputs import GeneratedScript

logger = logging.getLogger(__name__)


class RetrievalTools:
    """
    Tool suite for the Retrieval Agent.
    All tools operate within the provided workspace directories.
    """

    def __init__(self, input_dir: Path, output_dir: Path, generated_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.generated_dir = generated_dir
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
        out_path.write_text(content, encoding="utf-8")
        logger.info(f"Written to {out_path}")
        return f"Written to {out_path}"

    # Code Generation
    def write_script(self, script: GeneratedScript) -> str:
        """Save a GeneratedScript to workspace/generated/."""
        script_path = self.generated_dir / script.filename
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(script.code, encoding="utf-8")
        logger.info(f"Script written: {script_path} — {script.description}")
        return str(script_path)

    def execute_script(self, script_path: str) -> str:
        """
        Execute a Python script via subprocess.
        Returns stdout on success, stderr on failure.
        """
        path = Path(script_path)
        if not path.exists():
            return f"ERROR: Script not found at {path}"
        try:
            result = subprocess.run(
                ["python", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
            )
            if result.returncode != 0:
                logger.error(f"Script failed: {result.stderr}")
                return f"ERROR (exit {result.returncode}):\n{result.stderr}"
            logger.info(f"Script executed successfully: {path}")
            return result.stdout or "Script completed with no output."
        except subprocess.TimeoutExpired:
            return "ERROR: Script timed out after 30 seconds"
        except Exception as e:
            return f"ERROR: {e}"

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

        @tool
        def write_script(filename: str, code: str, description: str) -> str:
            """
            Save a generated Python script to the generated directory.
            Args:
                filename: e.g. 'retrieval_001.py'
                code: the complete Python script as a plain string, no markdown
                description: one sentence describing what the script does
            """
            from agentteam.models.structured_outputs import GeneratedScript

            return _self.write_script(
                GeneratedScript(
                    filename=filename,
                    code=code,
                    description=description,
                )
            )

        @tool
        def execute_script(script_path: str) -> str:
            """
            Execute a Python script and return its output.
            Args:
                script_path: absolute path returned by write_script
            """
            return _self.execute_script(script_path)

        return [list_input_files, read_csv, write_output, write_script, execute_script]
