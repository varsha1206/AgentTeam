"""
Tools for the Repair Agent.
Responsible for reading failing scripts and error context,
generating patched scripts, and executing them.
"""

import json
import logging
import subprocess
from pathlib import Path

from langchain.tools import tool

from agentteam.models.structured_outputs import GeneratedScript

logger = logging.getLogger(__name__)


class RepairTools:
    """
    Tool suite for the Repair Agent.
    All tools operate within the provided workspace directories.
    """

    def __init__(self, generated_dir: Path, logs_dir: Path, temp_dir: Path):
        self.generated_dir = generated_dir
        self.logs_dir = logs_dir
        self.temp_dir = temp_dir
        self._validate_dirs()

    def _validate_dirs(self) -> None:
        for path in [self.generated_dir, self.logs_dir, self.temp_dir]:
            if not path.exists():
                raise FileNotFoundError(f"Required directory not found at {path}")

    def read_script(self, script_path: str) -> str:
        """Read the contents of a script file."""
        path = Path(script_path)
        if not path.exists():
            return f"ERROR: Script not found at {path}"
        return path.read_text(encoding="utf-8")

    def read_transformation_report(self) -> str:
        """Read the latest transformation report from workspace/logs/."""
        report_path = self.logs_dir / "transformation_report.json"
        if not report_path.exists():
            return "ERROR: No transformation report found."
        return report_path.read_text(encoding="utf-8")

    def read_validation_report(self) -> str:
        """Read the latest validation report from workspace/logs/."""
        report_path = self.logs_dir / "validation_report.json"
        if not report_path.exists():
            return "ERROR: No validation report found."
        return report_path.read_text(encoding="utf-8")

    def write_script(self, script: GeneratedScript) -> str:
        """Save a repaired script to workspace/generated/."""
        script_path = self.generated_dir / script.filename
        script_path.write_text(script.code, encoding="utf-8")
        logger.info(f"Repaired script written: {script_path} — {script.description}")
        return str(script_path)

    def execute_script(self, script_path: str) -> str:
        """Execute a repaired script and return its output."""
        path = Path(script_path)
        if not path.exists():
            return "SCRIPT_FAILED: Script not found"
        try:
            result = subprocess.run(
                ["python", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
            )
            if result.returncode != 0:
                logger.error(f"Repaired script failed: {result.stderr}")
                return f"SCRIPT_FAILED (exit {result.returncode}):\n{result.stderr}"

            output = result.stdout.strip()
            logger.info(f"Repaired script executed: {path}")

            try:
                json.loads(output)
                return f"SCRIPT_SUCCESS:\n{output}"
            except json.JSONDecodeError:
                return (
                    f"SCRIPT_FAILED: script did not print valid JSON.\n"
                    f"Raw output: {output[:300]}"
                )

        except subprocess.TimeoutExpired:
            return "SCRIPT_FAILED: timed out after 30 seconds"
        except Exception as e:
            return f"SCRIPT_FAILED: {e}"

    def as_tools(self) -> list:
        _self = self

        @tool
        def read_script(script_path: str) -> str:
            """
            Read the contents of a script file.
            Args:
                script_path: absolute path to the script to read
            """
            return _self.read_script(script_path)

        @tool
        def read_transformation_report() -> str:
            """
            Read the latest transformation report from workspace/logs/.
            Call this to understand what transformations were applied and why rows were quarantined.
            """
            return _self.read_transformation_report()

        @tool
        def read_validation_report() -> str:
            """
            Read the latest validation report from workspace/logs/.
            Call this to understand what validation errors were found.
            """
            return _self.read_validation_report()

        @tool
        def write_script(filename: str, code: str, description: str) -> str:
            """
            Save a repaired Python script to the generated directory.
            Args:
                filename: e.g. 'repair_transformation_employee_data.py'
                code: complete repaired Python script, no markdown, no backticks
                description: one sentence describing what this script fixes
            """
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
            Execute a repaired script and return its output.
            Args:
                script_path: absolute path returned by write_script
            """
            return _self.execute_script(script_path)

        return [
            read_transformation_report,
            read_validation_report,
            read_script,
            write_script,
            execute_script,
        ]
