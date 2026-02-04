#!/usr/bin/env python3
"""测试数据生成工具

支持生成以下测试数据:
1. PII敏感数据样本（手机号、身份证、邮箱等）
2. 边界值测试数据（空值、超长字符串、特殊字符等）
3. 大批量订单数据（用于性能测试）
4. 业务模拟数据（符合实际业务场景）

用法:
    python tests/tools/test_data_generator.py --type pii --count 100
    python tests/tools/test_data_generator.py --type boundary --count 50
    python tests/tools/test_data_generator.py --type orders --count 10000
    python tests/tools/test_data_generator.py --type all
"""

import argparse
import json
import random
import string
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# ============================================================
# PII 敏感数据生成器
# ============================================================

class PIIDataGenerator:
    """PII敏感数据生成器

    生成符合中国规范的敏感数据样本:
    - 手机号: 1[3-9]xxxxxxxxx
    - 身份证: 18位，符合校验规则
    - 邮箱: 标准邮箱格式
    - 银行卡: 16-19位数字
    """

    # 常用姓氏
    SURNAMES = [
        '王', '李', '张', '刘', '陈', '杨', '黄', '赵', '吴', '周',
        '徐', '孙', '马', '朱', '胡', '郭', '何', '林', '高', '罗'
    ]

    # 常用名字
    NAMES = [
        '伟', '芳', '娜', '敏', '静', '丽', '强', '磊', '军', '洋',
        '勇', '艳', '杰', '娟', '涛', '明', '超', '秀英', '霞', '平'
    ]

    # 常用邮箱域名
    EMAIL_DOMAINS = [
        'qq.com', '163.com', 'gmail.com', 'outlook.com',
        '126.com', 'sina.com', 'hotmail.com'
    ]

    # 省份代码
    PROVINCE_CODES = [
        '11', '12', '13', '14', '15', '21', '22', '23', '31', '32',
        '33', '34', '35', '36', '37', '41', '42', '43', '44', '45',
        '46', '50', '51', '52', '53', '54', '61', '62', '63', '64', '65'
    ]

    @classmethod
    def generate_phone(cls) -> str:
        """生成中国大陆手机号"""
        prefix = random.choice(['13', '15', '16', '17', '18', '19'])
        suffix = ''.join(random.choices(string.digits, k=9))
        return f'{prefix}{suffix}'

    @classmethod
    def generate_id_card(cls) -> str:
        """生成18位中国居民身份证号（带校验码）"""
        # 地区码
        area_code = random.choice(cls.PROVINCE_CODES)
        # 随机4位地区码
        area_code += f'{random.randint(1, 9999):04d}'

        # 出生年份（1970-2005）
        year = random.randint(1970, 2005)
        month = f'{random.randint(1, 12):02d}'
        day = f'{random.randint(1, 28):02d}'

        # 顺序码（3位，最后一位奇数表示男性，偶数表示女性）
        sequence = f'{random.randint(1, 999):03d}'

        # 前17位
        id_17 = f'{area_code}{year}{month}{day}{sequence}'

        # 计算校验码
        weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        check_codes = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']

        total = 0
        for i in range(17):
            total += int(id_17[i]) * weights[i]

        check_code = check_codes[total % 11]

        return f'{id_17}{check_code}'

    @classmethod
    def generate_email(cls, name: str | None = None) -> str:
        """生成邮箱地址"""
        if name:
            # 基于姓名生成拼音邮箱
            prefix = ''.join([c for c in name if c.isalpha()])
        else:
            prefix = ''.join(random.choices(string.ascii_lowercase, k=random.randint(5, 10)))

        domain = random.choice(cls.EMAIL_DOMAINS)
        number = random.randint(1, 999) if random.random() > 0.7 else ''
        return f'{prefix}{number}@{domain}'

    @classmethod
    def generate_bank_card(cls) -> str:
        """生成银行卡号（16-19位）"""
        length = random.choice([16, 19])
        card = '622'  # 常用银行卡前缀
        card += ''.join(random.choices(string.digits, k=length - 3 - 1))
        # Luhn校验位（简化）
        card += str(random.randint(0, 9))
        return card

    @classmethod
    def generate_name(cls) -> str:
        """生成中文姓名"""
        surname = random.choice(cls.SURNAMES)
        given = random.choice(cls.NAMES)
        # 30%概率双字名
        if random.random() > 0.7:
            given += random.choice(cls.NAMES)
        return f'{surname}{given}'

    @classmethod
    def generate_address(cls) -> str:
        """生成地址"""
        provinces = ['北京', '上海', '广东', '深圳', '杭州', '成都', '武汉', '西安', '南京', '重庆']
        districts = ['朝阳区', '海淀区', '浦东新区', '天河区', '福田区', '滨江区', '高新区']
        streets = ['建设路', '人民路', '解放路', '中山路', '和平路', '长安街']

        province = random.choice(provinces)
        district = random.choice(districts)
        street = random.choice(streets)
        number = random.randint(1, 999)

        return f'{province}{district}{street}{number}号'

    @classmethod
    def generate_pii_sample(cls) -> dict[str, Any]:
        """生成一个完整的PII样本"""
        name = cls.generate_name()
        return {
            'name': name,
            'phone': cls.generate_phone(),
            'id_card': cls.generate_id_card(),
            'email': cls.generate_email(name),
            'bank_card': cls.generate_bank_card(),
            'address': cls.generate_address()
        }

    @classmethod
    def generate_pii_samples(cls, count: int) -> list[dict[str, Any]]:
        """生成多个PII样本"""
        return [cls.generate_pii_sample() for _ in range(count)]


# ============================================================
# 边界值数据生成器
# ============================================================

class BoundaryValueGenerator:
    """边界值测试数据生成器

    生成各种边界条件测试数据:
    - 空值（None, 空字符串）
    - 超长字符串
    - 特殊字符
    - 数值边界
    - 日期边界
    """

    # 特殊字符集
    SPECIAL_CHARS = {
        'sql_injection': [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users--"
        ],
        'xss': [
            '<script>alert("XSS")</script>',
            '<img src=x onerror=alert(1)>',
            'javascript:alert("XSS")',
            '<svg onload=alert(1)>'
        ],
        'path_traversal': [
            '../../../../etc/passwd',
            '..\\..\\..\\..\\windows\\system32',
            '%2e%2e%2f%2e%2e%2f%2e%2e%2f'
        ],
        'unicode': [
            '测试中文🎉',
            'עברית',
            'العربية',
            'مرحبا'
        ]
    }

    @classmethod
    def generate_null_variants(cls) -> list[dict[str, Any]]:
        """生成各种空值变体"""
        return [
            {'value': None, 'type': 'None'},
            {'value': '', 'type': 'empty_string'},
            {'value': ' ', 'type': 'space'},
            {'value': '  ', 'type': 'multiple_spaces'},
            {'value': '\t', 'type': 'tab'},
            {'value': '\n', 'type': 'newline'},
            {'value': '\r\n', 'type': 'crlf'},
            {'value': '   ', 'type': 'only_spaces'},
            {'value': '\u200b', 'type': 'zero_width_space'},
            {'value': '\u0000', 'type': 'null_byte'}
        ]

    @classmethod
    def generate_long_strings(cls) -> list[dict[str, Any]]:
        """生成超长字符串"""
        lengths = [1, 10, 100, 1000, 10000, 100000]
        results = []
        for length in lengths:
            content = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
            results.append({
                'length': length,
                'content': content[:100] + '...' if length > 100 else content,
                'size_bytes': len(content.encode('utf-8'))
            })
        return results

    @classmethod
    def generate_numeric_boundaries(cls) -> list[dict[str, Any]]:
        """生成数值边界"""
        return [
            {'name': 'zero', 'int': 0, 'float': 0.0, 'negative_zero': -0.0},
            {'name': 'tinyint_max', 'int': 127, 'float': 127.0},
            {'name': 'tinyint_min', 'int': -128, 'float': -128.0},
            {'name': 'smallint_max', 'int': 32767, 'float': 32767.0},
            {'name': 'smallint_min', 'int': -32768, 'float': -32768.0},
            {'name': 'int_max', 'int': 2147483647, 'float': 2147483647.0},
            {'name': 'int_min', 'int': -2147483648, 'float': -2147483648.0},
            {'name': 'very_small', 'int': 1, 'float': 0.000001},
            {'name': 'very_large', 'int': 1000000000, 'float': 1e10},
            {'name': 'negative', 'int': -1, 'float': -0.01}
        ]

    @classmethod
    def generate_date_boundaries(cls) -> list[dict[str, Any]]:
        """生成日期边界"""
        return [
            {'name': 'min_date', 'date': '0001-01-01', 'timestamp': '0001-01-01 00:00:00'},
            {'name': 'max_date', 'date': '9999-12-31', 'timestamp': '9999-12-31 23:59:59'},
            {'name': 'epoch', 'date': '1970-01-01', 'timestamp': '1970-01-01 00:00:00'},
            {'name': 'y2k', 'date': '2000-01-01', 'timestamp': '2000-01-01 00:00:00'},
            {'name': 'leap_year', 'date': '2020-02-29', 'timestamp': '2020-02-29 12:00:00'},
            {'name': 'leap_century', 'date': '2000-02-29', 'timestamp': '2000-02-29 23:59:59'},
            {'name': 'non_leap_century', 'date': '1900-03-01', 'timestamp': '1900-03-01 00:00:00'}
        ]

    @classmethod
    def generate_special_chars(cls) -> list[dict[str, Any]]:
        """生成特殊字符"""
        results = []
        for category, chars in cls.SPECIAL_CHARS.items():
            for char in chars:
                results.append({
                    'category': category,
                    'value': char
                })
        return results

    @classmethod
    def generate_boundary_samples(cls, count: int) -> list[dict[str, Any]]:
        """生成混合边界样本"""
        samples = []

        # 空值样本
        for _ in range(max(1, count // 10)):
            sample = {
                'type': 'null_variant',
                'id': random.randint(1, 100000),
                'name': random.choice(['Normal', None, '']),
                'email': random.choice(['test@example.com', None, '']),
                'phone': random.choice([PIIDataGenerator.generate_phone(), None, ''])
            }
            samples.append(sample)

        # 特殊字符样本
        for _ in range(max(1, count // 10)):
            char_sample = random.choice(cls.generate_special_chars())
            sample = {
                'type': 'special_char',
                'category': char_sample['category'],
                'value': char_sample['value']
            }
            samples.append(sample)

        # 边界数值样本
        for boundary in cls.generate_numeric_boundaries():
            sample = {
                'type': 'numeric_boundary',
                'name': boundary['name'],
                'int_value': boundary['int'],
                'float_value': boundary['float']
            }
            samples.append(sample)

        # 填充常规数据
        while len(samples) < count:
            sample = {
                'type': 'normal',
                'id': random.randint(1, 100000),
                'value': random.randint(1, 1000),
                'score': random.uniform(0, 100)
            }
            samples.append(sample)

        return samples[:count]


# ============================================================
# 订单数据生成器
# ============================================================

class OrderDataGenerator:
    """订单数据生成器

    生成符合业务场景的订单数据:
    - 订单基本信息
    - 订单状态流转
    - 不同金额区间
    - 不同时间分布
    """

    # 商品列表
    PRODUCTS = [
        {'id': 1, 'name': 'iPhone 15 Pro', 'category': '手机', 'price': 7999},
        {'id': 2, 'name': 'MacBook Pro', 'category': '电脑', 'price': 14999},
        {'id': 3, 'name': 'AirPods Pro', 'category': '耳机', 'price': 1899},
        {'id': 4, 'name': 'iPad Air', 'category': '平板', 'price': 4799},
        {'id': 5, 'name': 'Apple Watch', 'category': '手表', 'price': 2999},
        {'id': 6, 'name': '小米14', 'category': '手机', 'price': 3999},
        {'id': 7, 'name': '华为Mate60', 'category': '手机', 'price': 5999},
        {'id': 8, 'name': '戴尔显示器', 'category': '显示器', 'price': 1299},
        {'id': 9, 'name': '罗技鼠标', 'category': '配件', 'price': 99},
        {'id': 10, 'name': '机械键盘', 'category': '配件', 'price': 299}
    ]

    # 订单状态
    ORDER_STATUSES = [
        'pending',      # 待支付
        'paid',         # 已支付
        'shipped',      # 已发货
        'completed',    # 已完成
        'cancelled',    # 已取消
        'refunded'      # 已退款
    ]

    @classmethod
    def generate_order(cls, user_id_range: tuple = (1, 1000)) -> dict[str, Any]:
        """生成单个订单"""
        order_id = random.randint(100000, 999999)
        user_id = random.randint(*user_id_range)
        product = random.choice(cls.PRODUCTS)

        # 生成订单号
        order_no = f'ORD{datetime.now().strftime("%Y%m%d")}{order_id}'

        # 确定订单状态（带概率分布）
        status_weights = [0.05, 0.1, 0.15, 0.5, 0.15, 0.05]  # completed最高概率
        status = random.choices(cls.ORDER_STATUSES, weights=status_weights)[0]

        # 数量（1-5件）
        quantity = random.randint(1, 5)

        # 计算金额
        unit_price = product['price']
        total_amount = unit_price * quantity

        # 随机折扣
        if random.random() > 0.7:
            discount_rate = random.choice([0.1, 0.15, 0.2, 0.3])
            discount_amount = total_amount * discount_rate
            pay_amount = total_amount - discount_amount
        else:
            discount_amount = 0
            pay_amount = total_amount

        # 生成时间（最近30天内）
        days_ago = random.randint(0, 30)
        order_time = datetime.now() - timedelta(days=days_ago)

        # 根据状态设置相关时间
        pay_time = None
        ship_time = None
        complete_time = None

        if status in ['paid', 'shipped', 'completed']:
            pay_time = order_time + timedelta(minutes=random.randint(5, 60))
        if status in ['shipped', 'completed']:
            ship_time = pay_time + timedelta(hours=random.randint(1, 48))
        if status == 'completed':
            complete_time = ship_time + timedelta(days=random.randint(1, 7))

        return {
            'order_id': order_id,
            'order_no': order_no,
            'user_id': user_id,
            'product_id': product['id'],
            'product_name': product['name'],
            'category': product['category'],
            'quantity': quantity,
            'unit_price': unit_price,
            'total_amount': round(total_amount, 2),
            'discount_amount': round(discount_amount, 2),
            'pay_amount': round(pay_amount, 2),
            'status': status,
            'order_time': order_time.strftime('%Y-%m-%d %H:%M:%S'),
            'pay_time': pay_time.strftime('%Y-%m-%d %H:%M:%S') if pay_time else None,
            'ship_time': ship_time.strftime('%Y-%m-%d %H:%M:%S') if ship_time else None,
            'complete_time': complete_time.strftime('%Y-%m-%d %H:%M:%S') if complete_time else None
        }

    @classmethod
    def generate_orders(cls, count: int, user_id_range: tuple = (1, 1000)) -> list[dict[str, Any]]:
        """生成多个订单"""
        return [cls.generate_order(user_id_range) for _ in range(count)]

    @classmethod
    def generate_orders_sql(cls, count: int, table_name: str = 'test_orders') -> str:
        """生成订单插入SQL"""
        orders = cls.generate_orders(count)

        sql_lines = [f'-- 生成 {count} 条订单测试数据']
        sql_lines.append(f'INSERT INTO {table_name} (order_id, order_no, user_id, product_id, quantity,')
        sql_lines.append('unit_price, total_amount, discount_amount, pay_amount, status,')
        sql_lines.append('order_time, pay_time, ship_time, complete_time) VALUES')

        values = []
        for order in orders:
            value = f"({order['order_id']}, '{order['order_no']}', {order['user_id']}, {order['product_id']},"
            value += f"{order['quantity']}, {order['unit_price']}, {order['total_amount']},"
            value += f"{order['discount_amount']}, {order['pay_amount']}, '{order['status']}',"
            value += f"'{order['order_time']}',"
            value += f"'{order['pay_time']}'" if order['pay_time'] else 'NULL'
            value += f", '{order['ship_time']}'" if order['ship_time'] else ', NULL'
            value += f", '{order['complete_time']}'" if order['complete_time'] else ', NULL'
            value += ')'
            values.append(value)

        sql_lines.append(',\n'.join(values) + ';')
        return '\n'.join(sql_lines)


# ============================================================
# 业务模拟数据生成器
# ============================================================

class BusinessDataGenerator:
    """业务模拟数据生成器

    生成符合实际业务场景的测试数据:
    - 用户画像
    - 商品分类
    - 营销活动
    - 行为日志
    """

    @classmethod
    def generate_user_profile(cls, user_id: int) -> dict[str, Any]:
        """生成用户画像"""
        # 用户等级（基于消费金额）
        levels = [
            ('bronze', '青铜会员', 0, 1000),
            ('silver', '白银会员', 1000, 5000),
            ('gold', '黄金会员', 5000, 20000),
            ('platinum', '铂金会员', 20000, 50000),
            ('diamond', '钻石会员', 50000, float('inf'))
        ]

        # 随机选择等级
        level_data = random.choices(levels, weights=[0.4, 0.3, 0.15, 0.1, 0.05])[0]

        # 兴趣标签
        all_tags = ['数码', '美妆', '服饰', '食品', '运动', '阅读', '游戏', '旅游', '母婴', '汽车']
        selected_tags = random.sample(all_tags, k=random.randint(1, 4))

        return {
            'user_id': user_id,
            'level_code': level_data[0],
            'level_name': level_data[1],
            'tags': selected_tags,
            'register_days': random.randint(1, 1095),  # 1-3年
            'login_days': random.randint(1, 365),
            'total_orders': random.randint(0, 200),
            'total_spent': round(random.uniform(0, 100000), 2),
            'avg_order_amount': round(random.uniform(50, 2000), 2),
            'last_login_days': random.randint(0, 90)
        }

    @classmethod
    def generate_behavior_event(cls, user_id: int | None = None) -> dict[str, Any]:
        """生成用户行为事件"""
        event_types = [
            'page_view', 'click', 'add_cart', 'remove_cart',
            'search', 'favorite', 'share', 'login', 'logout'
        ]

        pages = [
            '/home', '/product/list', '/product/detail', '/cart',
            '/user/profile', '/search', '/category/electronics',
            '/category/clothing', '/checkout'
        ]

        return {
            'event_id': f'evt_{random.randint(1000000, 9999999)}',
            'user_id': user_id or random.randint(1, 10000),
            'event_type': random.choice(event_types),
            'page_url': random.choice(pages),
            'referrer': random.choice([None, 'https://www.google.com', 'https://www.baidu.com', '']),
            'user_agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)'
            ]),
            'ip_address': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
            'event_time': (datetime.now() - timedelta(seconds=random.randint(0, 86400))).strftime('%Y-%m-%d %H:%M:%S')
        }

    @classmethod
    def generate_behavior_events(cls, count: int) -> list[dict[str, Any]]:
        """生成多个行为事件"""
        return [cls.generate_behavior_event() for _ in range(count)]


# ============================================================
# 主程序
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='测试数据生成工具')
    parser.add_argument('--type', '-t', choices=['pii', 'boundary', 'orders', 'behavior', 'all'],
                        default='all', help='数据类型')
    parser.add_argument('--count', '-c', type=int, default=100, help='生成数量')
    parser.add_argument('--output', '-o', help='输出文件路径')
    parser.add_argument('--format', '-f', choices=['json', 'sql', 'csv'], default='json',
                        help='输出格式')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')

    args = parser.parse_args()

    # 默认输出目录
    if not args.output:
        output_dir = Path(__file__).parent.parent / 'test_data' / 'generated'
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = output_dir / f'test_data_{args.type}_{timestamp}.{args.format}'

    results = {}

    # 生成数据
    if args.type in ['pii', 'all']:
        print(f"生成 {args.count} 条 PII 数据...")
        results['pii'] = PIIDataGenerator.generate_pii_samples(args.count)

    if args.type in ['boundary', 'all']:
        print(f"生成 {args.count} 条边界值数据...")
        results['boundary'] = BoundaryValueGenerator.generate_boundary_samples(args.count)

    if args.type in ['orders', 'all']:
        print(f"生成 {args.count} 条订单数据...")
        results['orders'] = OrderDataGenerator.generate_orders(args.count)

    if args.type in ['behavior', 'all']:
        print(f"生成 {args.count} 条行为数据...")
        results['behavior'] = BusinessDataGenerator.generate_behavior_events(args.count)

    # 输出数据
    if args.format == 'json':
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    elif args.format == 'sql':
        with open(args.output, 'w', encoding='utf-8') as f:
            if 'orders' in results:
                f.write(OrderDataGenerator.generate_orders_sql(len(results['orders'])))
            else:
                f.write('-- SQL 输出暂仅支持订单数据\n')
    elif args.format == 'csv':
        import csv
        with open(args.output, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            for key, data in results.items():
                if data:
                    writer.writerow([f'# {key}'])
                    if isinstance(data[0], dict):
                        writer.writerow(data[0].keys())
                        for item in data:
                            writer.writerow(item.values())
                    writer.writerow([])

    print(f"数据已生成并保存到: {args.output}")
    print(f"总计: {sum(len(v) for v in results.values())} 条记录")


if __name__ == '__main__':
    main()
