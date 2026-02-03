#!/bin/bash
# PostgreSQL 初始化脚本
# 创建 Superset 和 DolphinScheduler 数据库

set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    -- Superset 数据库
    CREATE DATABASE superset;
    CREATE USER superset WITH PASSWORD 'superset123';
    GRANT ALL PRIVILEGES ON DATABASE superset TO superset;

    -- DolphinScheduler 数据库
    CREATE DATABASE dolphinscheduler;
    CREATE USER dolphinscheduler WITH PASSWORD 'ds2024';
    GRANT ALL PRIVILEGES ON DATABASE dolphinscheduler TO dolphinscheduler;
EOSQL
