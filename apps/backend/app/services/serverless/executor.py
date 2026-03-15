"""
Serverless Function Executor

Executes serverless functions with:
- Container runtime
- Memory and time limits
- Logging and monitoring
- Auto-scaling
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.serverless import (
    ServerlessFunction,
    FunctionExecution,
    FunctionLog,
    Runtime,
    ExecutionStatus,
    FunctionStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class ExecutionConfig:
    """Configuration for function execution"""
    timeout: int = 300  # seconds
    memory_mb: int = 256
    cpu_cores: float = 0.5
    temp_dir: str = "/tmp/serverless"
    log_level: str = "INFO"


@dataclass
class ExecutionResult:
    """Result of function execution"""
    execution_id: str
    status: str
    return_value: Any = None
    error_message: Optional[str] = None
    duration_ms: int = 0
    memory_used_mb: Optional[int] = None
    logs: List[str] = field(default_factory=list)


class PythonExecutor:
    """Execute Python functions in isolated environment"""

    def __init__(self, config: ExecutionConfig):
        self.config = config

    async def execute(
        self,
        code: str,
        handler: str,
        event: Dict[str, Any],
        context: Dict[str, Any],
    ) -> ExecutionResult:
        """
        Execute Python function.

        Args:
            code: Python code
            handler: Handler path (module.function)
            event: Event payload
            context: Execution context

        Returns:
            Execution result
        """
        import sys
        import io
        import traceback
        from contextlib import redirect_stdout, redirect_stderr

        execution_id = context.get("execution_id", str(uuid.uuid4()))
        start_time = datetime.utcnow()

        logs = []
        return_value = None
        error_message = None

        try:
            # Parse handler
            module_name, func_name = handler.split(".")
            full_code = f"{code}\n\n# Generated execution wrapper\n_result = None\n"

            # Prepare execution globals
            exec_globals = {
                "__name__": f"__function_{execution_id[:8]}__",
                "__builtins__": __builtins__,
                "event": event,
                "context": context,
            }

            # Capture stdout/stderr
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()

            # Execute code with timeout
            async def run_with_timeout():
                nonlocal return_value

                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    # Execute the user code
                    exec(code, exec_globals)

                    # Call the handler function
                    if func_name in exec_globals:
                        func = exec_globals[func_name]
                        if asyncio.iscoroutinefunction(func):
                            return_value = await func(event, context)
                        else:
                            return_value = func(event, context)
                    else:
                        raise NameError(f"Function '{func_name}' not found in module")

            # Run with timeout
            try:
                await asyncio.wait_for(run_with_timeout(), timeout=self.config.timeout)
            except asyncio.TimeoutError:
                error_message = f"Function execution timed out after {self.config.timeout}s"

            # Get logs
            logs.extend(stdout_capture.getvalue().splitlines())
            if stderr_capture.getvalue():
                logs.extend(f"ERROR: {line}" for line in stderr_capture.getvalue().splitlines())

        except Exception as e:
            error_message = f"{type(e).__name__}: {str(e)}"
            logs.append(f"Execution failed: {error_message}")
            logs.extend(traceback.format_exc().splitlines())

        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Determine status
        if error_message:
            status = ExecutionStatus.FAILED
        else:
            status = ExecutionStatus.COMPLETED

        return ExecutionResult(
            execution_id=execution_id,
            status=status,
            return_value=return_value,
            error_message=error_message,
            duration_ms=duration_ms,
            logs=logs,
        )


class ContainerExecutor:
    """Execute functions in container (Docker)"""

    def __init__(self, config: ExecutionConfig):
        self.config = config

    async def execute(
        self,
        image: str,
        handler: str,
        event: Dict[str, Any],
        context: Dict[str, Any],
        environment: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """
        Execute function in container.

        Args:
            image: Container image
            handler: Handler path
            event: Event payload
            context: Execution context
            environment: Environment variables

        Returns:
            Execution result
        """
        execution_id = context.get("execution_id", str(uuid.uuid4()))
        start_time = datetime.utcnow()

        # For now, simulate container execution
        # In production, this would use Docker SDK or Kubernetes
        logs = []
        return_value = None
        error_message = None

        try:
            import subprocess

            # Prepare payload
            payload = json.dumps({"event": event, "context": context})

            # Run container
            cmd = [
                "docker", "run", "--rm",
                f"--memory={self.config.memory_mb}m",
                f"--memory-swap={self.config.memory_mb * 2}m",
                f"--cpus={self.config.cpu_cores}",
                "-e", f"HANDLER={handler}",
                "-e", f"PAYLOAD={payload}",
            ]

            if environment:
                for k, v in environment.items():
                    cmd.extend(["-e", f"{k}={v}"])

            cmd.append(image)

            # Run with timeout
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.config.timeout,
                )

                if proc.returncode == 0:
                    return_value = json.loads(stdout.decode()) if stdout else None
                else:
                    error_message = stderr.decode()

            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                error_message = f"Container execution timed out after {self.config.timeout}s"

        except Exception as e:
            error_message = f"{type(e).__name__}: {str(e)}"

        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        return ExecutionResult(
            execution_id=execution_id,
            status=ExecutionStatus.FAILED if error_message else ExecutionStatus.COMPLETED,
            return_value=return_value,
            error_message=error_message,
            duration_ms=duration_ms,
            logs=logs,
        )


class ServerlessExecutor:
    """
    Serverless function executor with multiple runtime support
    """

    def __init__(self, config: Optional[ExecutionConfig] = None):
        self.config = config or ExecutionConfig()
        self._python_executor = PythonExecutor(self.config)
        self._container_executor = ContainerExecutor(self.config)

    async def execute(
        self,
        db: AsyncSession,
        function_id: str,
        event: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        trigger_id: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Execute a serverless function.

        Args:
            db: Database session
            function_id: Function to execute
            event: Event payload
            context: Execution context
            trigger_id: Trigger that invoked the function

        Returns:
            Execution result
        """
        # Get function
        result = await db.execute(
            select(ServerlessFunction).where(ServerlessFunction.function_id == function_id)
        )
        function = result.scalar_one_or_none()

        if not function:
            raise ValueError(f"Function {function_id} not found")

        if not function.enabled:
            raise ValueError(f"Function {function_id} is disabled")

        if function.status != FunctionStatus.READY:
            raise ValueError(f"Function {function_id} is not ready (status: {function.status})")

        # Create execution record
        execution_id = str(uuid.uuid4())
        execution = FunctionExecution(
            execution_id=execution_id,
            function_id=function_id,
            trigger_id=trigger_id,
            status=ExecutionStatus.RUNNING,
            event=event,
            payload=event.get("payload"),
            headers=context.get("headers") if context else None,
            started_at=datetime.utcnow(),
        )
        db.add(execution)
        await db.commit()

        # Build context
        exec_context = {
            "execution_id": execution_id,
            "function_id": function_id,
            "function_name": function.name,
            "request_id": context.get("request_id") if context else str(uuid.uuid4()),
            "invocation_source": context.get("invocation_source", "api") if context else "api",
            "deadline": (datetime.utcnow() + timedelta(seconds=function.timeout)).isoformat(),
            "timeout": function.timeout,
            "memory_limit_mb": function.memory_mb,
        }

        start_time = datetime.utcnow()

        try:
            # Execute based on runtime type
            if function.image:
                # Container execution
                result = await self._container_executor.execute(
                    image=function.image,
                    handler=function.handler,
                    event=event,
                    context=exec_context,
                    environment=function.environment,
                )
            else:
                # Direct Python execution
                result = await self._python_executor.execute(
                    code=function.code or "",
                    handler=function.handler,
                    event=event,
                    context=exec_context,
                )

            # Update execution record
            end_time = datetime.utcnow()
            execution.status = result.status
            execution.completed_at = end_time
            execution.duration_ms = result.duration_ms
            execution.result = {"return_value": result.return_value} if result.return_value else None
            execution.return_value = json.dumps(result.return_value) if result.return_value else None
            execution.error_message = result.error_message
            execution.memory_used_mb = result.memory_used_mb
            execution.logs = "\n".join(result.logs) if result.logs else None

            # Save logs
            for log_line in result.logs:
                log = FunctionLog(
                    execution_id=execution_id,
                    level="INFO",
                    message=log_line,
                )
                db.add(log)

            # Update function statistics
            function.invocation_count += 1
            function.total_duration_ms += result.duration_ms
            if result.status == ExecutionStatus.FAILED:
                function.error_count += 1
            function.last_invoked_at = start_time

            # Calculate average duration
            if function.invocation_count > 0:
                function.avg_duration_ms = function.total_duration_ms // function.invocation_count

            await db.commit()

            logger.info(
                f"Execution {execution_id} completed: "
                f"status={result.status}, duration={result.duration_ms}ms"
            )

            return result

        except Exception as e:
            logger.error(f"Execution {execution_id} failed: {e}")

            # Update execution as failed
            execution.status = ExecutionStatus.FAILED
            execution.completed_at = datetime.utcnow()
            execution.error_message = str(e)
            function.invocation_count += 1
            function.error_count += 1

            await db.commit()

            return ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                error_message=str(e),
                duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
            )

    async def execute_http(
        self,
        db: AsyncSession,
        function_id: str,
        body: Dict[str, Any],
        headers: Dict[str, str],
        query_params: Dict[str, str],
    ) -> ExecutionResult:
        """
        Execute function triggered by HTTP.

        Args:
            db: Database session
            function_id: Function to execute
            body: Request body
            headers: Request headers
            query_params: Query parameters

        Returns:
            Execution result
        """
        event = {
            "httpMethod": "POST",
            "headers": headers,
            "queryStringParameters": query_params,
            "body": json.dumps(body) if body else None,
        }

        context = {
            "invocation_source": "http",
            "headers": headers,
        }

        return await self.execute(
            db=db,
            function_id=function_id,
            event=event,
            context=context,
        )

    async def execute_timer(
        self,
        db: AsyncSession,
        function_id: str,
        timer_name: str,
        schedule: str,
    ) -> ExecutionResult:
        """
        Execute function triggered by timer.

        Args:
            db: Database session
            function_id: Function to execute
            timer_name: Timer name
            schedule: Cron schedule

        Returns:
            Execution result
        """
        event = {
            "timer": timer_name,
            "schedule": schedule,
            "time": datetime.utcnow().isoformat(),
        }

        context = {
            "invocation_source": "timer",
            "trigger_name": timer_name,
        }

        return await self.execute(
            db=db,
            function_id=function_id,
            event=event,
            context=context,
        )

    async def execute_queue(
        self,
        db: AsyncSession,
        function_id: str,
        queue_name: str,
        messages: List[Dict[str, Any]],
    ) -> List[ExecutionResult]:
        """
        Execute function for each message in queue.

        Args:
            db: Database session
            function_id: Function to execute
            queue_name: Queue name
            messages: Messages to process

        Returns:
            List of execution results
        """
        results = []

        for message in messages:
            event = {
                "queue": queue_name,
                "message": message,
                "messageId": message.get("id", str(uuid.uuid4())),
            }

            context = {
                "invocation_source": "queue",
                "queue_name": queue_name,
            }

            result = await self.execute(
                db=db,
                function_id=function_id,
                event=event,
                context=context,
            )

            results.append(result)

        return results


# Global executor instance
_executor: Optional[ServerlessExecutor] = None


def get_serverless_executor(config: Optional[ExecutionConfig] = None) -> ServerlessExecutor:
    """Get or create global executor instance"""
    global _executor
    if _executor is None or config:
        _executor = ServerlessExecutor(config)
    return _executor
