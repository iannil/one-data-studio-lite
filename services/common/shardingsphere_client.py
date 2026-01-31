"""ShardingSphere JDBC 客户端

通过 JDBC 连接 ShardingSphere Proxy 执行 DistSQL 动态配置脱敏规则。
"""

import logging
from typing import Optional, Any
from contextlib import asynccontextmanager

import aiomysql

logger = logging.getLogger(__name__)


class ShardingSphereClient:
    """ShardingSphere Proxy JDBC 客户端

    通过 DistSQL 动态管理脱敏规则，无需重启服务。

    Example:
        async with ShardingSphereClient(host="localhost", port=3309) as client:
            rules = await client.list_mask_rules()
            await client.add_mask_rule("t_user", "phone", "KEEP_FIRST_N_LAST_M", {...})
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 3309,
        user: str = "root",
        password: str = "",
        database: str = "sharding_db",
    ):
        """初始化客户端

        Args:
            host: ShardingSphere Proxy 主机
            port: Proxy 端口 (默认 3309)
            user: 用户名
            password: 密码
            database: 逻辑数据库名
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self._pool: Optional[aiomysql.Pool] = None

    async def connect(self):
        """创建连接池"""
        if self._pool is None:
            self._pool = await aiomysql.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                db=self.database,
                minsize=1,
                maxsize=5,
                autocommit=True,
            )

    async def close(self):
        """关闭连接池"""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @asynccontextmanager
    async def _get_cursor(self):
        """获取游标"""
        if self._pool is None:
            await self.connect()
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                yield cursor

    async def execute(self, sql: str, args: Optional[tuple] = None) -> list[dict]:
        """执行 SQL 并返回结果

        Args:
            sql: SQL 语句
            args: 参数

        Returns:
            结果列表
        """
        async with self._get_cursor() as cursor:
            await cursor.execute(sql, args)
            try:
                return await cursor.fetchall()
            except Exception:
                return []

    async def list_mask_rules(self) -> list[dict]:
        """列出所有脱敏规则

        Returns:
            脱敏规则列表
        """
        results = await self.execute("SHOW MASK RULES")
        return list(results)

    async def list_mask_algorithms(self) -> list[dict]:
        """列出所有脱敏算法

        Returns:
            脱敏算法列表
        """
        results = await self.execute("SHOW MASK ALGORITHMS")
        return list(results)

    async def get_table_rules(self, table_name: str) -> list[dict]:
        """获取表的脱敏规则

        Args:
            table_name: 表名

        Returns:
            该表的脱敏规则列表
        """
        results = await self.execute(f"SHOW MASK RULES FROM {table_name}")
        return list(results)

    async def add_mask_rule(
        self,
        table_name: str,
        column_name: str,
        algorithm_type: str,
        algorithm_props: Optional[dict] = None,
    ) -> bool:
        """添加脱敏规则

        Args:
            table_name: 表名
            column_name: 列名
            algorithm_type: 算法类型 (KEEP_FIRST_N_LAST_M, MD5, MASK_FIRST_N_LAST_M, ...)
            algorithm_props: 算法参数

        Returns:
            是否成功
        """
        props_str = self._format_props(algorithm_props)
        sql = f"""
        CREATE MASK RULE {table_name} (
            COLUMNS(
                (NAME={column_name}, TYPE(NAME='{algorithm_type}'{props_str}))
            )
        )
        """
        try:
            await self.execute(sql.strip())
            logger.info(f"添加脱敏规则: {table_name}.{column_name} -> {algorithm_type}")
            return True
        except Exception as e:
            logger.error(f"添加脱敏规则失败: {e}")
            return False

    async def alter_mask_rule(
        self,
        table_name: str,
        column_name: str,
        algorithm_type: str,
        algorithm_props: Optional[dict] = None,
    ) -> bool:
        """修改脱敏规则

        Args:
            table_name: 表名
            column_name: 列名
            algorithm_type: 算法类型
            algorithm_props: 算法参数

        Returns:
            是否成功
        """
        props_str = self._format_props(algorithm_props)
        sql = f"""
        ALTER MASK RULE {table_name} (
            COLUMNS(
                (NAME={column_name}, TYPE(NAME='{algorithm_type}'{props_str}))
            )
        )
        """
        try:
            await self.execute(sql.strip())
            logger.info(f"修改脱敏规则: {table_name}.{column_name} -> {algorithm_type}")
            return True
        except Exception as e:
            logger.error(f"修改脱敏规则失败: {e}")
            return False

    async def upsert_mask_rule(
        self,
        table_name: str,
        column_name: str,
        algorithm_type: str,
        algorithm_props: Optional[dict] = None,
    ) -> bool:
        """添加或更新脱敏规则

        先尝试修改，失败则添加。

        Args:
            table_name: 表名
            column_name: 列名
            algorithm_type: 算法类型
            algorithm_props: 算法参数

        Returns:
            是否成功
        """
        # 先尝试 ALTER
        success = await self.alter_mask_rule(
            table_name, column_name, algorithm_type, algorithm_props
        )
        if not success:
            # 规则不存在，尝试 CREATE
            success = await self.add_mask_rule(
                table_name, column_name, algorithm_type, algorithm_props
            )
        return success

    async def drop_mask_rule(self, table_name: str) -> bool:
        """删除表的所有脱敏规则

        Args:
            table_name: 表名

        Returns:
            是否成功
        """
        try:
            await self.execute(f"DROP MASK RULE {table_name}")
            logger.info(f"删除脱敏规则: {table_name}")
            return True
        except Exception as e:
            logger.error(f"删除脱敏规则失败: {e}")
            return False

    def _format_props(self, props: Optional[dict]) -> str:
        """格式化算法参数

        Args:
            props: 参数字典

        Returns:
            DistSQL 格式的参数字符串
        """
        if not props:
            return ""
        pairs = ", ".join(f'"{k}"="{v}"' for k, v in props.items())
        return f", PROPERTIES({pairs})"


# 预定义的脱敏算法类型
class MaskAlgorithms:
    """ShardingSphere 内置脱敏算法"""

    # 保留前 N 后 M 位
    KEEP_FIRST_N_LAST_M = "KEEP_FIRST_N_LAST_M"

    # 遮盖前 N 后 M 位
    MASK_FIRST_N_LAST_M = "MASK_FIRST_N_LAST_M"

    # MD5 哈希
    MD5 = "MD5"

    # 固定替换字符
    MASK_BEFORE_SPECIAL_CHARS = "MASK_BEFORE_SPECIAL_CHARS"

    # 电话号码脱敏 (保留前3后4)
    @staticmethod
    def phone_mask():
        return (
            MaskAlgorithms.KEEP_FIRST_N_LAST_M,
            {"first-n": "3", "last-m": "4", "replace-char": "*"},
        )

    # 身份证号脱敏 (保留前6后4)
    @staticmethod
    def id_card_mask():
        return (
            MaskAlgorithms.KEEP_FIRST_N_LAST_M,
            {"first-n": "6", "last-m": "4", "replace-char": "*"},
        )

    # 银行卡号脱敏 (保留后4位)
    @staticmethod
    def bank_card_mask():
        return (
            MaskAlgorithms.KEEP_FIRST_N_LAST_M,
            {"first-n": "0", "last-m": "4", "replace-char": "*"},
        )

    # 邮箱脱敏 (@ 前全部遮盖)
    @staticmethod
    def email_mask():
        return (
            MaskAlgorithms.MASK_BEFORE_SPECIAL_CHARS,
            {"special-chars": "@", "replace-char": "*"},
        )
