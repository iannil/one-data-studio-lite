"""NL2SQL 服务 - LLM 提示词模板"""

SYSTEM_PROMPT = """你是一个专业的 SQL 生成助手。根据用户的自然语言问题和数据库表结构信息，生成准确的 SQL 查询语句。

规则：
1. 只生成 SELECT 查询，不生成 INSERT/UPDATE/DELETE
2. 使用标准 SQL 语法，兼容 MySQL
3. 对于模糊的时间表述（如"最近7天"），使用 DATE_SUB(CURDATE(), INTERVAL 7 DAY)
4. 字段名和表名使用反引号包裹
5. 限制结果集大小，默认 LIMIT 100
6. 输出格式：只输出 SQL 语句，不要其他解释

"""

SCHEMA_TEMPLATE = """可用的数据库表结构如下：

{schema_info}

"""

QUERY_TEMPLATE = """用户问题: {question}

请生成对应的 SQL 查询语句:"""

EXPLAIN_TEMPLATE = """请用简洁的中文解释以下 SQL 查询的含义和作用：

```sql
{sql}
```

表结构信息：
{schema_info}

请用通俗易懂的中文解释这条 SQL 做了什么。"""

# Few-shot 示例
FEW_SHOT_EXAMPLES = [
    {
        "question": "查询近7天的订单总数",
        "sql": "SELECT COUNT(*) AS `订单总数` FROM `t_order` WHERE `create_time` >= DATE_SUB(CURDATE(), INTERVAL 7 DAY);"
    },
    {
        "question": "统计每个部门的员工数量，按数量降序排列",
        "sql": "SELECT `dept_name` AS `部门`, COUNT(*) AS `员工数量` FROM `t_employee` GROUP BY `dept_name` ORDER BY `员工数量` DESC;"
    },
    {
        "question": "查找金额最大的前10笔交易",
        "sql": "SELECT `id`, `user_id`, `amount`, `create_time` FROM `t_transaction` ORDER BY `amount` DESC LIMIT 10;"
    },
]
