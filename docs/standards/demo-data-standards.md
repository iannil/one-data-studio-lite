# 演示数据标准规范

**版本**: 1.0
**适用范围**: ONE-DATA-STUDIO-LITE 演示数据集
**业务场景**: 智慧零售电商平台

---

## 一、数据标准总则

### 1.1 命名规范

| 对象 | 规范 | 示例 |
|------|------|------|
| 数据库 | 小写+下划线 | `demo_retail_db` |
| 表名 | 层级前缀+下划线分隔 | `ods_user_info`, `dwd_order_detail` |
| 字段名 | 小写+下划线分隔 | `user_id`, `order_amount` |
| 索引名 | `idx_`前缀+字段名 | `idx_user_id`, `idx_order_date` |
| 主键 | `id`后缀或业务名+`_id` | `user_id`, `order_id` |
| 外键 | 关联表名+`_id` | `user_id`, `product_id` |

### 1.2 数据分层规范

| 层级 | 前缀 | 说明 | 保留期限 |
|------|------|------|----------|
| ODS | `ods_` | 原始数据层，保持源系统格式 | 180天 |
| DWD | `dwd_` | 明细数据层，清洗、脱敏、标准化 | 365天 |
| DWS | `dws_` | 汇总数据层，按维度汇总 | 永久 |
| ADS | `ads_` | 应用数据层，面向业务应用 | 永久 |
| DIM | `dim_` | 维度数据表（预留） | 永久 |

### 1.3 字段标准

#### 用户域字段

| 字段名 | 类型 | 说明 | 格式/约束 |
|--------|------|------|-----------|
| user_id | BIGINT | 用户ID | 主键，自增 |
| username | VARCHAR(50) | 用户名 | 唯一，4-50字符 |
| phone | VARCHAR(20) | 手机号（明文） | 11位数字 |
| phone_desensitized | VARCHAR(20) | 手机号（脱敏） | 138****8000 |
| email | VARCHAR(100) | 邮箱 | 标准邮箱格式 |
| id_card | VARCHAR(18) | 身份证号（明文） | 18位 |
| id_card_desensitized | VARCHAR(18) | 身份证号（脱敏） | 6位+4位 |
| gender | TINYINT | 性别 | 0未知 1男 2女 |
| age | INT | 年龄 | 18-120 |
| user_type | TINYINT | 用户类型 | 1普通 2VIP 3企业 |
| status | TINYINT | 状态 | 1正常 2冻结 3注销 |

#### 商品域字段

| 字段名 | 类型 | 说明 | 格式/约束 |
|--------|------|------|-----------|
| product_id | BIGINT | 商品ID | 主键，自增 |
| product_code | VARCHAR(50) | 商品编码 | 唯一 |
| product_name | VARCHAR(255) | 商品名称 | 非空 |
| category_l1/l2/l3 | VARCHAR(50) | 一级/二级/三级分类 | -- |
| brand | VARCHAR(50) | 品牌 | -- |
| price | DECIMAL(10,2) | 价格 | 非负，2位小数 |
| stock | INT | 库存 | 非负 |

#### 订单域字段

| 字段名 | 类型 | 说明 | 格式/约束 |
|--------|------|------|-----------|
| order_id | BIGINT | 订单ID | 主键，自增 |
| order_no | VARCHAR(32) | 订单编号 | 唯一，业务编码 |
| user_id | BIGINT | 用户ID | 外键 |
| total_amount | DECIMAL(10,2) | 订单总额 | 非负 |
| pay_amount | DECIMAL(10,2) | 实付金额 | 非负 |
| order_status | TINYINT | 订单状态 | 0待付 1待发 2待收 3完成 4取消 5售后 |

---

## 二、敏感数据标准

### 2.1 敏感字段分类

| 级别 | 类型 | 说明 | 脱敏规则 |
|------|------|------|----------|
| critical | 身份证号 | 最高敏感 | 保留前6后4位 |
| critical | 银行卡号 | 最高敏感 | 保留前6后4位 |
| high | 手机号 | 高敏感 | 保留前3后4位 |
| high | 详细地址 | 高敏感 | 隐藏门牌号 |
| medium | 邮箱 | 中敏感 | 保留@前2位 |
| low | 姓名 | 低敏感 | 姓+* |

### 2.2 脱敏算法

| 算法名 | 模式 | 示例 |
|--------|------|------|
| MASK_PHONE_CN | *** | 138****8000 |
| MASK_ID_CARD_CN | ****** | 110101********1234 |
| MASK_EMAIL | ***@ | us***@example.com |
| MASK_NAME | * | 张* |

---

## 三、数据关联标准

### 3.1 主键设计

| 表名 | 主键 | 说明 |
|------|------|------|
| ods_user_info | user_id | BIGINT自增 |
| ods_product_info | product_id | BIGINT自增 |
| ods_order_info | order_id | BIGINT自增 |
| dwd_user_info | user_id | 继承自ODS |
| dws_user_day | user_id, stat_date | 复合主键 |

### 3.2 外键关系

```
ods_user_info.user_id → dwd_user_info.user_id
ods_product_info.product_id → dwd_product_info.product_id
ods_order_info.order_id → dwd_order_detail.order_id
ods_order_info.user_id → dwd_user_info.user_id
```

---

## 四、枚举值标准

### 4.1 用户状态

| 值 | 名称 | 说明 |
|----|------|------|
| 1 | 正常 | 可以正常使用系统 |
| 2 | 冻结 | 暂时禁止使用 |
| 3 | 注销 | 已注销 |

### 4.2 订单状态

| 值 | 名称 | 说明 |
|----|------|------|
| 0 | 待支付 | 未支付 |
| 1 | 待发货 | 已支付待发货 |
| 2 | 待收货 | 已发货待收货 |
| 3 | 已完成 | 交易完成 |
| 4 | 已取消 | 订单取消 |
| 5 | 售后中 | 售后处理中 |

### 4.3 数据源类型

| 值 | 名称 |
|----|------|
| MySQL | 关系型数据库 |
| PostgreSQL | 关系型数据库 |
| Kafka | 消息队列 |
| Hive | 数据仓库 |
| ClickHouse | OLAP数据库 |
| API | 外部接口 |

---

## 五、数据质量标准

### 5.1 质量评分标准

| 分数区间 | 等级 | 说明 |
|----------|------|------|
| 95-100 | excellent | 优秀 |
| 90-94 | good | 良好 |
| 80-89 | fair | 一般 |
| <80 | poor | 差 |

### 5.2 质量检测规则

| 检测项 | 阈值 | 说明 |
|--------|------|------|
| 空值率 | <5% | 字段空值比例 |
| 重复率 | <1% | 主键重复比例 |
| 格式符合率 | >98% | 正则匹配通过率 |
| 及时性 | <1h | 数据延迟 |

---

## 六、Mock数据标准

### 6.1 Mock API响应格式

```typescript
// 成功响应
{
  code: 0,
  message: "success",
  data: any,
  timestamp: number
}

// 错误响应
{
  code: -1,
  message: string,
  data: null,
  timestamp: number
}
```

### 6.2 分页参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | number | 1 | 页码 |
| pageSize | number | 10 | 每页数量 |
| sortField | string | - | 排序字段 |
| sortOrder | asc/desc | - | 排序方向 |

### 6.3 分页响应

```typescript
{
  list: T[],
  total: number,
  page: number,
  pageSize: number
}
```

---

**文档版本**: 1.0
**最后更新**: 2024-02-01
**维护人**: admin
