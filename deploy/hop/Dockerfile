# ONE-DATA-STUDIO-LITE - Apache Hop 容器镜像
# Apache Hop: Kettle(PDI) 的开源替代方案
# 参考: https://hop.apache.org/

FROM apache/hop-web:2.8.0

LABEL maintainer="ONE-DATA-STUDIO-LITE"
LABEL description="Apache Hop ETL 引擎 - Kettle 开源替代"

USER root

# 安装额外的 JDBC 驱动
RUN mkdir -p /opt/hop/lib/jdbc && \
    # MySQL JDBC 驱动
    curl -fsSL "https://repo1.maven.org/maven2/com/mysql/mysql-connector-j/8.3.0/mysql-connector-j-8.3.0.jar" \
      -o /opt/hop/lib/jdbc/mysql-connector-j-8.3.0.jar && \
    # PostgreSQL JDBC 驱动
    curl -fsSL "https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.1/postgresql-42.7.1.jar" \
      -o /opt/hop/lib/jdbc/postgresql-42.7.1.jar && \
    # ClickHouse JDBC 驱动
    curl -fsSL "https://repo1.maven.org/maven2/com/clickhouse/clickhouse-jdbc/0.6.0/clickhouse-jdbc-0.6.0-all.jar" \
      -o /opt/hop/lib/jdbc/clickhouse-jdbc-0.6.0.jar

# 复制项目配置
COPY config/ /opt/hop/config/
COPY projects/ /opt/hop/projects/

# 环境变量
ENV HOP_LOG_LEVEL=Basic
ENV HOP_PROJECT_DIRECTORY=/opt/hop/projects
ENV HOP_ENVIRONMENT_DIRECTORY=/opt/hop/config
ENV HOP_SERVER_PORT=8182

USER hop

EXPOSE 8182 8080

CMD ["/opt/hop/hop-server.sh", "/opt/hop/config/hop-server.xml"]
