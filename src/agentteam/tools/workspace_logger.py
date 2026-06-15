"""
Worksspace logger for structured progress logging in markdown format.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def append_log(
    workspace_path: str,
    agent: str,
    action: str,
    status: str,
    result: str | None = None,
) -> None:
    """
    Append structured progress logs to workspace log file.

    File:
        workspace/logs/execution_log.md
    """

    workspace = Path(workspace_path)

    log_dir = workspace / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "execution_log.md"

    timestamp = datetime.utcnow().isoformat()

    entry = f"""
## [{timestamp}] [{agent}]

**Action**
{action}

**Status**
{status}
"""

    if result:
        entry += f"""

**Result**
{result}
"""

    entry += "\n---\n"

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(entry)
