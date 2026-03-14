"""
IDE Management Service Package

Provides VS Code Server and terminal management for online IDE functionality.
"""

from .vscode_manager import (
    IDEType,
    VSCodeStatus,
    VSCodeServerConfig,
    VSCodeServerInstance,
    VSCodeManager,
    get_vscode_manager,
)

from .terminal import (
    TerminalStatus,
    TerminalSession,
    TerminalMessage,
    TerminalManager,
    get_terminal_manager,
)

__all__ = [
    # VS Code Manager
    "IDEType",
    "VSCodeStatus",
    "VSCodeServerConfig",
    "VSCodeServerInstance",
    "VSCodeManager",
    "get_vscode_manager",
    # Terminal Manager
    "TerminalStatus",
    "TerminalSession",
    "TerminalMessage",
    "TerminalManager",
    "get_terminal_manager",
]
