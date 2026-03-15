"""
Serverless API Endpoints

Provides REST API for serverless function computation:
- Function CRUD
- Trigger management
- Execution management
- Runtime and layer management
"""

import logging
import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.serverless import (
    ServerlessFunction,
    FunctionTrigger,
    FunctionExecution,
    FunctionLog,
    Runtime,
    FunctionLayer,
    FunctionAlias,
    APIEndpoint,
    FunctionStatus,
    ExecutionStatus,
    TriggerType,
)
from app.services.serverless.executor import (
    ServerlessExecutor,
    get_serverless_executor,
    ExecutionResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/serverless", tags=["Serverless"])


# ============================================================================
# Request/Response Schemas
# ============================================================================


class CreateFunctionRequest(BaseModel):
    """Request to create a serverless function"""
    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    runtime: str = "python3.9"
    handler: str = "index.handler"
    code: Optional[str] = None
    code_s3_path: Optional[str] = None
    requirements: Optional[List[str]] = None
    timeout: int = Field(300, ge=1, le=900)
    memory_mb: int = Field(256, ge=128, le=10240)
    environment: Optional[Dict[str, str]] = None
    max_concurrent: int = Field(100, ge=1, le=1000)
    tags: Optional[List[str]] = None


class UpdateFunctionRequest(BaseModel):
    """Request to update a function"""
    name: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None
    timeout: Optional[int] = None
    memory_mb: Optional[int] = None
    environment: Optional[Dict[str, str]] = None
    enabled: Optional[bool] = None
    tags: Optional[List[str]] = None


class CreateTriggerRequest(BaseModel):
    """Request to create a trigger"""
    name: str = Field(..., min_length=1, max_length=256)
    type: str
    config: Dict[str, Any]


class TriggerFunctionRequest(BaseModel):
    """Request to manually trigger a function"""
    event: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None


# ============================================================================
# Function Endpoints
# ============================================================================


@router.post("/functions", response_model=Dict[str, Any])
async def create_function(
    request: CreateFunctionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new serverless function"""
    try:
        import uuid
        function_id = str(uuid.uuid4())

        function = ServerlessFunction(
            function_id=function_id,
            name=request.name,
            description=request.description,
            runtime=request.runtime,
            handler=request.handler,
            code=request.code,
            code_s3_path=request.code_s3_path,
            requirements=request.requirements,
            timeout=request.timeout,
            memory_mb=request.memory_mb,
            environment=request.environment,
            max_concurrent=request.max_concurrent,
            tags=request.tags,
            owner_id=str(current_user.id),
            tenant_id=current_user.tenant_id,
            status=FunctionStatus.READY if request.code else FunctionStatus.BUILDING,
        )

        db.add(function)
        await db.commit()

        return {
            "function_id": function.function_id,
            "name": function.name,
            "runtime": function.runtime,
            "handler": function.handler,
            "status": function.status,
            "created_at": function.created_at.isoformat(),
            "message": "Function created successfully",
        }

    except Exception as e:
        logger.error(f"Failed to create function: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/functions", response_model=List[Dict[str, Any]])
async def list_functions(
    runtime: Optional[str] = None,
    enabled: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List serverless functions"""
    try:
        query = select(ServerlessFunction).where(
            or_(
                ServerlessFunction.owner_id == str(current_user.id),
                ServerlessFunction.tenant_id == current_user.tenant_id,
            )
        )

        if runtime:
            query = query.where(ServerlessFunction.runtime == runtime)
        if enabled is not None:
            query = query.where(ServerlessFunction.enabled == enabled)

        query = query.order_by(ServerlessFunction.updated_at.desc()).limit(limit)

        result = await db.execute(query)
        functions = result.scalars().all()

        return [
            {
                "function_id": f.function_id,
                "name": f.name,
                "description": f.description,
                "runtime": f.runtime,
                "handler": f.handler,
                "timeout": f.timeout,
                "memory_mb": f.memory_mb,
                "status": f.status,
                "enabled": f.enabled,
                "invocation_count": f.invocation_count,
                "error_count": f.error_count,
                "avg_duration_ms": f.avg_duration_ms,
                "tags": f.tags,
                "created_at": f.created_at.isoformat(),
                "updated_at": f.updated_at.isoformat(),
                "last_invoked_at": f.last_invoked_at.isoformat() if f.last_invoked_at else None,
            }
            for f in functions
        ]

    except Exception as e:
        logger.error(f"Failed to list functions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/functions/{function_id}", response_model=Dict[str, Any])
async def get_function(
    function_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get function details"""
    try:
        result = await db.execute(
            select(ServerlessFunction).where(ServerlessFunction.function_id == function_id)
        )
        function = result.scalar_one_or_none()

        if not function:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Function {function_id} not found",
            )

        return {
            "function_id": function.function_id,
            "name": function.name,
            "description": function.description,
            "runtime": function.runtime,
            "runtime_type": function.runtime_type,
            "handler": function.handler,
            "code": function.code,
            "code_s3_path": function.code_s3_path,
            "code_hash": function.code_hash,
            "requirements": function.requirements,
            "timeout": function.timeout,
            "memory_mb": function.memory_mb,
            "ephemeral_storage_mb": function.ephemeral_storage_mb,
            "environment": function.environment,
            "max_concurrent": function.max_concurrent,
            "reserved_concurrent": function.reserved_concurrent,
            "image": function.image,
            "status": function.status,
            "enabled": function.enabled,
            "tags": function.tags,
            "invocation_count": function.invocation_count,
            "error_count": function.error_count,
            "avg_duration_ms": function.avg_duration_ms,
            "created_at": function.created_at.isoformat(),
            "updated_at": function.updated_at.isoformat(),
            "last_invoked_at": function.last_invoked_at.isoformat() if function.last_invoked_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get function: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/functions/{function_id}", response_model=Dict[str, Any])
async def update_function(
    function_id: str,
    request: UpdateFunctionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update function"""
    try:
        result = await db.execute(
            select(ServerlessFunction).where(ServerlessFunction.function_id == function_id)
        )
        function = result.scalar_one_or_none()

        if not function:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Function {function_id} not found",
            )

        # Check ownership
        if function.owner_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the owner can update the function",
            )

        # Update fields
        if request.name is not None:
            function.name = request.name
        if request.description is not None:
            function.description = request.description
        if request.code is not None:
            function.code = request.code
        if request.timeout is not None:
            function.timeout = request.timeout
        if request.memory_mb is not None:
            function.memory_mb = request.memory_mb
        if request.environment is not None:
            function.environment = request.environment
        if request.enabled is not None:
            function.enabled = request.enabled
        if request.tags is not None:
            function.tags = request.tags

        function.updated_at = datetime.utcnow()
        await db.commit()

        return {"message": "Function updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update function: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/functions/{function_id}", response_model=Dict[str, Any])
async def delete_function(
    function_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete function"""
    try:
        result = await db.execute(
            select(ServerlessFunction).where(ServerlessFunction.function_id == function_id)
        )
        function = result.scalar_one_or_none()

        if not function:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Function {function_id} not found",
            )

        # Check ownership
        if function.owner_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the owner can delete the function",
            )

        # Delete related records
        await db.execute(delete(FunctionTrigger).where(FunctionTrigger.function_id == function_id))
        await db.execute(delete(FunctionExecution).where(FunctionExecution.function_id == function_id))
        await db.execute(delete(APIEndpoint).where(APIEndpoint.function_id == function_id))

        # Delete function
        await db.delete(function)
        await db.commit()

        return {"message": "Function deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete function: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Invocation Endpoints
# ============================================================================


@router.post("/functions/{function_id}/invoke", response_model=Dict[str, Any])
async def invoke_function(
    function_id: str,
    request: TriggerFunctionRequest = TriggerFunctionRequest(),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Invoke a function"""
    try:
        executor = get_serverless_executor()

        event = request.event or {}
        if request.payload:
            event["payload"] = request.payload

        # Execute function
        result: ExecutionResult = await executor.execute(
            db=db,
            function_id=function_id,
            event=event,
            context={
                "invocation_source": "api",
                "user_id": str(current_user.id),
            },
        )

        return {
            "execution_id": result.execution_id,
            "status": result.status,
            "return_value": result.return_value,
            "error_message": result.error_message,
            "duration_ms": result.duration_ms,
            "logs": result.logs,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to invoke function: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/functions/{function_id}/executions", response_model=List[Dict[str, Any]])
async def list_executions(
    function_id: str,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List function executions"""
    try:
        query = select(FunctionExecution).where(FunctionExecution.function_id == function_id)

        if status:
            query = query.where(FunctionExecution.status == status)

        query = query.order_by(FunctionExecution.created_at.desc()).limit(limit)

        result = await db.execute(query)
        executions = result.scalars().all()

        return [
            {
                "execution_id": e.execution_id,
                "function_id": e.function_id,
                "trigger_id": e.trigger_id,
                "status": e.status,
                "started_at": e.started_at.isoformat() if e.started_at else None,
                "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                "duration_ms": e.duration_ms,
                "error_message": e.error_message,
                "created_at": e.created_at.isoformat(),
            }
            for e in executions
        ]

    except Exception as e:
        logger.error(f"Failed to list executions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/executions/{execution_id}", response_model=Dict[str, Any])
async def get_execution(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get execution details"""
    try:
        result = await db.execute(
            select(FunctionExecution).where(FunctionExecution.execution_id == execution_id)
        )
        execution = result.scalar_one_or_none()

        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found",
            )

        return {
            "execution_id": execution.execution_id,
            "function_id": execution.function_id,
            "trigger_id": execution.trigger_id,
            "status": execution.status,
            "event": execution.event,
            "payload": execution.payload,
            "headers": execution.headers,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "duration_ms": execution.duration_ms,
            "memory_used_mb": execution.memory_used_mb,
            "cpu_time_ms": execution.cpu_time_ms,
            "result": execution.result,
            "return_value": execution.return_value,
            "logs": execution.logs,
            "error_message": execution.error_message,
            "error_type": execution.error_type,
            "error_stack": execution.error_stack,
            "retry_count": execution.retry_count,
            "created_at": execution.created_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/executions/{execution_id}/logs", response_model=List[Dict[str, Any]])
async def get_execution_logs(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get execution logs"""
    try:
        result = await db.execute(
            select(FunctionLog).where(FunctionLog.execution_id == execution_id)
            .order_by(FunctionLog.timestamp)
        )
        logs = result.scalars().all()

        return [
            {
                "id": str(log.id),
                "execution_id": log.execution_id,
                "level": log.level,
                "message": log.message,
                "timestamp": log.timestamp.isoformat(),
                "source": log.source,
                "extra": log.extra,
            }
            for log in logs
        ]

    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Trigger Endpoints
# ============================================================================


@router.post("/functions/{function_id}/triggers", response_model=Dict[str, Any])
async def create_trigger(
    function_id: str,
    request: CreateTriggerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a trigger for a function"""
    try:
        import uuid
        trigger_id = str(uuid.uuid4())

        trigger = FunctionTrigger(
            trigger_id=trigger_id,
            function_id=function_id,
            name=request.name,
            type=request.type,
            config=request.config,
        )

        db.add(trigger)
        await db.commit()

        return {
            "trigger_id": trigger.trigger_id,
            "name": trigger.name,
            "type": trigger.type,
            "created_at": trigger.created_at.isoformat(),
            "message": "Trigger created successfully",
        }

    except Exception as e:
        logger.error(f"Failed to create trigger: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/functions/{function_id}/triggers", response_model=List[Dict[str, Any]])
async def list_triggers(
    function_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List triggers for a function"""
    try:
        result = await db.execute(
            select(FunctionTrigger).where(FunctionTrigger.function_id == function_id)
        )
        triggers = result.scalars().all()

        return [
            {
                "trigger_id": t.trigger_id,
                "function_id": t.function_id,
                "name": t.name,
                "type": t.type,
                "config": t.config,
                "enabled": t.enabled,
                "trigger_count": t.trigger_count,
                "last_triggered_at": t.last_triggered_at.isoformat() if t.last_triggered_at else None,
                "created_at": t.created_at.isoformat(),
            }
            for t in triggers
        ]

    except Exception as e:
        logger.error(f"Failed to list triggers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/triggers/{trigger_id}", response_model=Dict[str, Any])
async def delete_trigger(
    trigger_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a trigger"""
    try:
        result = await db.execute(
            select(FunctionTrigger).where(FunctionTrigger.trigger_id == trigger_id)
        )
        trigger = result.scalar_one_or_none()

        if not trigger:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trigger {trigger_id} not found",
            )

        await db.delete(trigger)
        await db.commit()

        return {"message": "Trigger deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete trigger: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Runtime Endpoints
# ============================================================================


@router.get("/runtimes", response_model=List[Dict[str, Any]])
async def list_runtimes(
    type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List available runtimes"""
    try:
        query = select(Runtime).where(Runtime.enabled == True)

        if type:
            query = query.where(Runtime.type == type)

        result = await db.execute(query)
        runtimes = result.scalars().all()

        return [
            {
                "runtime_id": r.runtime_id,
                "name": r.name,
                "type": r.type,
                "version": r.version,
                "image": r.image,
                "min_memory_mb": r.min_memory_mb,
                "max_memory_mb": r.max_memory_mb,
                "min_timeout": r.min_timeout,
                "max_timeout": r.max_timeout,
                "function_count": r.function_count,
            }
            for r in runtimes
        ]

    except Exception as e:
        logger.error(f"Failed to list runtimes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
