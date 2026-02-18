"""
电商演示数据初始化脚本 - 全生命周期测试数据方案

生成规模:
- 产品分类: 15条
- 产品: 200条
- 客户: 1000条
- 订单: 5000条
- 订单明细: ~12000条

数据生命周期:
1. 业务数据 (categories, products, customers, orders)
2. 数据源配置 (PostgreSQL, CSV)
3. 元数据扫描与注册
4. 数据采集任务
5. ETL管道配置
6. 数据资产注册
"""
from __future__ import annotations

import asyncio
import random
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from faker import Faker
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal, engine, Base
from app.models.metadata import DataSource, DataSourceType, DataSourceStatus, MetadataTable, MetadataColumn
from app.models.collect import CollectTask, CollectTaskStatus
from app.models.etl import ETLPipeline, ETLStep, ETLStepType, PipelineStatus
from app.models.asset import DataAsset, AssetType, AccessLevel


fake = Faker('zh_CN')
fake_en = Faker('en_US')

# Configuration
CONFIG = {
    'categories': 15,
    'products': 200,
    'customers': 1000,
    'orders': 5000,
}

# Product category data
CATEGORY_DATA = [
    {'name': '电子产品', 'parent': None, 'sort': 1},
    {'name': '服装', 'parent': None, 'sort': 2},
    {'name': '家居', 'parent': None, 'sort': 3},
    {'name': '食品', 'parent': None, 'sort': 4},
    {'name': '手机', 'parent': '电子产品', 'sort': 1},
    {'name': '电脑', 'parent': '电子产品', 'sort': 2},
    {'name': '配件', 'parent': '电子产品', 'sort': 3},
    {'name': '男装', 'parent': '服装', 'sort': 1},
    {'name': '女装', 'parent': '服装', 'sort': 2},
    {'name': '童装', 'parent': '服装', 'sort': 3},
    {'name': '家具', 'parent': '家居', 'sort': 1},
    {'name': '厨具', 'parent': '家居', 'sort': 2},
    {'name': '零食', 'parent': '食品', 'sort': 1},
    {'name': '饮料', 'parent': '食品', 'sort': 2},
    {'name': '生鲜', 'parent': '食品', 'sort': 3},
]

# Brand data by category
BRANDS = {
    '手机': ['Apple', 'Samsung', 'Huawei', 'Xiaomi', 'OPPO', 'vivo', 'OnePlus'],
    '电脑': ['Apple', 'Lenovo', 'Dell', 'HP', 'ASUS', 'Acer', 'Microsoft'],
    '配件': ['Apple', 'Anker', 'Belkin', 'Logitech', 'Razer', 'JBL', 'Sony'],
    '男装': ['UNIQLO', 'ZARA', 'H&M', 'Nike', 'Adidas', 'GAP', 'Levis'],
    '女装': ['ZARA', 'H&M', 'UNIQLO', 'Only', 'Vero Moda', 'Lululemon', 'COS'],
    '童装': ['GAP Kids', 'UNIQLO', 'Carter\'s', 'H&M Kids', 'ZARA Kids'],
    '家具': ['IKEA', '全友', '顾家', '芝华仕', '宜家', '红星美凯龙'],
    '厨具': ['苏泊尔', '美的', '九阳', '小熊', 'WMF', '双立人'],
    '零食': ['三只松鼠', '良品铺子', '百草味', '旺旺', '乐事', '奥利奥'],
    '饮料': ['可口可乐', '百事可乐', '农夫山泉', '元气森林', '康师傅', '统一'],
    '生鲜': ['盒马', '叮咚', '美团', '每日优鲜', '山姆'],
}

# Price ranges by category
PRICE_RANGES = {
    '手机': (1999, 12999),
    '电脑': (3999, 29999),
    '配件': (49, 2999),
    '男装': (99, 999),
    '女装': (99, 1999),
    '童装': (49, 499),
    '家具': (299, 9999),
    '厨具': (49, 1999),
    '零食': (9.9, 199),
    '饮料': (3, 99),
    '生鲜': (9.9, 299),
}

# VIP levels and their weights
VIP_LEVELS = [
    ('normal', 0.5),
    ('silver', 0.25),
    ('gold', 0.15),
    ('platinum', 0.08),
    ('diamond', 0.02),
]

# Payment methods
PAYMENT_METHODS = ['alipay', 'wechat', 'creditcard', 'debitcard', 'cash_on_delivery']

# Order statuses and weights
ORDER_STATUSES = [
    ('completed', 0.7),
    ('shipped', 0.15),
    ('pending', 0.1),
    ('cancelled', 0.05),
]

# Chinese cities
CITIES = [
    ('北京', '北京'), ('上海', '上海'), ('广州', '广东'), ('深圳', '广东'),
    ('杭州', '浙江'), ('南京', '江苏'), ('成都', '四川'), ('武汉', '湖北'),
    ('西安', '陕西'), ('重庆', '重庆'), ('苏州', '江苏'), ('天津', '天津'),
    ('青岛', '山东'), ('郑州', '河南'), ('长沙', '湖南'), ('沈阳', '辽宁'),
    ('合肥', '安徽'), ('福州', '福建'), ('济南', '山东'), ('昆明', '云南'),
]


def weighted_choice(choices: list[tuple[str, float]]) -> str:
    """Select a value based on weighted probabilities."""
    total = sum(w for _, w in choices)
    r = random.uniform(0, total)
    cumulative = 0
    for value, weight in choices:
        cumulative += weight
        if r <= cumulative:
            return value
    return choices[-1][0]


async def create_ecommerce_tables(session: AsyncSession) -> None:
    """Create e-commerce business tables in the database."""
    print("  Creating e-commerce tables...")

    ddl_statements = """
    -- Drop existing tables if any (for clean start)
    DROP TABLE IF EXISTS order_items CASCADE;
    DROP TABLE IF EXISTS orders CASCADE;
    DROP TABLE IF EXISTS products CASCADE;
    DROP TABLE IF EXISTS categories CASCADE;
    DROP TABLE IF EXISTS customers CASCADE;
    DROP TABLE IF EXISTS sales_daily_report CASCADE;
    DROP TABLE IF EXISTS customer_analysis CASCADE;
    DROP TABLE IF EXISTS customers_masked CASCADE;
    DROP TABLE IF EXISTS dw_customers CASCADE;
    DROP TABLE IF EXISTS dw_orders CASCADE;
    DROP TABLE IF EXISTS dw_sales_summary CASCADE;

    -- Customers table
    CREATE TABLE customers (
        id SERIAL PRIMARY KEY,
        customer_code VARCHAR(20) UNIQUE NOT NULL,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(100),
        phone VARCHAR(20),
        gender VARCHAR(10),
        birth_date DATE,
        city VARCHAR(50),
        province VARCHAR(50),
        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        vip_level VARCHAR(20) DEFAULT 'normal',
        total_spent DECIMAL(12,2) DEFAULT 0,
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Categories table
    CREATE TABLE categories (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        parent_id INTEGER REFERENCES categories(id),
        description TEXT,
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Products table
    CREATE TABLE products (
        id SERIAL PRIMARY KEY,
        product_code VARCHAR(30) UNIQUE NOT NULL,
        name VARCHAR(200) NOT NULL,
        category_id INTEGER REFERENCES categories(id),
        brand VARCHAR(100),
        price DECIMAL(10,2) NOT NULL,
        cost DECIMAL(10,2),
        stock_quantity INTEGER DEFAULT 0,
        unit VARCHAR(20),
        status VARCHAR(20) DEFAULT 'active',
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Orders table
    CREATE TABLE orders (
        id SERIAL PRIMARY KEY,
        order_no VARCHAR(30) UNIQUE NOT NULL,
        customer_id INTEGER REFERENCES customers(id),
        order_date TIMESTAMP NOT NULL,
        status VARCHAR(20) DEFAULT 'pending',
        total_amount DECIMAL(12,2) NOT NULL,
        discount_amount DECIMAL(10,2) DEFAULT 0,
        payment_method VARCHAR(30),
        shipping_address TEXT,
        shipped_at TIMESTAMP,
        delivered_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Order items table
    CREATE TABLE order_items (
        id SERIAL PRIMARY KEY,
        order_id INTEGER REFERENCES orders(id),
        product_id INTEGER REFERENCES products(id),
        quantity INTEGER NOT NULL,
        unit_price DECIMAL(10,2) NOT NULL,
        subtotal DECIMAL(10,2) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- ETL target tables (for demonstration)
    CREATE TABLE sales_daily_report (
        id SERIAL PRIMARY KEY,
        report_date DATE NOT NULL,
        category_name VARCHAR(100),
        total_orders INTEGER,
        total_customers INTEGER,
        total_revenue DECIMAL(12,2),
        total_cost DECIMAL(12,2),
        profit DECIMAL(12,2),
        avg_order_value DECIMAL(10,2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE customer_analysis (
        id SERIAL PRIMARY KEY,
        customer_id INTEGER,
        customer_code VARCHAR(20),
        customer_name VARCHAR(100),
        vip_level VARCHAR(20),
        city VARCHAR(50),
        total_orders INTEGER,
        total_spent DECIMAL(12,2),
        avg_order_value DECIMAL(10,2),
        last_order_date DATE,
        days_since_last_order INTEGER,
        customer_segment VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE customers_masked (
        id SERIAL PRIMARY KEY,
        customer_code VARCHAR(20),
        name VARCHAR(100),
        email VARCHAR(100),
        phone VARCHAR(20),
        gender VARCHAR(10),
        city VARCHAR(50),
        province VARCHAR(50),
        vip_level VARCHAR(20),
        is_active BOOLEAN,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Data warehouse staging tables
    CREATE TABLE dw_customers (
        id SERIAL PRIMARY KEY,
        customer_code VARCHAR(20),
        name VARCHAR(100),
        email VARCHAR(100),
        phone VARCHAR(20),
        city VARCHAR(50),
        province VARCHAR(50),
        vip_level VARCHAR(20),
        total_spent DECIMAL(12,2),
        is_active BOOLEAN,
        synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE dw_orders (
        id SERIAL PRIMARY KEY,
        order_no VARCHAR(30),
        customer_id INTEGER,
        order_date TIMESTAMP,
        status VARCHAR(20),
        total_amount DECIMAL(12,2),
        payment_method VARCHAR(30),
        synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE dw_sales_summary (
        id SERIAL PRIMARY KEY,
        sale_date DATE,
        category_name VARCHAR(100),
        total_sales DECIMAL(12,2),
        order_count INTEGER,
        synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Create indexes for better performance
    CREATE INDEX idx_customers_city ON customers(city);
    CREATE INDEX idx_customers_vip ON customers(vip_level);
    CREATE INDEX idx_products_category ON products(category_id);
    CREATE INDEX idx_products_brand ON products(brand);
    CREATE INDEX idx_orders_customer ON orders(customer_id);
    CREATE INDEX idx_orders_date ON orders(order_date);
    CREATE INDEX idx_orders_status ON orders(status);
    CREATE INDEX idx_order_items_order ON order_items(order_id);
    CREATE INDEX idx_order_items_product ON order_items(product_id);
    """

    for statement in ddl_statements.split(';'):
        statement = statement.strip()
        if statement:
            await session.execute(text(statement))

    await session.commit()
    print("  E-commerce tables created successfully")


async def create_categories(session: AsyncSession) -> dict[str, int]:
    """Create product categories and return name->id mapping."""
    print("  Creating product categories...")

    category_ids: dict[str, int] = {}

    # First pass: create parent categories
    for cat in CATEGORY_DATA:
        if cat['parent'] is None:
            result = await session.execute(
                text("""
                    INSERT INTO categories (name, parent_id, description, sort_order)
                    VALUES (:name, NULL, :desc, :sort)
                    RETURNING id
                """),
                {
                    'name': cat['name'],
                    'desc': f"{cat['name']}类商品",
                    'sort': cat['sort'],
                }
            )
            category_ids[cat['name']] = result.scalar_one()

    await session.commit()

    # Second pass: create child categories
    for cat in CATEGORY_DATA:
        if cat['parent'] is not None:
            parent_id = category_ids.get(cat['parent'])
            result = await session.execute(
                text("""
                    INSERT INTO categories (name, parent_id, description, sort_order)
                    VALUES (:name, :parent_id, :desc, :sort)
                    RETURNING id
                """),
                {
                    'name': cat['name'],
                    'parent_id': parent_id,
                    'desc': f"{cat['name']}类商品",
                    'sort': cat['sort'],
                }
            )
            category_ids[cat['name']] = result.scalar_one()

    await session.commit()
    print(f"  Created {len(category_ids)} categories")
    return category_ids


async def create_products(session: AsyncSession, category_ids: dict[str, int]) -> list[dict]:
    """Create product data."""
    print(f"  Creating {CONFIG['products']} products...")

    products = []
    product_idx = 1

    # Get child categories (which have products)
    child_categories = [cat['name'] for cat in CATEGORY_DATA if cat['parent'] is not None]

    for _ in range(CONFIG['products']):
        category = random.choice(child_categories)
        category_id = category_ids[category]
        brands = BRANDS.get(category, ['Generic'])
        brand = random.choice(brands)
        price_range = PRICE_RANGES.get(category, (10, 1000))
        price = round(random.uniform(*price_range), 2)
        cost = round(price * random.uniform(0.5, 0.8), 2)

        product_name = f"{brand} {fake.word()}{fake.word()} {fake_en.word().capitalize()}"

        product = {
            'product_code': f'P{product_idx:05d}',
            'name': product_name[:200],
            'category_id': category_id,
            'brand': brand,
            'price': price,
            'cost': cost,
            'stock': random.randint(0, 1000),
            'unit': random.choice(['件', '个', '台', '套', '盒', '包']),
            'status': random.choices(['active', 'inactive', 'discontinued'], weights=[0.85, 0.1, 0.05])[0],
        }

        await session.execute(
            text("""
                INSERT INTO products (product_code, name, category_id, brand, price, cost, stock_quantity, unit, status, description)
                VALUES (:code, :name, :cat_id, :brand, :price, :cost, :stock, :unit, :status, :desc)
            """),
            {
                'code': product['product_code'],
                'name': product['name'],
                'cat_id': product['category_id'],
                'brand': product['brand'],
                'price': product['price'],
                'cost': product['cost'],
                'stock': product['stock'],
                'unit': product['unit'],
                'status': product['status'],
                'desc': f"{brand} {category}产品",
            }
        )

        products.append(product)
        product_idx += 1

        if product_idx % 50 == 0:
            await session.commit()

    await session.commit()
    print(f"  Created {len(products)} products")
    return products


async def create_customers(session: AsyncSession) -> list[dict]:
    """Create customer data."""
    print(f"  Creating {CONFIG['customers']} customers...")

    customers = []

    for i in range(1, CONFIG['customers'] + 1):
        gender = random.choice(['男', '女'])
        city, province = random.choice(CITIES)
        vip_level = weighted_choice(VIP_LEVELS)

        customer = {
            'customer_code': f'C{i:05d}',
            'name': fake.name_male() if gender == '男' else fake.name_female(),
            'email': fake_en.email(),
            'phone': fake.phone_number(),
            'gender': gender,
            'birth_date': fake.date_of_birth(minimum_age=18, maximum_age=70),
            'city': city,
            'province': province,
            'registration_date': fake.date_time_between(start_date='-3y', end_date='now'),
            'vip_level': vip_level,
            'is_active': random.random() > 0.05,
        }

        await session.execute(
            text("""
                INSERT INTO customers (customer_code, name, email, phone, gender, birth_date, city, province, registration_date, vip_level, is_active)
                VALUES (:code, :name, :email, :phone, :gender, :birth_date, :city, :province, :reg_date, :vip, :active)
            """),
            {
                'code': customer['customer_code'],
                'name': customer['name'],
                'email': customer['email'],
                'phone': customer['phone'],
                'gender': customer['gender'],
                'birth_date': customer['birth_date'],
                'city': customer['city'],
                'province': customer['province'],
                'reg_date': customer['registration_date'],
                'vip': customer['vip_level'],
                'active': customer['is_active'],
            }
        )

        customers.append(customer)

        if i % 200 == 0:
            await session.commit()
            print(f"    Progress: {i}/{CONFIG['customers']} customers")

    await session.commit()
    print(f"  Created {len(customers)} customers")
    return customers


async def create_orders(session: AsyncSession, num_customers: int, num_products: int) -> None:
    """Create orders and order items."""
    print(f"  Creating {CONFIG['orders']} orders...")

    start_date = datetime.now() - timedelta(days=365)
    end_date = datetime.now()

    for i in range(1, CONFIG['orders'] + 1):
        customer_id = random.randint(1, num_customers)
        order_date = fake.date_time_between(start_date=start_date, end_date=end_date)
        status = weighted_choice(ORDER_STATUSES)
        payment_method = random.choice(PAYMENT_METHODS)

        # Generate order items (1-5 items per order)
        num_items = random.randint(1, 5)
        product_ids = random.sample(range(1, num_products + 1), min(num_items, num_products))

        order_no = f"ORD{order_date.strftime('%Y%m%d')}{i:06d}"

        # Calculate totals
        total_amount = Decimal('0')
        items_data = []

        for product_id in product_ids:
            # Get product price (simplified - use random for demo)
            unit_price = Decimal(str(round(random.uniform(10, 5000), 2)))
            quantity = random.randint(1, 3)
            subtotal = unit_price * quantity
            total_amount += subtotal
            items_data.append({
                'product_id': product_id,
                'quantity': quantity,
                'unit_price': float(unit_price),
                'subtotal': float(subtotal),
            })

        discount = Decimal(str(round(float(total_amount) * random.uniform(0, 0.1), 2)))

        # Determine shipped/delivered dates based on status
        shipped_at = None
        delivered_at = None
        if status in ('shipped', 'completed'):
            shipped_at = order_date + timedelta(days=random.randint(1, 3))
        if status == 'completed':
            delivered_at = shipped_at + timedelta(days=random.randint(1, 5)) if shipped_at else None

        # Insert order
        result = await session.execute(
            text("""
                INSERT INTO orders (order_no, customer_id, order_date, status, total_amount, discount_amount, payment_method, shipping_address, shipped_at, delivered_at)
                VALUES (:order_no, :customer_id, :order_date, :status, :total, :discount, :payment, :address, :shipped, :delivered)
                RETURNING id
            """),
            {
                'order_no': order_no,
                'customer_id': customer_id,
                'order_date': order_date,
                'status': status,
                'total': float(total_amount),
                'discount': float(discount),
                'payment': payment_method,
                'address': fake.address(),
                'shipped': shipped_at,
                'delivered': delivered_at,
            }
        )
        order_id = result.scalar_one()

        # Insert order items
        for item in items_data:
            await session.execute(
                text("""
                    INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal)
                    VALUES (:order_id, :product_id, :quantity, :unit_price, :subtotal)
                """),
                {
                    'order_id': order_id,
                    'product_id': item['product_id'],
                    'quantity': item['quantity'],
                    'unit_price': item['unit_price'],
                    'subtotal': item['subtotal'],
                }
            )

        if i % 500 == 0:
            await session.commit()
            print(f"    Progress: {i}/{CONFIG['orders']} orders")

    await session.commit()

    # Update customer total_spent
    await session.execute(text("""
        UPDATE customers c
        SET total_spent = COALESCE((
            SELECT SUM(o.total_amount - o.discount_amount)
            FROM orders o
            WHERE o.customer_id = c.id AND o.status = 'completed'
        ), 0)
    """))
    await session.commit()

    print(f"  Created {CONFIG['orders']} orders with items")


async def create_data_source(session: AsyncSession) -> UUID:
    """Create PostgreSQL data source configuration."""
    print("  Creating data source configuration...")

    # Check if already exists
    existing = await session.execute(
        text("SELECT id FROM data_sources WHERE name = :name"),
        {'name': '电商业务数据库'}
    )
    existing_id = existing.scalar_one_or_none()

    if existing_id:
        print("  Data source already exists, skipping...")
        return existing_id

    data_source = DataSource(
        name='电商业务数据库',
        description='电商平台核心业务数据库，包含客户、产品、订单等数据',
        type=DataSourceType.POSTGRESQL,
        connection_config={
            'host': 'localhost',
            'port': 5432,
            'database': 'smart_data',
            'username': 'postgres',
            'password': 'postgres',
        },
        status=DataSourceStatus.ACTIVE,
        last_connected_at=datetime.now(),
    )
    session.add(data_source)
    await session.commit()
    await session.refresh(data_source)

    print(f"  Created data source: {data_source.name} (ID: {data_source.id})")
    return data_source.id


async def create_csv_data_source(session: AsyncSession) -> UUID:
    """Create CSV data source for external supplier data."""
    print("  Creating CSV data source configuration...")

    existing = await session.execute(
        text("SELECT id FROM data_sources WHERE name = :name"),
        {'name': '外部供应商数据'}
    )
    existing_id = existing.scalar_one_or_none()

    if existing_id:
        print("  CSV data source already exists, skipping...")
        return existing_id

    csv_source = DataSource(
        name='外部供应商数据',
        description='外部供应商提供的产品目录数据',
        type=DataSourceType.CSV,
        connection_config={
            'file_path': '/data/supplier_products.csv',
        },
        status=DataSourceStatus.ACTIVE,
    )
    session.add(csv_source)
    await session.commit()
    await session.refresh(csv_source)

    print(f"  Created CSV data source: {csv_source.name} (ID: {csv_source.id})")
    return csv_source.id


async def scan_metadata(session: AsyncSession, source_id: UUID) -> None:
    """Scan and register metadata for business tables."""
    print("  Scanning and registering metadata...")

    tables_metadata = [
        {
            'table_name': 'customers',
            'description': '客户主数据表，存储客户基本信息和VIP等级',
            'ai_description': '电商平台客户信息表，包含个人资料、联系方式和消费统计',
            'tags': ['客户', '主数据', 'PII'],
            'columns': [
                {'name': 'id', 'type': 'integer', 'pk': True, 'nullable': False, 'desc': '客户唯一标识'},
                {'name': 'customer_code', 'type': 'varchar(20)', 'pk': False, 'nullable': False, 'desc': '客户编码'},
                {'name': 'name', 'type': 'varchar(100)', 'pk': False, 'nullable': False, 'desc': '客户姓名', 'category': 'PII'},
                {'name': 'email', 'type': 'varchar(100)', 'pk': False, 'nullable': True, 'desc': '邮箱地址', 'category': 'PII'},
                {'name': 'phone', 'type': 'varchar(20)', 'pk': False, 'nullable': True, 'desc': '联系电话', 'category': 'PII'},
                {'name': 'gender', 'type': 'varchar(10)', 'pk': False, 'nullable': True, 'desc': '性别'},
                {'name': 'birth_date', 'type': 'date', 'pk': False, 'nullable': True, 'desc': '出生日期', 'category': 'PII'},
                {'name': 'city', 'type': 'varchar(50)', 'pk': False, 'nullable': True, 'desc': '所在城市'},
                {'name': 'province', 'type': 'varchar(50)', 'pk': False, 'nullable': True, 'desc': '所在省份'},
                {'name': 'vip_level', 'type': 'varchar(20)', 'pk': False, 'nullable': True, 'desc': 'VIP等级'},
                {'name': 'total_spent', 'type': 'decimal(12,2)', 'pk': False, 'nullable': True, 'desc': '累计消费金额', 'category': 'Financial'},
                {'name': 'is_active', 'type': 'boolean', 'pk': False, 'nullable': True, 'desc': '是否活跃'},
            ],
        },
        {
            'table_name': 'products',
            'description': '产品信息表，存储产品基本信息和库存',
            'ai_description': '电商平台产品目录，包含价格、品牌、库存等信息',
            'tags': ['产品', '目录', '库存'],
            'columns': [
                {'name': 'id', 'type': 'integer', 'pk': True, 'nullable': False, 'desc': '产品唯一标识'},
                {'name': 'product_code', 'type': 'varchar(30)', 'pk': False, 'nullable': False, 'desc': '产品编码'},
                {'name': 'name', 'type': 'varchar(200)', 'pk': False, 'nullable': False, 'desc': '产品名称'},
                {'name': 'category_id', 'type': 'integer', 'pk': False, 'nullable': True, 'desc': '分类ID'},
                {'name': 'brand', 'type': 'varchar(100)', 'pk': False, 'nullable': True, 'desc': '品牌'},
                {'name': 'price', 'type': 'decimal(10,2)', 'pk': False, 'nullable': False, 'desc': '售价', 'category': 'Financial'},
                {'name': 'cost', 'type': 'decimal(10,2)', 'pk': False, 'nullable': True, 'desc': '成本', 'category': 'Financial'},
                {'name': 'stock_quantity', 'type': 'integer', 'pk': False, 'nullable': True, 'desc': '库存数量'},
                {'name': 'status', 'type': 'varchar(20)', 'pk': False, 'nullable': True, 'desc': '状态'},
            ],
        },
        {
            'table_name': 'orders',
            'description': '订单表，存储订单交易信息',
            'ai_description': '电商平台订单记录，包含订单金额、支付方式、配送状态等',
            'tags': ['订单', '交易', '业务数据'],
            'columns': [
                {'name': 'id', 'type': 'integer', 'pk': True, 'nullable': False, 'desc': '订单唯一标识'},
                {'name': 'order_no', 'type': 'varchar(30)', 'pk': False, 'nullable': False, 'desc': '订单编号'},
                {'name': 'customer_id', 'type': 'integer', 'pk': False, 'nullable': True, 'desc': '客户ID'},
                {'name': 'order_date', 'type': 'timestamp', 'pk': False, 'nullable': False, 'desc': '订单日期'},
                {'name': 'status', 'type': 'varchar(20)', 'pk': False, 'nullable': True, 'desc': '订单状态'},
                {'name': 'total_amount', 'type': 'decimal(12,2)', 'pk': False, 'nullable': False, 'desc': '订单总金额', 'category': 'Financial'},
                {'name': 'discount_amount', 'type': 'decimal(10,2)', 'pk': False, 'nullable': True, 'desc': '折扣金额', 'category': 'Financial'},
                {'name': 'payment_method', 'type': 'varchar(30)', 'pk': False, 'nullable': True, 'desc': '支付方式'},
            ],
        },
        {
            'table_name': 'order_items',
            'description': '订单明细表，存储订单商品明细',
            'ai_description': '订单商品明细，关联订单和产品的中间表',
            'tags': ['订单', '明细'],
            'columns': [
                {'name': 'id', 'type': 'integer', 'pk': True, 'nullable': False, 'desc': '明细唯一标识'},
                {'name': 'order_id', 'type': 'integer', 'pk': False, 'nullable': True, 'desc': '订单ID'},
                {'name': 'product_id', 'type': 'integer', 'pk': False, 'nullable': True, 'desc': '产品ID'},
                {'name': 'quantity', 'type': 'integer', 'pk': False, 'nullable': False, 'desc': '购买数量'},
                {'name': 'unit_price', 'type': 'decimal(10,2)', 'pk': False, 'nullable': False, 'desc': '单价', 'category': 'Financial'},
                {'name': 'subtotal', 'type': 'decimal(10,2)', 'pk': False, 'nullable': False, 'desc': '小计', 'category': 'Financial'},
            ],
        },
        {
            'table_name': 'categories',
            'description': '产品分类表，支持多级分类',
            'ai_description': '产品分类层级结构，支持父子分类关系',
            'tags': ['分类', '主数据'],
            'columns': [
                {'name': 'id', 'type': 'integer', 'pk': True, 'nullable': False, 'desc': '分类唯一标识'},
                {'name': 'name', 'type': 'varchar(100)', 'pk': False, 'nullable': False, 'desc': '分类名称'},
                {'name': 'parent_id', 'type': 'integer', 'pk': False, 'nullable': True, 'desc': '父分类ID'},
                {'name': 'description', 'type': 'text', 'pk': False, 'nullable': True, 'desc': '分类描述'},
                {'name': 'sort_order', 'type': 'integer', 'pk': False, 'nullable': True, 'desc': '排序顺序'},
            ],
        },
    ]

    for table_meta in tables_metadata:
        # Check if table metadata already exists
        existing = await session.execute(
            text("SELECT id FROM metadata_tables WHERE source_id = :sid AND table_name = :tname"),
            {'sid': source_id, 'tname': table_meta['table_name']}
        )
        if existing.scalar_one_or_none():
            continue

        # Get row count
        count_result = await session.execute(
            text(f"SELECT COUNT(*) FROM {table_meta['table_name']}")
        )
        row_count = count_result.scalar_one()

        # Create metadata table
        meta_table = MetadataTable(
            source_id=source_id,
            schema_name='public',
            table_name=table_meta['table_name'],
            description=table_meta['description'],
            ai_description=table_meta['ai_description'],
            tags=table_meta['tags'],
            row_count=row_count,
        )
        session.add(meta_table)
        await session.flush()

        # Create metadata columns
        for idx, col in enumerate(table_meta['columns']):
            meta_col = MetadataColumn(
                table_id=meta_table.id,
                column_name=col['name'],
                data_type=col['type'],
                nullable=col['nullable'],
                is_primary_key=col['pk'],
                description=col['desc'],
                ai_data_category=col.get('category'),
                ordinal_position=idx,
            )
            session.add(meta_col)

    await session.commit()
    print("  Metadata registered successfully")


async def create_collect_tasks(session: AsyncSession, source_id: UUID) -> None:
    """Create data collection tasks."""
    print("  Creating data collection tasks...")

    tasks = [
        {
            'name': '客户数据全量同步',
            'description': '从业务库同步客户主数据到数据仓库',
            'source_table': 'customers',
            'target_table': 'dw_customers',
            'schedule_cron': '0 2 * * *',
            'is_incremental': False,
        },
        {
            'name': '订单数据增量同步',
            'description': '增量同步订单数据，基于updated_at字段',
            'source_table': 'orders',
            'target_table': 'dw_orders',
            'schedule_cron': '0 * * * *',
            'is_incremental': True,
            'incremental_field': 'updated_at',
        },
        {
            'name': '销售汇总数据同步',
            'description': '通过自定义SQL汇总销售数据',
            'source_query': """
                SELECT o.order_date::date as sale_date,
                       c.name as category_name,
                       SUM(oi.subtotal) as total_sales,
                       COUNT(DISTINCT o.id) as order_count
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                JOIN products p ON oi.product_id = p.id
                JOIN categories c ON p.category_id = c.id
                WHERE o.status = 'completed'
                GROUP BY o.order_date::date, c.name
            """,
            'target_table': 'dw_sales_summary',
            'schedule_cron': '0 3 * * *',
            'is_incremental': False,
        },
    ]

    for task_data in tasks:
        # Check if task already exists
        existing = await session.execute(
            text("SELECT id FROM collect_tasks WHERE name = :name"),
            {'name': task_data['name']}
        )
        if existing.scalar_one_or_none():
            continue

        task = CollectTask(
            name=task_data['name'],
            description=task_data['description'],
            source_id=source_id,
            source_table=task_data.get('source_table'),
            source_query=task_data.get('source_query'),
            target_table=task_data['target_table'],
            schedule_cron=task_data.get('schedule_cron'),
            is_active=True,
            is_incremental=task_data.get('is_incremental', False),
            incremental_field=task_data.get('incremental_field'),
            status=CollectTaskStatus.PENDING,
        )
        session.add(task)

    await session.commit()
    print("  Collect tasks created successfully")


async def create_etl_pipelines(session: AsyncSession, source_id: UUID) -> None:
    """Create ETL pipeline configurations."""
    print("  Creating ETL pipelines...")

    pipelines = [
        {
            'name': '销售日报生成管道',
            'description': '从订单数据生成每日销售报表，包含数据清洗、聚合和计算',
            'status': PipelineStatus.ACTIVE,
            'source_type': 'table',
            'source_config': {
                'source_id': str(source_id),
                'table_name': 'orders',
            },
            'target_type': 'table',
            'target_config': {
                'table_name': 'sales_daily_report',
                'if_exists': 'replace',
            },
            'tags': ['daily', 'sales', 'report'],
            'steps': [
                {
                    'name': '过滤已完成订单',
                    'step_type': ETLStepType.FILTER,
                    'order': 1,
                    'config': {'column': 'status', 'operator': 'eq', 'value': 'completed'},
                },
                {
                    'name': '重命名列',
                    'step_type': ETLStepType.RENAME,
                    'order': 2,
                    'config': {'mapping': {'total_amount': 'revenue'}},
                },
                {
                    'name': '按日期聚合',
                    'step_type': ETLStepType.AGGREGATE,
                    'order': 3,
                    'config': {
                        'group_by': ['order_date'],
                        'aggregations': {'revenue': 'sum', 'customer_id': 'nunique', 'id': 'count'},
                    },
                },
                {
                    'name': '按日期排序',
                    'step_type': ETLStepType.SORT,
                    'order': 4,
                    'config': {'columns': ['order_date'], 'ascending': [False]},
                },
            ],
        },
        {
            'name': '客户RFM分析管道',
            'description': '分析客户购买行为，计算RFM指标并分类',
            'status': PipelineStatus.ACTIVE,
            'source_type': 'query',
            'source_config': {
                'source_id': str(source_id),
                'query': """
                    SELECT c.id as customer_id, c.customer_code, c.name as customer_name,
                           c.vip_level, c.city, COUNT(o.id) as total_orders,
                           COALESCE(SUM(o.total_amount), 0) as total_spent,
                           MAX(o.order_date) as last_order_date
                    FROM customers c
                    LEFT JOIN orders o ON c.id = o.customer_id
                    GROUP BY c.id, c.customer_code, c.name, c.vip_level, c.city
                """,
            },
            'target_type': 'table',
            'target_config': {
                'table_name': 'customer_analysis',
                'if_exists': 'replace',
            },
            'tags': ['customer', 'rfm', 'analysis'],
            'steps': [
                {
                    'name': '填充缺失值',
                    'step_type': ETLStepType.FILL_MISSING,
                    'order': 1,
                    'config': {'columns': {'total_orders': 0, 'total_spent': 0}},
                },
                {
                    'name': '计算平均订单金额',
                    'step_type': ETLStepType.CALCULATE,
                    'order': 2,
                    'config': {'new_column': 'avg_order_value', 'expression': 'total_spent / total_orders.replace(0, 1)'},
                },
                {
                    'name': '选择输出列',
                    'step_type': ETLStepType.SELECT_COLUMNS,
                    'order': 3,
                    'config': {
                        'columns': ['customer_id', 'customer_code', 'customer_name', 'vip_level',
                                    'city', 'total_orders', 'total_spent', 'avg_order_value', 'last_order_date'],
                    },
                },
            ],
        },
        {
            'name': '客户数据脱敏管道',
            'description': '对敏感客户数据进行脱敏处理后导出',
            'status': PipelineStatus.ACTIVE,
            'source_type': 'table',
            'source_config': {
                'source_id': str(source_id),
                'table_name': 'customers',
            },
            'target_type': 'table',
            'target_config': {
                'table_name': 'customers_masked',
                'if_exists': 'replace',
            },
            'tags': ['security', 'mask', 'export'],
            'steps': [
                {
                    'name': '手机号脱敏',
                    'step_type': ETLStepType.MASK,
                    'order': 1,
                    'config': {'column': 'phone', 'mask_type': 'partial', 'start': 3, 'end': 7, 'mask_char': '*'},
                },
                {
                    'name': '邮箱脱敏',
                    'step_type': ETLStepType.MASK,
                    'order': 2,
                    'config': {'column': 'email', 'mask_type': 'email'},
                },
                {
                    'name': '删除敏感列',
                    'step_type': ETLStepType.DROP_COLUMNS,
                    'order': 3,
                    'config': {'columns': ['birth_date', 'total_spent']},
                },
                {
                    'name': '选择输出列',
                    'step_type': ETLStepType.SELECT_COLUMNS,
                    'order': 4,
                    'config': {
                        'columns': ['id', 'customer_code', 'name', 'email', 'phone', 'gender',
                                    'city', 'province', 'vip_level', 'is_active'],
                    },
                },
            ],
        },
    ]

    for pipeline_data in pipelines:
        # Check if pipeline already exists
        existing = await session.execute(
            text("SELECT id FROM etl_pipelines WHERE name = :name"),
            {'name': pipeline_data['name']}
        )
        if existing.scalar_one_or_none():
            continue

        steps_data = pipeline_data.pop('steps')

        pipeline = ETLPipeline(
            name=pipeline_data['name'],
            description=pipeline_data['description'],
            status=pipeline_data['status'],
            source_type=pipeline_data['source_type'],
            source_config=pipeline_data['source_config'],
            target_type=pipeline_data['target_type'],
            target_config=pipeline_data['target_config'],
            tags=pipeline_data['tags'],
        )
        session.add(pipeline)
        await session.flush()

        for step_data in steps_data:
            step = ETLStep(
                pipeline_id=pipeline.id,
                name=step_data['name'],
                step_type=step_data['step_type'],
                config=step_data['config'],
                order=step_data['order'],
                is_enabled=True,
            )
            session.add(step)

    await session.commit()
    print("  ETL pipelines created successfully")


async def create_data_assets(session: AsyncSession) -> None:
    """Register data assets."""
    print("  Registering data assets...")

    assets = [
        {
            'name': '电商客户主数据',
            'description': '存储客户基本信息、VIP等级、消费统计等核心客户数据',
            'asset_type': AssetType.TABLE,
            'source_table': 'customers',
            'source_database': 'smart_data',
            'access_level': AccessLevel.RESTRICTED,
            'tags': ['客户', '主数据', 'PII'],
            'category': '主数据',
            'domain': '客户管理',
            'ai_summary': '客户核心数据表，包含个人信息和消费行为统计，需要严格的数据脱敏和访问控制',
            'value_score': 95.0,
            'is_certified': True,
        },
        {
            'name': '电商订单数据',
            'description': '存储订单交易信息，包含订单金额、支付方式、配送状态等',
            'asset_type': AssetType.TABLE,
            'source_table': 'orders',
            'source_database': 'smart_data',
            'access_level': AccessLevel.INTERNAL,
            'tags': ['订单', '交易', '业务数据'],
            'category': '业务数据',
            'domain': '销售管理',
            'ai_summary': '订单交易核心数据，用于销售分析和业务运营',
            'value_score': 90.0,
            'is_certified': True,
        },
        {
            'name': '产品目录数据',
            'description': '产品基础信息，包含价格、库存、分类等',
            'asset_type': AssetType.TABLE,
            'source_table': 'products',
            'source_database': 'smart_data',
            'access_level': AccessLevel.INTERNAL,
            'tags': ['产品', '目录', '库存'],
            'category': '主数据',
            'domain': '产品管理',
            'ai_summary': '产品主数据，包含完整的产品信息和库存状态',
            'value_score': 85.0,
            'is_certified': True,
        },
        {
            'name': '销售日报表',
            'description': '按日汇总的销售数据报表，包含销售额、订单量、客户数等核心指标',
            'asset_type': AssetType.REPORT,
            'source_table': 'sales_daily_report',
            'source_database': 'smart_data',
            'access_level': AccessLevel.PUBLIC,
            'tags': ['销售', '日报', 'KPI'],
            'category': '报表',
            'domain': '销售分析',
            'ai_summary': '每日销售汇总报表，用于追踪销售业绩和趋势分析',
            'value_score': 88.0,
            'is_certified': True,
        },
        {
            'name': '客户分析报告',
            'description': '基于RFM模型的客户分析数据，包含客户分群和价值评估',
            'asset_type': AssetType.REPORT,
            'source_table': 'customer_analysis',
            'source_database': 'smart_data',
            'access_level': AccessLevel.INTERNAL,
            'tags': ['客户', 'RFM', '分析'],
            'category': '报表',
            'domain': '客户分析',
            'ai_summary': '客户价值分析报告，用于精准营销和客户运营',
            'value_score': 92.0,
            'is_certified': True,
        },
        {
            'name': '脱敏客户数据',
            'description': '经过脱敏处理的客户数据，可用于开发测试和数据共享',
            'asset_type': AssetType.TABLE,
            'source_table': 'customers_masked',
            'source_database': 'smart_data',
            'access_level': AccessLevel.PUBLIC,
            'tags': ['客户', '脱敏', '安全'],
            'category': '衍生数据',
            'domain': '数据安全',
            'ai_summary': '安全脱敏后的客户数据，可用于非生产环境',
            'value_score': 70.0,
            'is_certified': False,
        },
    ]

    for asset_data in assets:
        # Check if asset already exists
        existing = await session.execute(
            text("SELECT id FROM data_assets WHERE name = :name"),
            {'name': asset_data['name']}
        )
        if existing.scalar_one_or_none():
            continue

        asset = DataAsset(
            name=asset_data['name'],
            description=asset_data['description'],
            asset_type=asset_data['asset_type'],
            source_table=asset_data['source_table'],
            source_database=asset_data['source_database'],
            access_level=asset_data['access_level'],
            tags=asset_data['tags'],
            category=asset_data['category'],
            domain=asset_data['domain'],
            ai_summary=asset_data['ai_summary'],
            value_score=asset_data['value_score'],
            is_certified=asset_data['is_certified'],
            certified_at=datetime.now() if asset_data['is_certified'] else None,
        )
        session.add(asset)

    await session.commit()
    print("  Data assets registered successfully")


async def print_summary(session: AsyncSession) -> None:
    """Print summary of created data."""
    print("\n" + "=" * 60)
    print("数据初始化汇总")
    print("=" * 60)

    tables = ['categories', 'products', 'customers', 'orders', 'order_items']
    for table in tables:
        result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
        count = result.scalar_one()
        print(f"  {table}: {count:,} 条记录")

    result = await session.execute(text("SELECT COUNT(*) FROM data_sources"))
    print(f"  数据源: {result.scalar_one()} 个")

    result = await session.execute(text("SELECT COUNT(*) FROM metadata_tables"))
    print(f"  元数据表: {result.scalar_one()} 个")

    result = await session.execute(text("SELECT COUNT(*) FROM collect_tasks"))
    print(f"  采集任务: {result.scalar_one()} 个")

    result = await session.execute(text("SELECT COUNT(*) FROM etl_pipelines"))
    print(f"  ETL管道: {result.scalar_one()} 个")

    result = await session.execute(text("SELECT COUNT(*) FROM data_assets"))
    print(f"  数据资产: {result.scalar_one()} 个")

    print("=" * 60)


async def main():
    """Main function: execute complete lifecycle initialization."""
    print("=" * 60)
    print("智能大数据平台 - 电商演示数据初始化")
    print("=" * 60)

    # Ensure platform tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        print("\n[1/8] 创建电商业务表...")
        await create_ecommerce_tables(session)

        print("\n[2/8] 创建产品分类...")
        category_ids = await create_categories(session)

        print("\n[3/8] 创建产品数据...")
        products = await create_products(session, category_ids)

        print("\n[4/8] 创建客户数据...")
        customers = await create_customers(session)

        print("\n[5/8] 创建订单数据...")
        await create_orders(session, len(customers), len(products))

        print("\n[6/8] 配置数据源...")
        pg_source_id = await create_data_source(session)
        await create_csv_data_source(session)

        print("\n[7/8] 扫描元数据并创建采集任务...")
        await scan_metadata(session, pg_source_id)
        await create_collect_tasks(session, pg_source_id)

        print("\n[8/8] 创建ETL管道和数据资产...")
        await create_etl_pipelines(session, pg_source_id)
        await create_data_assets(session)

        await print_summary(session)

        print("\n✅ 初始化完成!")
        print("\n提示:")
        print("  - 启动后端: cd backend && uvicorn app.main:app --reload")
        print("  - 启动前端: cd frontend && npm run dev")
        print("  - 访问: http://localhost:3000")
        print("  - 测试用户: engineer@test.com / engineer_password_123")


if __name__ == "__main__":
    asyncio.run(main())
