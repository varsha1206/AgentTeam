"""
Plugin registry: loads, saves, and registers transformation plugins.
Plugins are plain Python functions with the signature:
    fn(df: pd.DataFrame, rule: TransformationRule) -> pd.DataFrame

Plugins are saved to workspace/plugins/ and reused across runs.
The LLM only generates a plugin when one does not already exist.
"""

import importlib.util
import logging
from pathlib import Path

from agentteam.utils.rule_executor import RuleExecutor, TransformationFn

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    Manages transformation plugins in workspace/plugins/.
    Plugins are generated once by the LLM and reused on future runs.
    All plugins are registered into RuleExecutor on load.
    """

    def __init__(self, plugins_dir: Path):
        self.plugins_dir = plugins_dir
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

    # -----------------------------
    # Existence checks
    # -----------------------------

    def exists(self, operation: str) -> bool:
        """Check if a plugin file exists for this operation."""
        return self._plugin_path(operation).exists()

    def is_available(self, operation: str) -> bool:
        """Check if an operation is available — either built-in or as a plugin."""
        return RuleExecutor.is_supported(operation) or self.exists(operation)

    # -----------------------------
    # Save
    # -----------------------------

    def save(self, operation: str, code: str) -> Path:
        """
        Save a generated plugin to workspace/plugins/<operation>.py.
        Automatically loads and registers it after saving.
        """
        path = self._plugin_path(operation)
        path.write_text(code, encoding="utf-8")
        logger.info(f"Plugin saved: {path}")
        self.load(operation)
        return path

    # -----------------------------
    # Load
    # -----------------------------

    def load(self, operation: str) -> bool:
        """
        Load a plugin from disk and register it in RuleExecutor.
        Returns True if successful, False if plugin file not found.
        """
        path = self._plugin_path(operation)
        if not path.exists():
            logger.warning(f"Plugin not found: {path}")
            return False

        try:
            fn = self._import_fn(operation, path)
            RuleExecutor.register(operation, fn)
            logger.info(f"Plugin loaded and registered: {operation}")
            return True
        except Exception as e:
            logger.error(f"Failed to load plugin {operation}: {e}")
            return False

    def load_all(self) -> list[str]:
        """
        Load all plugins from workspace/plugins/ into RuleExecutor.
        Call this at pipeline startup to restore plugins from previous runs.
        Returns list of successfully loaded operation names.
        """
        loaded = []
        for path in self.plugins_dir.glob("*.py"):
            operation = path.stem
            if not RuleExecutor.is_supported(operation):
                if self.load(operation):
                    loaded.append(operation)
        if loaded:
            logger.info(f"Loaded {len(loaded)} plugins: {loaded}")
        return loaded

    # -----------------------------
    # List
    # -----------------------------

    def list_plugins(self) -> list[str]:
        """Return list of all plugin operation names saved to disk."""
        return [p.stem for p in self.plugins_dir.glob("*.py")]

    def list_all_operations(self) -> dict[str, str]:
        """
        Return all available operations with their source.
        Returns {operation_name: 'built_in' | 'plugin'}
        """
        result = {op: "built_in" for op in RuleExecutor.supported_operations()}
        for op in self.list_plugins():
            if op not in result:
                result[op] = "plugin"
        return result

    # -----------------------------
    # Internals
    # -----------------------------

    def _plugin_path(self, operation: str) -> Path:
        return self.plugins_dir / f"{operation}.py"

    def _import_fn(self, operation: str, path: Path) -> TransformationFn:
        """
        Dynamically import a plugin function from a file.
        The function must have the same name as the operation.
        e.g. normalize_phone_numbers.py must define normalize_phone_numbers(df, rule)
        """
        spec = importlib.util.spec_from_file_location(operation, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if not hasattr(module, operation):
            raise AttributeError(
                f"Plugin {path} must define a function named '{operation}'"
            )

        fn = getattr(module, operation)
        if not callable(fn):
            raise TypeError(f"'{operation}' in {path} is not callable")

        return fn
