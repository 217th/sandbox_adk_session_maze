"""Maze agent package implementing the ADK session demo."""

import logging

from .agent_handler import AgentHandler
from .engine import MazeEngine
from .session_manager import SessionManager

__all__ = ["AgentHandler", "MazeEngine", "SessionManager"]


def configure_logging() -> None:
    """Ensure maze_agent loggers write to console."""
    logger = logging.getLogger("maze_agent")
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[MazeAgent] %(levelname)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


configure_logging()
