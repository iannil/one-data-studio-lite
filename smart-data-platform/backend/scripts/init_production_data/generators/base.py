"""
Base class for data generators.

Provides common functionality for database connections,
batch processing, and progress tracking.
"""

from __future__ import annotations

import hashlib
import random
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Generator, Iterator

from faker import Faker
from sqlalchemy import MetaData, Table, Column, create_engine, insert, text
from sqlalchemy.engine import Engine

from ..config import (
    CHINESE_GIVEN_NAMES,
    CHINESE_SURNAMES,
    GENERATOR_CONFIG,
)


class BaseDataGenerator(ABC):
    """Base class for all data generators."""

    def __init__(
        self,
        connection_string: str,
        batch_size: int = GENERATOR_CONFIG.batch_size,
        seed: int = GENERATOR_CONFIG.seed,
        locale: str = GENERATOR_CONFIG.locale,
    ):
        self.connection_string = connection_string
        self.batch_size = batch_size
        self.seed = seed
        self.locale = locale

        self._engine: Engine | None = None
        self._faker: Faker | None = None

        random.seed(seed)

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = create_engine(
                self.connection_string,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
            )
        return self._engine

    @property
    def faker(self) -> Faker:
        if self._faker is None:
            self._faker = Faker(self.locale)
            Faker.seed(self.seed)
        return self._faker

    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        """Get a database connection."""
        connection = self.engine.connect()
        try:
            yield connection
        finally:
            connection.close()

    @abstractmethod
    def create_schema(self) -> None:
        """Create database schema (tables, indexes, constraints)."""
        pass

    @abstractmethod
    def generate_data(self) -> None:
        """Generate all data for this system."""
        pass

    def run(self) -> None:
        """Run the complete data generation process."""
        start_time = time.time()
        print(f"\n{'=' * 60}")
        print(f"Starting {self.__class__.__name__}")
        print(f"{'=' * 60}")

        print("\n[1/2] Creating schema...")
        self.create_schema()
        print("Schema created successfully.")

        print("\n[2/2] Generating data...")
        self.generate_data()

        elapsed = time.time() - start_time
        print(f"\n{'=' * 60}")
        print(f"{self.__class__.__name__} completed in {elapsed:.2f} seconds")
        print(f"{'=' * 60}\n")

    def execute_sql_file(self, file_path: str) -> None:
        """Execute SQL statements from a file."""
        with open(file_path, encoding="utf-8") as f:
            sql_content = f.read()

        statements = [s.strip() for s in sql_content.split(";") if s.strip()]

        with self.get_connection() as conn:
            for statement in statements:
                if statement:
                    conn.execute(text(statement))
            conn.commit()

    def batch_insert(
        self,
        table_name: str,
        columns: list[str],
        data_iterator: Iterator[tuple[Any, ...]],
        total: int,
        schema: str | None = None,
    ) -> None:
        """Insert data in batches with progress tracking."""
        # Reflect the table from the database to use SQLAlchemy's insert
        metadata = MetaData()
        table = Table(table_name, metadata, autoload_with=self.engine, schema=schema)

        inserted = 0
        batch: list[dict[str, Any]] = []
        start_time = time.time()

        with self.get_connection() as conn:
            for row in data_iterator:
                batch.append(dict(zip(columns, row)))

                if len(batch) >= self.batch_size:
                    conn.execute(insert(table), batch)
                    conn.commit()
                    inserted += len(batch)
                    self._print_progress(table_name, inserted, total, start_time)
                    batch = []

            if batch:
                conn.execute(insert(table), batch)
                conn.commit()
                inserted += len(batch)
                self._print_progress(table_name, inserted, total, start_time)

        print()

    def _print_progress(
        self,
        table_name: str,
        current: int,
        total: int,
        start_time: float,
    ) -> None:
        """Print progress bar."""
        if not GENERATOR_CONFIG.show_progress:
            return

        percent = (current / total) * 100
        elapsed = time.time() - start_time
        rate = current / elapsed if elapsed > 0 else 0
        eta = (total - current) / rate if rate > 0 else 0

        bar_length = 30
        filled = int(bar_length * current / total)
        bar = "█" * filled + "░" * (bar_length - filled)

        print(
            f"\r  {table_name}: [{bar}] {percent:5.1f}% "
            f"({current:,}/{total:,}) "
            f"[{elapsed:.0f}s elapsed, {eta:.0f}s ETA, {rate:.0f} rows/s]",
            end="",
            flush=True,
        )

    # Utility methods for data generation

    def generate_chinese_name(self) -> str:
        """Generate a Chinese name."""
        surname = random.choice(CHINESE_SURNAMES)
        given_name = random.choice(CHINESE_GIVEN_NAMES)
        return surname + given_name

    def generate_phone_number(self) -> str:
        """Generate a Chinese mobile phone number."""
        prefixes = [
            "130", "131", "132", "133", "134", "135", "136", "137", "138", "139",
            "150", "151", "152", "153", "155", "156", "157", "158", "159",
            "180", "181", "182", "183", "184", "185", "186", "187", "188", "189",
        ]
        prefix = random.choice(prefixes)
        suffix = "".join([str(random.randint(0, 9)) for _ in range(8)])
        return prefix + suffix

    def generate_id_card(self) -> str:
        """Generate a Chinese ID card number (masked for privacy)."""
        area_codes = [
            "110101", "310101", "440101", "440301", "330101", "320101",
            "420101", "510101", "500101", "610101", "370101", "350101",
        ]
        area = random.choice(area_codes)

        birth_year = random.randint(1960, 2005)
        birth_month = random.randint(1, 12)
        birth_day = random.randint(1, 28)
        birth_date = f"{birth_year}{birth_month:02d}{birth_day:02d}"

        sequence = random.randint(1, 999)
        gender_digit = random.randint(0, 9)
        seq_str = f"{sequence:03d}{gender_digit}"

        base = area + birth_date + seq_str

        weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        check_chars = "10X98765432"
        total = sum(int(base[i]) * weights[i] for i in range(17))
        check_char = check_chars[total % 11]

        full_id = base + check_char
        return full_id[:6] + "********" + full_id[14:]

    def generate_bank_card(self) -> str:
        """Generate a bank card number (masked for privacy)."""
        prefixes = ["621226", "622202", "622848", "625820", "621700", "622260"]
        prefix = random.choice(prefixes)
        suffix = "".join([str(random.randint(0, 9)) for _ in range(10)])
        full_card = prefix + suffix
        return full_card[:4] + " **** **** " + full_card[12:]

    def generate_email(self, name: str) -> str:
        """Generate an email address based on name."""
        domains = [
            "qq.com", "163.com", "126.com", "sina.com", "sohu.com",
            "gmail.com", "outlook.com", "foxmail.com",
        ]
        pinyin = self._name_to_pinyin(name)
        suffix = random.randint(1, 999)
        domain = random.choice(domains)
        return f"{pinyin}{suffix}@{domain}"

    def _name_to_pinyin(self, name: str) -> str:
        """Simple hash-based pseudo-pinyin generator."""
        return hashlib.md5(name.encode()).hexdigest()[:8]

    def generate_address(self) -> str:
        """Generate a Chinese address."""
        return self.faker.address()

    def generate_random_datetime(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> datetime:
        """Generate a random datetime between two dates."""
        delta = end_date - start_date
        random_seconds = random.randint(0, int(delta.total_seconds()))
        return start_date + timedelta(seconds=random_seconds)

    def generate_amount(
        self,
        min_val: float = 0.01,
        max_val: float = 100000.00,
        decimal_places: int = 2,
    ) -> float:
        """Generate a random monetary amount."""
        amount = random.uniform(min_val, max_val)
        return round(amount, decimal_places)

    def generate_percentage(
        self,
        min_val: float = 0.0,
        max_val: float = 100.0,
        decimal_places: int = 2,
    ) -> float:
        """Generate a random percentage."""
        pct = random.uniform(min_val, max_val)
        return round(pct, decimal_places)

    def generate_uuid(self) -> str:
        """Generate a UUID string."""
        return self.faker.uuid4()

    def generate_ip_address(self) -> str:
        """Generate a random IP address."""
        return self.faker.ipv4()

    def generate_mac_address(self) -> str:
        """Generate a random MAC address."""
        return self.faker.mac_address()

    def generate_coordinates(
        self,
        lat_range: tuple[float, float] = (18.0, 53.0),
        lon_range: tuple[float, float] = (73.0, 135.0),
    ) -> tuple[float, float]:
        """Generate random coordinates (default: China)."""
        lat = random.uniform(*lat_range)
        lon = random.uniform(*lon_range)
        return round(lat, 6), round(lon, 6)
