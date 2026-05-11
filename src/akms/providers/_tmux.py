"""Per-pane activity logging for CLI-subprocess providers.

Configure `tmux_pane: <name>` in your provider's config block to write agent
I/O to ~/.akms/panes/<name>.log.  Watch it live in any terminal or tmux pane:

    tail -f ~/.akms/panes/<name>.log
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_LOG_DIR = Path.home() / ".akms" / "panes"


def pane_log_path(target: str) -> Path:
    """Return the log file path for the given pane target name."""
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", target)
    return _LOG_DIR / f"{safe}.log"


def write_to_pane(target: str, text: str) -> None:
    """Append a line to the pane log file. OSErrors are swallowed."""
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(pane_log_path(target), "a") as fh:
            fh.write(text + "\n")
    except OSError as exc:
        logger.debug("pane log write failed for %r: %s", target, exc)
