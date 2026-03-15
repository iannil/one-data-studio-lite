"""
Terminal Management Service

Manages terminal sessions for online IDE instances.
"""

import logging
import asyncio
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TerminalStatus(str, Enum):
    """Terminal session status"""
    STARTING = "starting"
    RUNNING = "running"
    IDLE = "idle"
    TERMINATED = "terminated"
    ERROR = "error"


@dataclass
class TerminalSession:
    """Terminal session"""
    id: str
    notebook_id: int
    user_id: int
    status: TerminalStatus
    pid: Optional[int] = None
    shell: str = "/bin/bash"

    # Session info
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    terminated_at: Optional[datetime] = None

    # Configuration
    rows: int = 24
    cols: int = 80
    cwd: str = "/home/jovyan"

    # Environment
    env_vars: Dict[str, str] = field(default_factory=dict)


@dataclass
class TerminalMessage:
    """Message from/to terminal"""
    id: str
    session_id: str
    type: str  # input, output, resize, close
    data: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


class TerminalManager:
    """
    Terminal Manager

    Manages terminal sessions for notebook/IDE instances.
    """

    def __init__(self):
        self.sessions: Dict[str, TerminalSession] = {}
        self.session_outputs: Dict[str, List[TerminalMessage]] = {}
        self._max_output_lines = 1000
        self._idle_timeout_minutes = 30

    async def create_session(
        self,
        notebook_id: int,
        user_id: int,
        shell: str = "/bin/bash",
        rows: int = 24,
        cols: int = 80,
        cwd: str = "/home/jovyan",
        env_vars: Optional[Dict[str, str]] = None,
    ) -> TerminalSession:
        """Create a new terminal session"""
        session_id = str(uuid.uuid4())

        # Check if user has too many sessions
        user_sessions = [
            s for s in self.sessions.values()
            if s.user_id == user_id and s.status != TerminalStatus.TERMINATED
        ]
        if len(user_sessions) >= 10:
            raise ValueError("Maximum terminal sessions reached (10)")

        # Create session
        session = TerminalSession(
            id=session_id,
            notebook_id=notebook_id,
            user_id=user_id,
            status=TerminalStatus.STARTING,
            shell=shell,
            rows=rows,
            cols=cols,
            cwd=cwd,
            env_vars=env_vars or {},
        )

        self.sessions[session_id] = session
        self.session_outputs[session_id] = []

        # Start the terminal
        await self._start_terminal(session)

        return session

    async def _start_terminal(self, session: TerminalSession) -> None:
        """Start the terminal process"""
        try:
            # In production, this would spawn a real pty process
            # For now, we'll simulate the startup
            await asyncio.sleep(0.5)

            session.status = TerminalStatus.RUNNING
            session.last_activity = datetime.utcnow()

            # Add welcome message
            self._add_output(
                session.id,
                f"Welcome to terminal session {session.id[:8]}\n",
            )
            self._add_output(
                session.id,
                f"Shell: {session.shell} | Working directory: {session.cwd}\n",
            )
            self._add_output(session.id, f"$ ")

        except Exception as e:
            logger.error(f"Failed to start terminal: {e}")
            session.status = TerminalStatus.ERROR

    def _add_output(self, session_id: str, data: str) -> None:
        """Add output to session buffer"""
        output = TerminalMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            type="output",
            data=data,
        )

        self.session_outputs[session_id].append(output)

        # Trim old output
        if len(self.session_outputs[session_id]) > self._max_output_lines:
            self.session_outputs[session_id] = \
                self.session_outputs[session_id][-self._max_output_lines:]

    async def send_input(
        self,
        session_id: str,
        input_data: str,
    ) -> Tuple[bool, str]:
        """Send input to terminal session"""
        session = self.sessions.get(session_id)
        if not session:
            return False, "Session not found"

        if session.status != TerminalStatus.RUNNING:
            return False, f"Session is not running (status: {session.status})"

        try:
            # Update activity
            session.last_activity = datetime.utcnow()

            # In production, this would write to the pty
            # For now, simulate command execution
            self._add_output(session_id, input_data + "\n")

            # Simulate command response
            if input_data.strip():
                response = await self._simulate_command(session, input_data.strip())
                self._add_output(session_id, response)
                self._add_output(session_id, "$ ")

            return True, "Input sent successfully"

        except Exception as e:
            logger.error(f"Failed to send input: {e}")
            return False, str(e)

    async def _simulate_command(
        self,
        session: TerminalSession,
        command: str,
    ) -> str:
        """Simulate command execution"""
        # Simple command simulation
        if command == "clear":
            self.session_outputs[session.id] = []
            return ""
        elif command == "pwd":
            return session.cwd + "\n"
        elif command == "whoami":
            return "jovyan\n"
        elif command.startswith("echo "):
            return command[5:] + "\n"
        elif command == "date":
            return datetime.utcnow().strftime("%a %b %d %H:%M:%S UTC %Y\n")
        elif command == "ls":
            return "notebooks  data  README.md\n"
        elif command == "help":
            return "Available commands: clear, pwd, whoami, echo, date, ls, help, exit\n"
        elif command == "exit":
            await self.terminate_session(session.id)
            return "Session terminated.\n"
        else:
            return f"Command not found: {command}\n"

    async def resize(
        self,
        session_id: str,
        rows: int,
        cols: int,
    ) -> Tuple[bool, str]:
        """Resize terminal session"""
        session = self.sessions.get(session_id)
        if not session:
            return False, "Session not found"

        if session.status != TerminalStatus.RUNNING:
            return False, f"Session is not running"

        session.rows = rows
        session.cols = cols

        # In production, this would resize the pty
        return True, "Terminal resized"

    async def get_output(
        self,
        session_id: str,
        since: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get output from terminal session"""
        outputs = self.session_outputs.get(session_id, [])

        if since:
            # Filter messages since given message ID
            try:
                since_index = next(
                    i for i, o in enumerate(outputs)
                    if o.id == since
                )
                outputs = outputs[since_index + 1:]
            except StopIteration:
                pass

        return [
            {
                "id": o.id,
                "type": o.type,
                "data": o.data,
                "timestamp": o.timestamp.isoformat(),
            }
            for o in outputs
        ]

    async def terminate_session(
        self,
        session_id: str,
    ) -> Tuple[bool, str]:
        """Terminate a terminal session"""
        session = self.sessions.get(session_id)
        if not session:
            return False, "Session not found"

        try:
            # In production, this would kill the pty process
            if session.pid:
                try:
                    import os
                    os.kill(session.pid, 15)  # SIGTERM
                except ProcessLookupError:
                    pass

            session.status = TerminalStatus.TERMINATED
            session.terminated_at = datetime.utcnow()

            # Add close message
            self._add_output(session_id, "\nSession closed.")

            return True, "Session terminated"

        except Exception as e:
            logger.error(f"Failed to terminate session: {e}")
            return False, str(e)

    async def delete_session(
        self,
        session_id: str,
    ) -> Tuple[bool, str]:
        """Delete a terminal session and its data"""
        # Terminate first
        await self.terminate_session(session_id)

        if session_id in self.sessions:
            del self.sessions[session_id]

        if session_id in self.session_outputs:
            del self.session_outputs[session_id]

        return True, "Session deleted"

    async def get_session(
        self,
        session_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get terminal session info"""
        session = self.sessions.get(session_id)
        if not session:
            return None

        return {
            "id": session.id,
            "notebook_id": session.notebook_id,
            "user_id": session.user_id,
            "status": session.status.value,
            "shell": session.shell,
            "rows": session.rows,
            "cols": session.cols,
            "cwd": session.cwd,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "terminated_at": session.terminated_at.isoformat() if session.terminated_at else None,
        }

    async def list_sessions(
        self,
        user_id: Optional[int] = None,
        notebook_id: Optional[int] = None,
        status: Optional[TerminalStatus] = None,
    ) -> List[Dict[str, Any]]:
        """List terminal sessions"""
        sessions = list(self.sessions.values())

        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]

        if notebook_id:
            sessions = [s for s in sessions if s.notebook_id == notebook_id]

        if status:
            sessions = [s for s in sessions if s.status == status]

        return [
            {
                "id": s.id,
                "notebook_id": s.notebook_id,
                "user_id": s.user_id,
                "status": s.status.value,
                "shell": s.shell,
                "created_at": s.created_at.isoformat(),
                "last_activity": s.last_activity.isoformat(),
            }
            for s in sessions
        ]

    async def cleanup_idle_sessions(self) -> int:
        """Clean up idle terminal sessions"""
        now = datetime.utcnow()
        timeout = timedelta(minutes=self._idle_timeout_minutes)
        cleaned = 0

        for session_id, session in list(self.sessions.items()):
            if session.status == TerminalStatus.RUNNING:
                idle_time = now - session.last_activity
                if idle_time > timeout:
                    await self.terminate_session(session_id)
                    cleaned += 1

        return cleaned

    async def health_check(self) -> Dict[str, Any]:
        """Health check for terminal manager"""
        now = datetime.utcnow()

        active_sessions = [
            s for s in self.sessions.values()
            if s.status == TerminalStatus.RUNNING
        ]

        idle_sessions = [
            s for s in active_sessions
            if (now - s.last_activity).total_seconds() > 300
        ]

        return {
            "total_sessions": len(self.sessions),
            "active_sessions": len(active_sessions),
            "idle_sessions": len(idle_sessions),
            "output_buffers": len(self.session_outputs),
        }


# Global terminal manager instance
_terminal_manager: Optional[TerminalManager] = None


def get_terminal_manager() -> TerminalManager:
    """Get the global terminal manager instance"""
    global _terminal_manager
    if _terminal_manager is None:
        _terminal_manager = TerminalManager()
    return _terminal_manager
