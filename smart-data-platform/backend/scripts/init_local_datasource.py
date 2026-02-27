#!/usr/bin/env python3
"""
Initialize local PostgreSQL datasource metadata.

This script creates a data source record for a local PostgreSQL database
and scans all business tables (excluding system tables) to populate
metadata_tables and metadata_columns.

Usage:
    cd backend
    python scripts/init_local_datasource.py

Examples:
    # Use default configuration (localhost:3102/smart_data)
    python scripts/init_local_datasource.py

    # Include row count statistics
    python scripts/init_local_datasource.py --include-row-count

    # Dry-run mode (preview actions without making changes)
    python scripts/init_local_datasource.py --dry-run --verbose

    # Scan only specific tables matching pattern
    python scripts/init_local_datasource.py --table-filter "dw_.*"

    # Update existing datasource configuration
    python scripts/init_local_datasource.py --force-update

    # Custom connection parameters
    python scripts/init_local_datasource.py \\
        --name "Production DB" \\
        --host prod.db.example.com \\
        --port 5432 \\
        --database mydb
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models.metadata import DataSource, DataSourceStatus, DataSourceType

# Import MetadataEngine directly to avoid loading all services
# The services/__init__.py imports OCRService which needs pytesseract
import importlib.util
def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

_backend_path = Path(__file__).parent.parent

# Load connectors first (needed by metadata_engine)
_load_module("app.connectors.base", str(_backend_path / "app" / "connectors" / "base.py"))
_load_module("app.connectors.database", str(_backend_path / "app" / "connectors" / "database.py"))

# Create a minimal connectors module with get_connector
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass

class _ConnectorsModule:
    """Minimal connectors module for the script."""
    @staticmethod
    def get_connector(source_type, config):
        from app.connectors.database import DatabaseConnector
        from app.models.metadata import DataSourceType
        database_types = {
            DataSourceType.POSTGRESQL,
            DataSourceType.MYSQL,
            DataSourceType.ORACLE,
            DataSourceType.SQLSERVER,
            DataSourceType.SQLITE,
        }
        if source_type in database_types:
            return DatabaseConnector({"type": source_type.value, **config})
        raise ValueError(f"Unsupported data source type: {source_type}")

sys.modules["app.connectors"] = _ConnectorsModule()

# Load metadata engine
MetadataEngine = _load_module(
    "app.services.metadata_engine",
    str(_backend_path / "app" / "services" / "metadata_engine.py")
).MetadataEngine


# Default excluded tables (system schemas and application tables)
DEFAULT_EXCLUDED_PATTERNS = [
    r"information_schema\..*",
    r"pg_catalog\..*",
    r"pg_toast\..*",
]

DEFAULT_EXCLUDED_TABLES = [
    "users",
    "roles",
    "user_roles",
    "audit_logs",
    "data_sources",
    "metadata_tables",
    "metadata_columns",
    "metadata_versions",
    "collect_tasks",
    "collect_executions",
    "etl_pipelines",
    "etl_steps",
    "etl_executions",
    "data_assets",
    "asset_access",
    "alert_rules",
    "alerts",
    "quality_rules",
    "quality_issues",
    "lineage_graph",
    "lineage_relationships",
    "report_definitions",
    "report_executions",
    "standard_fields",
    "standard_mappings",
    "compliance_policies",
    "compliance_checks",
]


@dataclass
class ScriptConfig:
    """Configuration for the datasource initialization script."""

    name: str = "本地 PostgreSQL"
    host: str = "localhost"
    port: int = 3102
    database: str = "smart_data"
    username: str = "postgres"
    password: str = "postgres"
    schema: str | None = None
    include_row_count: bool = False
    table_filter: str | None = None
    exclude_tables: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDED_TABLES))
    exclude_patterns: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDED_PATTERNS))
    dry_run: bool = False
    force_update: bool = False
    verbose: bool = False


@dataclass
class ExecutionSummary:
    """Summary of script execution."""

    datasource_created: bool = False
    datasource_updated: bool = False
    datasource_skipped: bool = False
    tables_scanned: int = 0
    columns_scanned: int = 0
    tables_excluded: int = 0
    duration_ms: int = 0
    errors: list[str] = field(default_factory=list)

    def has_changes(self) -> bool:
        """Check if any changes were made."""
        return self.datasource_created or self.datasource_updated


def parse_args() -> ScriptConfig:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Initialize local PostgreSQL datasource metadata.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--name",
        type=str,
        default="本地 PostgreSQL",
        help="Datasource name (default: '本地 PostgreSQL')",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Database host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=3102,
        help="Database port (default: 3102)",
    )
    parser.add_argument(
        "--database",
        type=str,
        default="smart_data",
        help="Database name (default: smart_data)",
    )
    parser.add_argument(
        "--username",
        type=str,
        default="postgres",
        help="Database username (default: postgres)",
    )
    parser.add_argument(
        "--password",
        type=str,
        default="postgres",
        help="Database password (default: postgres)",
    )
    parser.add_argument(
        "--schema",
        type=str,
        default=None,
        help="Schema to scan (default: all non-system schemas)",
    )
    parser.add_argument(
        "--include-row-count",
        action="store_true",
        help="Include row count statistics (slower for large tables)",
    )
    parser.add_argument(
        "--table-filter",
        type=str,
        default=None,
        help="Regex pattern to filter table names (e.g., 'dw_.*' for data warehouse tables)",
    )
    parser.add_argument(
        "--exclude-tables",
        type=str,
        default=None,
        help="Comma-separated list of tables to exclude",
    )
    parser.add_argument(
        "--exclude-patterns",
        type=str,
        default=None,
        help="Comma-separated list of regex patterns to exclude tables",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without making changes",
    )
    parser.add_argument(
        "--force-update",
        action="store_true",
        help="Update existing datasource configuration",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    # Build excluded tables list
    excluded_tables = list(DEFAULT_EXCLUDED_TABLES)
    if args.exclude_tables:
        excluded_tables.extend([t.strip() for t in args.exclude_tables.split(",")])

    # Build excluded patterns list
    excluded_patterns = list(DEFAULT_EXCLUDED_PATTERNS)
    if args.exclude_patterns:
        excluded_patterns.extend([p.strip() for p in args.exclude_patterns.split(",")])

    return ScriptConfig(
        name=args.name,
        host=args.host,
        port=args.port,
        database=args.database,
        username=args.username,
        password=args.password,
        schema=args.schema,
        include_row_count=args.include_row_count,
        table_filter=args.table_filter,
        exclude_tables=excluded_tables,
        exclude_patterns=excluded_patterns,
        dry_run=args.dry_run,
        force_update=args.force_update,
        verbose=args.verbose,
    )


def log_verbose(config: ScriptConfig, message: str) -> None:
    """Log message if verbose mode is enabled."""
    if config.verbose:
        print(f"    [DEBUG] {message}")


def log_info(message: str) -> None:
    """Log info message."""
    print(f"    {message}")


def log_error(message: str) -> None:
    """Log error message."""
    print(f"    [ERROR] {message}", file=sys.stderr)


async def test_connection(config: ScriptConfig) -> tuple[bool, str]:
    """Test database connection."""
    from sqlalchemy import create_engine, text

    url = (
        f"postgresql+psycopg2://"
        f"{config.username}:{config.password}@"
        f"{config.host}:{config.port}/{config.database}"
    )

    engine = None
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Connection successful"
    except Exception as e:
        return False, str(e)
    finally:
        if engine:
            engine.dispose()


async def get_or_create_datasource(
    session: AsyncSession,
    config: ScriptConfig,
) -> tuple[DataSource, ExecutionSummary]:
    """Get or create datasource record."""
    summary = ExecutionSummary()

    # Check if datasource exists
    result = await session.execute(
        select(DataSource).where(DataSource.name == config.name)
    )
    existing = result.scalar_one_or_none()

    connection_config: dict[str, Any] = {
        "host": config.host,
        "port": config.port,
        "database": config.database,
        "username": config.username,
        "password": config.password,
    }

    if config.schema:
        connection_config["schema"] = config.schema

    if existing:
        log_verbose(config, f"Found existing datasource: {existing.id}")
        if config.force_update:
            existing.connection_config = connection_config
            existing.status = DataSourceStatus.INACTIVE
            summary.datasource_updated = True
            log_info(f"Updated datasource configuration: {existing.id}")
        else:
            summary.datasource_skipped = True
            log_info(f"Using existing datasource: {existing.id}")
        return existing, summary

    # Create new datasource
    datasource = DataSource(
        name=config.name,
        type=DataSourceType.POSTGRESQL,
        connection_config=connection_config,
        status=DataSourceStatus.INACTIVE,
    )
    session.add(datasource)
    await session.flush()

    summary.datasource_created = True
    log_info(f"Created new datasource: {datasource.id}")

    return datasource, summary


async def scan_metadata(
    session: AsyncSession,
    datasource: DataSource,
    config: ScriptConfig,
) -> ExecutionSummary:
    """Scan metadata from datasource."""
    from app.models.metadata import MetadataColumn, MetadataTable
    from sqlalchemy import create_engine, inspect, text
    from sqlalchemy.exc import SQLAlchemyError

    summary = ExecutionSummary()

    # Create SQLAlchemy engine for synchronous operations
    url = (
        f"postgresql+psycopg2://"
        f"{config.username}:{config.password}@"
        f"{config.host}:{config.port}/{config.database}"
    )

    sync_engine = None
    try:
        sync_engine = create_engine(url, pool_pre_ping=True)
        inspector = inspect(sync_engine)

        # Get all tables
        log_verbose(config, "Fetching table list from database...")
        tables = []

        schemas = [config.schema] if config.schema else inspector.get_schema_names()

        for schema in schemas:
            if schema in ("information_schema", "pg_catalog", "pg_toast"):
                continue

            try:
                for table_name in inspector.get_table_names(schema=schema):
                    tables.append({
                        "schema_name": schema if schema != "public" else None,
                        "table_name": table_name,
                        "table_type": "table",
                    })

                for view_name in inspector.get_view_names(schema=schema):
                    tables.append({
                        "schema_name": schema if schema != "public" else None,
                        "table_name": view_name,
                        "table_type": "view",
                    })
            except Exception:
                # Skip schemas we can't access
                continue

        log_verbose(config, f"Found {len(tables)} total tables/views")

        # Filter out excluded tables
        filtered_tables = []
        for table in tables:
            full_name = f"{table.get('schema_name')}.{table['table_name']}" if table.get('schema_name') else table['table_name']

            # Check against excluded patterns
            excluded = False
            for pattern in config.exclude_patterns:
                if re.match(pattern, full_name):
                    log_verbose(config, f"Excluded by pattern '{pattern}': {full_name}")
                    excluded = True
                    summary.tables_excluded += 1
                    break

            if excluded:
                continue

            # Check against excluded table names
            if table['table_name'] in config.exclude_tables:
                log_verbose(config, f"Excluded by name: {full_name}")
                summary.tables_excluded += 1
                continue

            # Apply table filter if specified
            if config.table_filter:
                if not re.match(config.table_filter, table['table_name']):
                    log_verbose(config, f"Filtered out by --table-filter: {full_name}")
                    summary.tables_excluded += 1
                    continue

            filtered_tables.append(table)

        log_verbose(config, f"After filtering: {len(filtered_tables)} tables to scan")

        if config.dry_run:
            log_info(f"[DRY-RUN] Would scan {len(filtered_tables)} tables:")
            for table in filtered_tables[:10]:  # Show first 10
                schema_prefix = f"{table.get('schema_name')}." if table.get('schema_name') else ""
                log_info(f"  - {schema_prefix}{table['table_name']}")
            if len(filtered_tables) > 10:
                log_info(f"  ... and {len(filtered_tables) - 10} more")
            return summary

        # Scan each table
        tables_scanned = 0
        columns_scanned = 0
        metadata_engine = MetadataEngine(session)

        for table in filtered_tables:
            schema_name = table.get('schema_name')
            table_name = table['table_name']
            full_name = f"{schema_name}.{table_name}" if schema_name else table_name

            try:
                # Get columns
                columns_data = inspector.get_columns(table_name, schema=schema_name)
                pk_constraint = inspector.get_pk_constraint(table_name, schema=schema_name)
                pk_columns = set(pk_constraint.get("constrained_columns", []))

                columns = []
                for idx, col in enumerate(columns_data):
                    columns.append({
                        "column_name": col["name"],
                        "data_type": str(col["type"]),
                        "nullable": col.get("nullable", True),
                        "is_primary_key": col["name"] in pk_columns,
                        "default_value": str(col.get("default")) if col.get("default") else None,
                        "ordinal_position": idx,
                    })
                columns_scanned += len(columns)

                # Get row count if requested
                row_count = None
                if config.include_row_count:
                    try:
                        with sync_engine.connect() as conn:
                            if schema_name:
                                sql = f'SELECT COUNT(*) FROM "{schema_name}"."{table_name}"'
                            else:
                                sql = f"SELECT COUNT(*) FROM {table_name}"
                            result = conn.execute(text(sql))
                            row_count = result.scalar() or 0
                    except Exception as e:
                        log_verbose(config, f"Could not get row count for {full_name}: {e}")

                # Check if table exists
                result = await session.execute(
                    select(MetadataTable).where(
                        MetadataTable.source_id == datasource.id,
                        MetadataTable.table_name == table_name,
                        MetadataTable.schema_name == schema_name,
                    )
                )
                metadata_table = result.scalar_one_or_none()

                if metadata_table:
                    # Update existing table
                    await metadata_engine._create_version_snapshot(metadata_table)
                    metadata_table.row_count = row_count
                    metadata_table.version += 1
                    log_verbose(config, f"Updated table: {full_name} (v{metadata_table.version})")
                else:
                    # Create new table
                    metadata_table = MetadataTable(
                        source_id=datasource.id,
                        schema_name=schema_name,
                        table_name=table_name,
                        row_count=row_count,
                    )
                    session.add(metadata_table)
                    await session.flush()
                    log_verbose(config, f"Created table: {full_name}")

                # Sync columns
                await metadata_engine._sync_columns(metadata_table, columns)
                tables_scanned += 1

            except Exception as e:
                error_msg = f"Failed to scan table {full_name}: {e}"
                log_error(error_msg)
                summary.errors.append(error_msg)

        await session.commit()

        summary.tables_scanned = tables_scanned
        summary.columns_scanned = columns_scanned

        return summary

    except Exception as e:
        await session.rollback()
        summary.errors.append(str(e))
        raise RuntimeError(f"Metadata scan failed: {e}") from e
    finally:
        if sync_engine:
            sync_engine.dispose()


def print_summary(config: ScriptConfig, summary: ExecutionSummary) -> None:
    """Print execution summary."""
    print()
    print("=" * 60)
    print("执行摘要 (Execution Summary)")
    print("=" * 60)

    status_icons = []
    if summary.datasource_created:
        status_icons.append("✅ 新建数据源")
    elif summary.datasource_updated:
        status_icons.append("🔄 更新数据源")
    elif summary.datasource_skipped:
        status_icons.append("⏭️  使用现有数据源")

    if config.dry_run:
        status_icons.append("👁️  预演模式 (无实际修改)")

    for icon in status_icons:
        print(f"  {icon}")

    print()
    print(f"  扫描表数: {summary.tables_scanned}")
    print(f"  扫描列数: {summary.columns_scanned}")
    print(f"  排除表数: {summary.tables_excluded}")
    print(f"  耗时: {summary.duration_ms} ms")

    if summary.errors:
        print()
        print(f"  ⚠️  错误数: {len(summary.errors)}")
        for error in summary.errors[:5]:  # Show first 5 errors
            print(f"    - {error}")
        if len(summary.errors) > 5:
            print(f"    ... and {len(summary.errors) - 5} more")

    print("=" * 60)


async def main() -> None:
    """Main entry point."""
    config = parse_args()
    start_time = datetime.now()

    print()
    print("=" * 60)
    print("数据源初始化脚本 (Datasource Initialization)")
    print("=" * 60)
    print(f"  数据源: {config.name}")
    print(f"  连接: {config.host}:{config.port}/{config.database}")
    print(f"  时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    # Test connection
    print("步骤 1/4: 测试数据库连接")
    print("-" * 60)
    success, message = await test_connection(config)
    if not success:
        log_error(f"Connection failed: {message}")
        print()
        print("❌ 无法连接到数据库，请检查连接参数。")
        sys.exit(1)
    log_info(f"连接成功: {message}")
    print()

    # Create async session
    app_settings = get_settings()
    engine = create_async_engine(
        app_settings.DATABASE_URL,
        echo=False,
    )
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    summary = ExecutionSummary()

    async with async_session() as session:
        # Get or create datasource
        print("步骤 2/4: 获取或创建数据源")
        print("-" * 60)
        datasource, ds_summary = await get_or_create_datasource(session, config)
        summary.datasource_created = ds_summary.datasource_created
        summary.datasource_updated = ds_summary.datasource_updated
        summary.datasource_skipped = ds_summary.datasource_skipped

        if config.dry_run and not summary.datasource_skipped:
            log_info(f"[DRY-RUN] Would create datasource: {config.name}")
        elif not config.dry_run:
            await session.commit()
        print()

        # Scan metadata
        print("步骤 3/4: 扫描元数据")
        print("-" * 60)

        if config.dry_run:
            log_info("预演模式: 不会实际修改数据库")

        try:
            scan_summary = await scan_metadata(session, datasource, config)
            summary.tables_scanned = scan_summary.tables_scanned
            summary.columns_scanned = scan_summary.columns_scanned
            summary.tables_excluded = scan_summary.tables_excluded
            summary.errors.extend(scan_summary.errors)
        except Exception as e:
            log_error(str(e))
            await engine.dispose()
            sys.exit(1)
        print()

        # List scanned tables
        if config.verbose and summary.tables_scanned > 0:
            print("步骤 4/4: 验证扫描结果")
            print("-" * 60)
            from app.models.metadata import MetadataTable

            result = await session.execute(
                select(MetadataTable)
                .where(MetadataTable.source_id == datasource.id)
                .order_by(MetadataTable.table_name)
            )
            tables = result.scalars().all()

            log_info(f"数据库中的表记录 ({len(tables)}):")
            for table in tables[:20]:  # Show first 20
                schema_prefix = f"{table.schema_name}." if table.schema_name else ""
                row_count_str = f" ({table.row_count} rows)" if table.row_count else ""
                log_info(f"  - {schema_prefix}{table.table_name}{row_count_str}")
            if len(tables) > 20:
                log_info(f"  ... and {len(tables) - 20} more")
            print()

    # Calculate duration
    duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
    summary.duration_ms = duration_ms

    # Print summary
    print_summary(config, summary)

    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n操作已取消。")
        sys.exit(1)
