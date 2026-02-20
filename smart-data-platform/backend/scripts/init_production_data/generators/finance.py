"""
Finance System Data Generator.

Generates production-level test data for the finance schema:
- customers (100,000)
- accounts (200,000)
- transactions (3,000,000)
- portfolios (50,000)
- portfolio_holdings (300,000)
- risk_assessments (100,000)
- audit_logs (1,000,000)
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import text

from .base import BaseDataGenerator
from .. import config
from ..config import (
    BANK_CODES,
    BANK_NAMES,
    CHINESE_CITIES,
    CHINESE_PROVINCES,
    FINANCE_PRODUCTS,
    POSTGRESQL_CONFIG,
    TRANSACTION_TYPES,
)


class FinanceDataGenerator(BaseDataGenerator):
    """Generator for finance system test data."""

    SCHEMA_FILE = Path(__file__).parent.parent / "schemas" / "finance.sql"

    def __init__(self):
        super().__init__(POSTGRESQL_CONFIG.connection_string)
        self.customer_ids: list[int] = []
        self.account_ids: list[int] = []
        self.portfolio_ids: list[int] = []

    def create_schema(self) -> None:
        """Create the finance schema."""
        self.execute_sql_file(str(self.SCHEMA_FILE))

    def generate_data(self) -> None:
        """Generate all finance data."""
        self._generate_customers()
        self._generate_accounts()
        self._generate_transactions()
        self._generate_portfolios()
        self._generate_portfolio_holdings()
        self._generate_risk_assessments()
        self._generate_audit_logs()

    def _generate_customers(self) -> None:
        """Generate customer data."""
        total = config.DATA_VOLUME_CONFIG.finance_customers
        columns = [
            "customer_code", "name", "id_card_encrypted", "phone", "email",
            "address", "city", "province", "postal_code", "customer_type",
            "risk_level", "credit_score", "kyc_status", "kyc_verified_at",
            "total_assets", "total_liabilities", "status", "created_at",
            "updated_at", "created_by"
        ]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            for i in range(total):
                name = self.generate_chinese_name()
                city = random.choice(CHINESE_CITIES)
                province = random.choice(CHINESE_PROVINCES)
                customer_type = random.choices(
                    ["individual", "corporate"],
                    weights=[0.95, 0.05]
                )[0]
                created_at = self.generate_random_datetime(
                    datetime(2020, 1, 1),
                    datetime(2025, 12, 31)
                )
                kyc_status = random.choices(
                    ["pending", "verified", "rejected"],
                    weights=[0.1, 0.85, 0.05]
                )[0]
                kyc_verified_at = created_at + timedelta(days=random.randint(1, 30)) if kyc_status == "verified" else None

                yield (
                    f"CUST{i + 1:08d}",
                    name,
                    self.generate_id_card(),
                    self.generate_phone_number(),
                    self.generate_email(name),
                    self.generate_address(),
                    city,
                    province,
                    f"{random.randint(100000, 999999)}",
                    customer_type,
                    random.randint(1, 5),
                    random.randint(300, 850) if random.random() > 0.1 else None,
                    kyc_status,
                    kyc_verified_at,
                    self.generate_amount(0, 10000000),
                    self.generate_amount(0, 1000000),
                    random.choices(["active", "inactive", "frozen"], weights=[0.9, 0.08, 0.02])[0],
                    created_at,
                    created_at,
                    "system"
                )

        self.batch_insert("customers", columns, data_generator(), total, schema="finance")

        with self.get_connection() as conn:
            result = conn.execute(text("SELECT id FROM finance.customers"))
            self.customer_ids = [row[0] for row in result]

    def _generate_accounts(self) -> None:
        """Generate account data."""
        total = config.DATA_VOLUME_CONFIG.finance_accounts
        columns = [
            "account_number", "customer_id", "account_type", "currency",
            "balance", "available_balance", "frozen_amount", "credit_limit",
            "interest_rate", "last_transaction_at", "overdraft_protection",
            "daily_limit", "monthly_limit", "status", "opened_at", "created_at", "updated_at"
        ]

        account_types = ["checking", "savings", "investment", "credit"]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            for i in range(total):
                customer_id = random.choice(self.customer_ids)
                account_type = random.choice(account_types)
                balance = self.generate_amount(0, 5000000)
                frozen = self.generate_amount(0, balance * 0.1)
                opened_at = self.generate_random_datetime(
                    datetime(2020, 1, 1),
                    datetime(2025, 12, 31)
                )

                yield (
                    f"ACC{i + 1:012d}",
                    customer_id,
                    account_type,
                    "CNY",
                    balance,
                    balance - frozen,
                    frozen,
                    self.generate_amount(10000, 500000) if account_type == "credit" else None,
                    round(random.uniform(0.001, 0.05), 6),
                    self.generate_random_datetime(opened_at, datetime(2026, 2, 18)),
                    random.random() > 0.7,
                    self.generate_amount(10000, 100000),
                    self.generate_amount(100000, 1000000),
                    random.choices(["active", "inactive", "frozen", "closed"], weights=[0.85, 0.08, 0.05, 0.02])[0],
                    opened_at,
                    opened_at,
                    opened_at
                )

        self.batch_insert("accounts", columns, data_generator(), total, schema="finance")

        with self.get_connection() as conn:
            result = conn.execute(text("SELECT id FROM finance.accounts"))
            self.account_ids = [row[0] for row in result]

    def _generate_transactions(self) -> None:
        """Generate transaction data."""
        total = config.DATA_VOLUME_CONFIG.finance_transactions
        columns = [
            "transaction_id", "account_id", "transaction_type", "direction",
            "amount", "balance_before", "balance_after", "currency",
            "counterparty_account", "counterparty_name", "counterparty_bank",
            "channel", "device_id", "ip_address", "location", "description",
            "reference_number", "fee_amount", "status", "risk_score",
            "is_suspicious", "transaction_at", "settled_at", "created_at"
        ]

        channels = ["mobile", "web", "atm", "branch", "api"]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            for i in range(total):
                account_id = random.choice(self.account_ids)
                tx_type = random.choice(TRANSACTION_TYPES)
                direction = "in" if tx_type in ["存款", "转账", "退款", "利息", "红利"] else "out"
                amount = self.generate_amount(1, 100000)
                balance_before = self.generate_amount(0, 1000000)
                balance_after = balance_before + amount if direction == "in" else balance_before - amount
                tx_at = self.generate_random_datetime(
                    datetime(2024, 1, 1),
                    datetime(2026, 2, 18)
                )
                risk_score = random.randint(0, 100)

                yield (
                    f"TX{uuid.uuid4().hex[:24].upper()}",
                    account_id,
                    tx_type,
                    direction,
                    amount,
                    balance_before,
                    max(0, balance_after),
                    "CNY",
                    f"ACC{random.randint(1, 1000000):012d}" if tx_type == "转账" else None,
                    self.generate_chinese_name() if tx_type == "转账" else None,
                    random.choice(BANK_NAMES) if tx_type == "转账" else None,
                    random.choice(channels),
                    uuid.uuid4().hex[:16] if random.random() > 0.3 else None,
                    self.generate_ip_address(),
                    random.choice(CHINESE_CITIES),
                    f"{tx_type} - {self.faker.sentence(nb_words=3)}",
                    f"REF{uuid.uuid4().hex[:12].upper()}",
                    self.generate_amount(0, 50) if tx_type in ["转账", "取款"] else 0,
                    random.choices(["completed", "pending", "failed"], weights=[0.95, 0.03, 0.02])[0],
                    risk_score,
                    risk_score > 80,
                    tx_at,
                    tx_at + timedelta(seconds=random.randint(1, 3600)),
                    tx_at
                )

        self.batch_insert("transactions", columns, data_generator(), total, schema="finance")

    def _generate_portfolios(self) -> None:
        """Generate portfolio data."""
        total = config.DATA_VOLUME_CONFIG.finance_portfolios
        columns = [
            "portfolio_code", "customer_id", "name", "portfolio_type",
            "risk_tolerance", "target_return", "investment_horizon",
            "total_value", "total_cost", "unrealized_pnl", "realized_pnl",
            "annual_return", "benchmark", "rebalance_frequency",
            "last_rebalanced_at", "status", "created_at", "updated_at"
        ]

        portfolio_types = ["conservative", "balanced", "growth", "aggressive"]
        benchmarks = ["沪深300", "中证500", "创业板指", "上证50", "标普500"]
        frequencies = ["daily", "weekly", "monthly", "quarterly"]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            for i in range(total):
                customer_id = random.choice(self.customer_ids)
                ptype = random.choice(portfolio_types)
                total_cost = self.generate_amount(10000, 5000000)
                pnl = self.generate_amount(-total_cost * 0.3, total_cost * 0.5)
                created_at = self.generate_random_datetime(
                    datetime(2021, 1, 1),
                    datetime(2025, 12, 31)
                )

                yield (
                    f"PF{i + 1:08d}",
                    customer_id,
                    f"{ptype.capitalize()} Portfolio {i + 1}",
                    ptype,
                    random.randint(1, 5),
                    self.generate_percentage(3, 15),
                    random.randint(12, 120),
                    total_cost + pnl,
                    total_cost,
                    pnl * 0.6,
                    pnl * 0.4,
                    self.generate_percentage(-20, 30),
                    random.choice(benchmarks),
                    random.choice(frequencies),
                    self.generate_random_datetime(created_at, datetime(2026, 2, 18)),
                    random.choices(["active", "inactive"], weights=[0.9, 0.1])[0],
                    created_at,
                    created_at
                )

        self.batch_insert("portfolios", columns, data_generator(), total, schema="finance")

        with self.get_connection() as conn:
            result = conn.execute(text("SELECT id FROM finance.portfolios"))
            self.portfolio_ids = [row[0] for row in result]

    def _generate_portfolio_holdings(self) -> None:
        """Generate portfolio holdings data."""
        total = config.DATA_VOLUME_CONFIG.finance_portfolio_holdings
        columns = [
            "portfolio_id", "asset_code", "asset_name", "asset_type",
            "quantity", "average_cost", "current_price", "market_value",
            "unrealized_pnl", "weight_percent", "target_weight", "currency",
            "exchange", "sector", "last_price_update", "created_at", "updated_at"
        ]

        asset_types = ["stock", "bond", "fund", "etf", "cash"]
        exchanges = ["SSE", "SZSE", "HKEx", "NYSE", "NASDAQ"]
        sectors = ["金融", "科技", "医疗", "消费", "能源", "材料", "工业", "公用事业"]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            for i in range(total):
                portfolio_id = random.choice(self.portfolio_ids)
                asset_type = random.choice(asset_types)
                quantity = self.generate_amount(10, 10000)
                avg_cost = self.generate_amount(1, 500)
                current_price = avg_cost * random.uniform(0.7, 1.5)
                market_value = quantity * current_price
                cost = quantity * avg_cost
                now = datetime.now()

                yield (
                    portfolio_id,
                    f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=4))}{random.randint(100, 999)}",
                    f"{random.choice(sectors)}{asset_type.capitalize()} {i + 1}",
                    asset_type,
                    quantity,
                    avg_cost,
                    current_price,
                    market_value,
                    market_value - cost,
                    self.generate_percentage(0.1, 30),
                    self.generate_percentage(0.1, 30),
                    "CNY",
                    random.choice(exchanges),
                    random.choice(sectors),
                    self.generate_random_datetime(datetime(2026, 1, 1), now),
                    self.generate_random_datetime(datetime(2023, 1, 1), datetime(2025, 12, 31)),
                    now
                )

        self.batch_insert("portfolio_holdings", columns, data_generator(), total, schema="finance")

    def _generate_risk_assessments(self) -> None:
        """Generate risk assessment data."""
        total = config.DATA_VOLUME_CONFIG.finance_risk_assessments
        columns = [
            "assessment_code", "account_id", "assessment_type", "risk_score",
            "risk_level", "var_1d", "var_10d", "expected_shortfall",
            "stress_test_result", "probability_of_default", "loss_given_default",
            "exposure_at_default", "factors", "recommendations", "assessed_by",
            "reviewed_by", "reviewed_at", "valid_until", "status",
            "created_at", "updated_at"
        ]

        assessment_types = ["credit", "market", "liquidity", "operational"]
        risk_levels = {
            (0, 25): "low",
            (25, 50): "medium",
            (50, 75): "high",
            (75, 101): "critical"
        }

        def get_risk_level(score: int) -> str:
            for (low, high), level in risk_levels.items():
                if low <= score < high:
                    return level
            return "medium"

        def data_generator() -> Iterator[tuple[Any, ...]]:
            for i in range(total):
                account_id = random.choice(self.account_ids)
                risk_score = random.randint(0, 100)
                created_at = self.generate_random_datetime(
                    datetime(2023, 1, 1),
                    datetime(2026, 2, 18)
                )
                exposure = self.generate_amount(10000, 1000000)

                yield (
                    f"RA{i + 1:08d}",
                    account_id,
                    random.choice(assessment_types),
                    risk_score,
                    get_risk_level(risk_score),
                    exposure * random.uniform(0.01, 0.05),
                    exposure * random.uniform(0.02, 0.1),
                    exposure * random.uniform(0.03, 0.15),
                    exposure * random.uniform(-0.2, 0.2),
                    round(random.uniform(0.001, 0.1), 6),
                    round(random.uniform(0.2, 0.8), 4),
                    exposure,
                    json.dumps({"market_volatility": round(random.uniform(0, 1), 2), "credit_spread": round(random.uniform(0, 0.05), 4)}),
                    ["Increase monitoring", "Review credit limits"],
                    f"analyst{random.randint(1, 50)}",
                    f"manager{random.randint(1, 10)}" if random.random() > 0.2 else None,
                    created_at + timedelta(days=random.randint(1, 7)) if random.random() > 0.2 else None,
                    created_at + timedelta(days=90),
                    random.choices(["active", "expired"], weights=[0.8, 0.2])[0],
                    created_at,
                    created_at
                )

        self.batch_insert("risk_assessments", columns, data_generator(), total, schema="finance")

    def _generate_audit_logs(self) -> None:
        """Generate audit log data."""
        total = config.DATA_VOLUME_CONFIG.finance_audit_logs
        columns = [
            "trace_id", "entity_type", "entity_id", "action", "actor_id",
            "actor_type", "actor_ip", "actor_user_agent", "old_values",
            "new_values", "changes", "metadata", "result", "error_message",
            "duration_ms", "created_at"
        ]

        entity_types = ["customer", "account", "transaction", "portfolio"]
        actions = ["create", "update", "delete", "view", "export"]
        actor_types = ["user", "system", "api"]
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
        ]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            for i in range(total):
                entity_type = random.choice(entity_types)
                action = random.choice(actions)
                result = random.choices(["success", "failure"], weights=[0.98, 0.02])[0]

                yield (
                    uuid.uuid4().hex,
                    entity_type,
                    random.randint(1, 100000),
                    action,
                    f"user{random.randint(1, 1000)}" if random.random() > 0.3 else None,
                    random.choice(actor_types),
                    self.generate_ip_address(),
                    random.choice(user_agents),
                    json.dumps({"field": "old_value"}) if action == "update" else None,
                    json.dumps({"field": "new_value"}) if action in ["create", "update"] else None,
                    json.dumps(["field"]) if action == "update" else None,
                    json.dumps({"source": "web", "session_id": uuid.uuid4().hex[:8]}),
                    result,
                    "Permission denied" if result == "failure" else None,
                    random.randint(10, 5000),
                    self.generate_random_datetime(datetime(2024, 1, 1), datetime(2026, 2, 18))
                )

        self.batch_insert("audit_logs", columns, data_generator(), total, schema="finance")
