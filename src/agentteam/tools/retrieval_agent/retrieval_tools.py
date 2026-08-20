# src/agentteam/tools/retrieval_agent/retrieval_tools.py

"""
Tools for the Retrieval Agent.
Responsible for file discovery, reading, and writing within the workspace.
"""

import json
import logging
import subprocess
from pathlib import Path

import pandas as pd
from langchain.tools import tool

from agentteam.evaluation.test_injection import get_injection
from agentteam.models.structured_outputs import GeneratedScript

logger = logging.getLogger(__name__)


class RetrievalTools:
    """
    Tool suite for the Retrieval Agent.
    All tools operate within the provided workspace directories.
    """

    def __init__(
        self,
        input_dir: Path,
        bronze_dir: Path,
        generated_dir: Path,
        staged_input_dir: Path,
    ):
        self.input_dir = input_dir
        self.bronze_dir = bronze_dir
        self.generated_dir = generated_dir
        self.staged_input_dir = staged_input_dir
        self.workspace_path = input_dir.parent
        self._validate_dirs()

    # -----------------------------
    # Validation
    # -----------------------------

    def _validate_dirs(self) -> None:
        if not self.input_dir.exists():
            raise FileNotFoundError(f"Input directory not found at {self.input_dir}")
        if not self.bronze_dir.exists():
            raise FileNotFoundError(f"Bronze directory not found at {self.bronze_dir}")
        if not self.staged_input_dir.exists():
            raise FileNotFoundError(
                f"Staged input directory not found at {self.staged_input_dir}"
            )

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

    def read_json(self, file_path: str) -> str:
        """
        Read a JSON file and return its contents as a string.
        Args:
            file_path: absolute path as returned by list_input_files
        """
        path = Path(file_path)
        if not path.exists():
            return f"ERROR: File not found at {path}"
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"Read {path} — {len(data)} top-level keys")
            return json.dumps(data, indent=2)
        except Exception as e:
            return f"ERROR reading {path}: {e}"

    def _read_csv(self, path: Path) -> pd.DataFrame:
        """Read a CSV file."""
        return pd.read_csv(path)

    def _read_json(self, path: Path) -> pd.DataFrame:
        """Read a JSON file."""
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        return pd.json_normalize(data)

    def standardize_bronze_files_to_csv(self) -> str:
        """
        Convert every supported file in the bronze directory into CSV format.

        Supported:
        - .csv
        - .json

        Output:
            workspace/staged_input/<original_name>.csv
        """

        self.staged_input_dir.mkdir(parents=True, exist_ok=True)

        readers = {
            ".csv": self._read_csv,
            ".json": self._read_json,
        }

        for file_path in self.bronze_dir.iterdir():
            if not file_path.is_file():
                continue

            reader = readers.get(file_path.suffix.lower())

            if reader is None:
                logger.warning("Skipping unsupported file: %s", file_path.name)
                continue

            try:
                df = reader(file_path)

                output_path = self.staged_input_dir / f"{file_path.stem}.csv"
                df.to_csv(output_path, index=False)

                logger.info(
                    "Standardized %s -> %s",
                    file_path.name,
                    output_path.name,
                )

            except Exception as e:
                logger.exception(
                    "Failed to standardize %s: %s",
                    file_path.name,
                    e,
                )
        return f"Standardized files written to {self.staged_input_dir}"

    def write_output(self, filename: str, content: str) -> str:
        """
        Write content to the outputs directory.
        Args:
            filename: filename only, e.g. 'result.csv'
            content: string content to write
        """
        out_path = self.bronze_dir / filename
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        logger.info(f"Written to {out_path}")
        return f"Written to {out_path}"

    def _get_test_failure_type(self, filename: str) -> str | None:
        """
        Checks the evaluation harness's injection marker for this script.
        Applies only during controlled evaluation runs — never reads
        validation_rules.yaml, so it cannot be confused with user-defined
        pipeline configuration.
        """
        stem = filename.replace("retrieval_", "")
        if ".py" in stem:
            stem = stem.replace(".py", "")
        if ".csv" not in stem:
            stem += ".csv"
        print(
            f"Checking for test failure injection for {stem} in {self.workspace_path}"
        )

        return get_injection(self.workspace_path, stem)

    def _corrupt_script(self, code: str, failure_type: str) -> str:
        if failure_type == "syntax_error":
            return "this is not valid python!!!\n" + code

        lines = code.split("\n")
        insert_at = 0
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                insert_at = i + 1

        if failure_type == "import_error":
            lines.insert(insert_at, "import this_module_does_not_exist_xyz123")
            return "\n".join(lines)

        if failure_type == "runtime_type_error":
            lines.insert(
                insert_at,
                "_INJECTED_TEST_VAR = {'a': 1}['__nonexistent_key_for_test_injection__']",
            )
            return "\n".join(lines)

        return code

    # Code Generation
    def write_script(self, script: GeneratedScript) -> str:
        """Save a GeneratedScript to workspace/generated/."""
        script_path = self.generated_dir / script.filename
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(script.code, encoding="utf-8")
        logger.info(f"Script written: {script_path} — {script.description}")

        # call site — unchanged shape, new source
        failure_type = self._get_test_failure_type(script.filename)
        if failure_type:
            corrupted = self._corrupt_script(script.code, failure_type)
            script_path.write_text(corrupted, encoding="utf-8")
            logger.debug(f"Test error injected into {script.filename}: {failure_type}")
        return str(script_path)

    def execute_script(self, script_path: str) -> str:
        """Execute a retrieval script and return its output."""
        path = Path(script_path)

        if not path.exists():
            return json.dumps(
                {
                    "SCRIPT_FAILED": True,
                    "stage": "retrieval",
                    "error": f"Script not found at {script_path}",
                    "script_path": script_path,
                }
            )

        try:
            result = subprocess.run(
                ["python", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
            )

            if result.returncode != 0:
                logger.error(f"Retrieval script failed: {path} — {result.stderr[:200]}")
                return json.dumps(
                    {
                        "SCRIPT_FAILED": True,
                        "stage": "retrieval",
                        "error": result.stderr,
                        "script_path": str(path),
                    }
                )

            output = result.stdout.strip()
            logger.info(f"Script executed successfully: {path}")

            try:
                json.loads(output)
                return f"SCRIPT_SUCCESS:\n{output}"
            except json.JSONDecodeError:
                return json.dumps(
                    {
                        "SCRIPT_FAILED": True,
                        "stage": "retrieval",
                        "error": f"Script ran but did not print valid JSON. Raw output: {output[:300]}",
                        "script_path": str(path),
                    }
                )

        except subprocess.TimeoutExpired:
            return json.dumps(
                {
                    "SCRIPT_FAILED": True,
                    "stage": "retrieval",
                    "error": "Script timed out after 30 seconds",
                    "script_path": str(path),
                }
            )
        except Exception as e:
            return json.dumps(
                {
                    "SCRIPT_FAILED": True,
                    "stage": "retrieval",
                    "error": str(e),
                    "script_path": str(path),
                }
            )

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
        def standardize_bronze_files_to_csv() -> str:
            """
            Convert every supported file in the bronze directory into CSV format.
            Supported: .csv, .json
            Output: workspace/staged_input/<original_name>.csv
            """
            return _self.standardize_bronze_files_to_csv()

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

        return [
            list_input_files,
            read_csv,
            write_output,
            write_script,
            execute_script,
            standardize_bronze_files_to_csv,
        ]
