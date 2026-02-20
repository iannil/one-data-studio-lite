# Backend Scripts

This directory contains utility scripts for data initialization and testing.

## Active Scripts

### Demo Data

| Script | Purpose | Usage |
|--------|---------|-------|
| `init_demo_data.py` | 生成电商演示数据 (产品、客户、订单) | `python init_demo_data.py` |
| `create_admin.py` | 创建管理员用户 | `python create_admin.py` |
| `create_example_pipelines.py` | 创建示例 ETL 管道 | `python create_example_pipelines.py` |

### Production Data

| Script/Folder | Purpose | Usage |
|---------------|---------|-------|
| `init_production_data/` | 生产数据初始化脚本目录 | See directory README |
| `register_production_sources.py` | 注册生产数据源 | `python register_production_sources.py` |
| `test_and_scan_sources.py` | 测试并扫描数据源 | `python test_and_scan_sources.py` |

## Archive

The `archive/` folder contains deprecated or unused scripts that are kept for reference.

## Demo Data Schema

The `init_demo_data.py` script generates the following data:

```
电商演示数据规模:
- 产品分类: 15条
- 产品: 200条
- 客户: 1000条
- 订单: 5000条
- 订单明细: ~12000条
```

数据生命周期:
1. 业务数据 (categories, products, customers, orders)
2. 数据源配置 (PostgreSQL, CSV)
3. 元数据扫描与注册
4. 数据采集任务
5. ETL管道配置
6. 数据资产注册

## Running Scripts

```bash
# From backend directory
cd backend

# Run demo data initialization
python scripts/init_demo_data.py

# Create admin user
python scripts/create_admin.py

# Create example pipelines
python scripts/create_example_pipelines.py
```

## Notes

- Scripts should be run in an activated virtual environment
- Database must be running before executing scripts
- Demo data is intended for development and testing only
