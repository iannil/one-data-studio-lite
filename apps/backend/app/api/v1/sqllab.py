"""
SQLLab API Endpoints

Provides REST API for interactive SQL queries with multi-database support.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.sqllab.query_engine import (
    get_sqllab_service,
    DatabaseType,
    QueryStatus,
    ResultFormat,
    DatabaseConnection,
    QueryResult,
    QueryHistory,
    SavedQuery,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sqllab", tags=["SQLLab"])


# ============================================================================
# Request/Response Models
# ============================================================================


class ConnectionCreateRequest(BaseModel):
    """Request to create a database connection"""
    name: str = Field(..., min_length=1, max_length=100)
    db_type: DatabaseType
    host: str
    port: int
    database: str
    username: Optional[str] = None
    password: Optional[str] = None
    description: Optional[str] = None
    options: Dict[str, Any] = {}


class ConnectionResponse(BaseModel):
    """Database connection response"""
    id: str
    name: str
    db_type: str
    host: str
    port: int
    database: str
    description: Optional[str]
    created_at: str
    is_active: bool


class QueryExecuteRequest(BaseModel):
    """Request to execute a query"""
    connection_id: str
    sql: str
    limit: Optional[int] = Field(1000, ge=1, le=10000)
    offset: Optional[int] = Field(0, ge=0)
    enable_cache: bool = True


class QueryExecuteResponse(BaseModel):
    """Query execution response"""
    query_id: str
    status: str
    rows: List[Dict[str, Any]]
    columns: List[str]
    row_count: int
    execution_time_ms: float
    limit_reached: bool
    cached: bool
    error: Optional[str]


class QueryAnalyzeRequest(BaseModel):
    """Request to analyze a query"""
    sql: str
    db_type: DatabaseType


class SaveQueryRequest(BaseModel):
    """Request to save a query"""
    name: str
    query: str
    connection_id: str
    description: Optional[str] = None
    tags: List[str] = []
    is_public: bool = False


class SaveQueryResponse(BaseModel):
    """Saved query response"""
    id: str
    name: str
    query: str
    connection_id: str
    description: Optional[str]
    tags: List[str]
    is_public: bool
    created_at: str


# ============================================================================
# Connection Endpoints
# ============================================================================


@router.post("/connections", response_model=ConnectionResponse)
async def create_connection(
    data: ConnectionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new database connection"""
    service = get_sqllab_service(db)

    try:
        connection = service.create_connection(
            name=data.name,
            db_type=data.db_type,
            host=data.host,
            port=data.port,
            database=data.database,
            username=data.username,
            password=data.password,
            description=data.description,
            user_id=str(current_user.id),
            **data.options,
        )

        return ConnectionResponse(
            id=connection.id,
            name=connection.name,
            db_type=connection.db_type.value,
            host=connection.host,
            port=connection.port,
            database=connection.database,
            description=connection.description,
            created_at=connection.created_at.isoformat(),
            is_active=connection.is_active,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/connections", response_model=List[ConnectionResponse])
async def list_connections(
    db_type: Optional[DatabaseType] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all database connections"""
    service = get_sqllab_service(db)

    connections = service.list_connections(
        user_id=str(current_user.id),
        db_type=db_type,
    )

    return [
        ConnectionResponse(
            id=conn.id,
            name=conn.name,
            db_type=conn.db_type.value,
            host=conn.host,
            port=conn.port,
            database=conn.database,
            description=conn.description,
            created_at=conn.created_at.isoformat(),
            is_active=conn.is_active,
        )
        for conn in connections
    ]


@router.get("/connections/{connection_id}")
async def get_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a database connection by ID"""
    service = get_sqllab_service(db)
    connection = service.get_connection(connection_id)

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )

    return ConnectionResponse(
        id=connection.id,
        name=connection.name,
        db_type=connection.db_type.value,
        host=connection.host,
        port=connection.port,
        database=connection.database,
        description=connection.description,
        created_at=connection.created_at.isoformat(),
        is_active=connection.is_active,
    )


@router.post("/connections/{connection_id}/test")
async def test_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Test a database connection"""
    service = get_sqllab_service(db)
    connection = service.get_connection(connection_id)

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )

    success, error = service.test_connection(connection)

    return {
        "success": success,
        "error": error,
    }


@router.delete("/connections/{connection_id}")
async def delete_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a database connection"""
    service = get_sqllab_service(db)
    success = service.delete_connection(connection_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )

    return {"success": True}


# ============================================================================
# Query Execution Endpoints
# ============================================================================


@router.post("/queries/execute", response_model=QueryExecuteResponse)
async def execute_query(
    request: QueryExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Execute a SQL query"""
    service = get_sqllab_service(db)

    result = service.execute_query(
        connection_id=request.connection_id,
        sql=request.sql,
        user_id=str(current_user.id),
        limit=request.limit,
        offset=request.offset,
        enable_cache=request.enable_cache,
    )

    return QueryExecuteResponse(
        query_id=result.query_id,
        status=result.status.value,
        rows=result.rows,
        columns=result.columns,
        row_count=result.row_count,
        execution_time_ms=result.execution_time_ms,
        limit_reached=result.limit_reached,
        cached=result.cached,
        error=result.error,
    )


@router.post("/queries/analyze")
async def analyze_query(
    request: QueryAnalyzeRequest,
    current_user: User = Depends(get_current_user),
):
    """Analyze a SQL query without executing it"""
    from app.services.sqllab.query_engine import get_sqllab_service

    service = get_sqllab_service(db)
    analysis = service.analyze_query(request.sql, request.db_type)

    return analysis


@router.get("/queries/history")
async def get_query_history(
    connection_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get query history"""
    service = get_sqllab_service(db)

    history = service.get_query_history(
        user_id=str(current_user.id),
        limit=limit,
        connection_id=connection_id,
    )

    return {
        "history": [
            {
                "id": h.id,
                "query": h.query,
                "connection_id": h.connection_id,
                "status": h.status.value,
                "execution_time_ms": h.execution_time_ms,
                "row_count": h.row_count,
                "executed_at": h.executed_at.isoformat(),
            }
            for h in history
        ]
    }


# ============================================================================
# Saved Queries Endpoints
# ============================================================================


@router.get("/queries/saved", response_model=List[SaveQueryResponse])
async def get_saved_queries(
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get saved queries"""
    service = get_sqllab_service(db)

    queries = service.get_saved_queries(
        user_id=str(current_user.id),
        limit=limit,
    )

    return [
        SaveQueryResponse(
            id=q.id,
            name=q.name,
            query=q.query,
            connection_id=q.connection_id,
            description=q.description,
            tags=q.tags,
            is_public=q.is_public,
            created_at=q.created_at.isoformat(),
        )
        for q in queries
    ]


@router.post("/queries/save", response_model=SaveQueryResponse)
async def save_query(
    request: SaveQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save a query for reuse"""
    service = get_sqllab_service(db)

    query = service.save_query(
        user_id=str(current_user.id),
        name=request.name,
        query=request.query,
        connection_id=request.connection_id,
        description=request.description,
        tags=request.tags,
        is_public=request.is_public,
    )

    return SaveQueryResponse(
        id=query.id,
        name=query.name,
        query=query.query,
        connection_id=query.connection_id,
        description=query.description,
        tags=query.tags,
        is_public=query.is_public,
        created_at=query.created_at.isoformat(),
    )


@router.delete("/queries/saved/{query_id}")
async def delete_saved_query(
    query_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a saved query"""
    service = get_sqllab_service(db)
    success = service.delete_saved_query(query_id, str(current_user.id))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved query not found"
        )

    return {"success": True}


# ============================================================================
# Schema Exploration Endpoints
# ============================================================================


@router.get("/connections/{connection_id}/tables")
async def get_tables(
    connection_id: str,
    database: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get list of tables in the database"""
    service = get_sqllab_service(db)

    tables = service.get_tables(
        connection_id=connection_id,
        database=database,
    )

    return {
        "connection_id": connection_id,
        "tables": tables,
    }


@router.get("/connections/{connection_id}/tables/{table_name}/schema")
async def get_table_schema(
    connection_id: str,
    table_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get table schema"""
    service = get_sqllab_service(db)

    columns = service.get_table_schema(
        connection_id=connection_id,
        table_name=table_name,
    )

    return {
        "table_name": table_name,
        "columns": columns,
    }


@router.get("/connections/{connection_id}/tables/{table_name}/preview")
async def get_table_preview(
    connection_id: str,
    table_name: str,
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get table data preview"""
    service = get_sqllab_service(db)

    result = service.get_table_preview(
        connection_id=connection_id,
        table_name=table_name,
        limit=limit,
    )

    return QueryExecuteResponse(
        query_id=result.query_id,
        status=result.status.value,
        rows=result.rows,
        columns=result.columns,
        row_count=result.row_count,
        execution_time_ms=result.execution_time_ms,
        limit_reached=result.limit_reached,
        cached=result.cached,
        error=result.error,
    )


# ============================================================================
# Cache Management Endpoints
# ============================================================================


@router.post("/cache/invalidate")
async def invalidate_cache(
    connection_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Invalidate query cache"""
    from app.services.sqllab.query_engine import QueryCache

    cache = QueryCache()
    cache.invalidate(connection_id)

    return {
        "success": True,
        "message": "Cache invalidated",
    }
