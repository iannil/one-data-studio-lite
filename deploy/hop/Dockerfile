# ONE-DATA-STUDIO-LITE - Apache Hop 容器镜像
# Apache Hop: Kettle(PDI) 的开源替代方案
# 参考: https://hop.apache.org/

FROM apache/hop-web:2.8.0

LABEL maintainer="ONE-DATA-STUDIO-LITE"
LABEL description="Apache Hop ETL 引擎 - Kettle 开源替代"

USER root

# 安装额外的 JDBC 驱动
RUN mkdir -p /usr/local/tomcat/lib && \
    # MySQL JDBC 驱动
    curl -fsSL "https://repo1.maven.org/maven2/com/mysql/mysql-connector-j/8.3.0/mysql-connector-j-8.3.0.jar" \
      -o /usr/local/tomcat/lib/mysql-connector-j-8.3.0.jar && \
    # PostgreSQL JDBC 驱动
    curl -fsSL "https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.1/postgresql-42.7.1.jar" \
      -o /usr/local/tomcat/lib/postgresql-42.7.1.jar && \
    # ClickHouse JDBC 驱动
    curl -fsSL "https://repo1.maven.org/maven2/com/clickhouse/clickhouse-jdbc/0.6.0/clickhouse-jdbc-0.6.0-all.jar" \
      -o /usr/local/tomcat/lib/clickhouse-jdbc-0.6.0.jar

# 环境变量
ENV HOP_LOG_LEVEL=Basic

USER hop

EXPOSE 8080

# hop-web uses Tomcat, no custom CMD needed
