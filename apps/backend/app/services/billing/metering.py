"""
Resource Metering Service

Tracks resource usage for billing and quota enforcement.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class ResourceType(str, Enum):
    """Types of resources that can be metered"""

    # Compute resources
    CPU_HOUR = "cpu_hour"
    GPU_HOUR = "gpu_hour"
    MEMORY_GB_HOUR = "memory_gb_hour"

    # Storage
    STORAGE_GB_MONTH = "storage_gb_month"
    MODEL_STORAGE_GB = "model_storage_gb"
    DATA_STORAGE_GB = "data_storage_gb"

    # API calls
    API_REQUEST = "api_request"
    INFERENCE_REQUEST = "inference_request"
    EMBEDDING_REQUEST = "embedding_request"

    # ML resources
    TRAINING_JOB_HOUR = "training_job_hour"
    EXPERIMENT_RUN = "experiment_run"

    # Network
    NETWORK_EGRESS_GB = "network_egress_gb"

    # Annotation
    ANNOTATION_TASK = "annotation_task"
    ANNOTATION_AUTO_HOUR = "annotation_auto_hour"


class MeteringUnit(str, Enum):
    """Units for metering"""

    HOUR = "hour"
    GB = "gb"
    GB_MONTH = "gb_month"
    COUNT = "count"
    REQUEST = "request"


@dataclass
class ResourcePrice:
    """Pricing for a resource type"""

    resource_type: ResourceType
    unit: MeteringUnit
    unit_price: float  # Price per unit in USD
    free_tier allowance: int = 0  # Free allowance per billing period


# Pricing tiers
PRICING_PLANS: Dict[str, Dict[ResourceType, ResourcePrice]] = {
    "free": {
        ResourceType.CPU_HOUR: ResourcePrice(
            resource_type=ResourceType.CPU_HOUR,
            unit=MeteringUnit.HOUR,
            unit_price=0.0,
            free_allowance=100,  # 100 CPU hours free
        ),
        ResourceType.API_REQUEST: ResourcePrice(
            resource_type=ResourceType.API_REQUEST,
            unit=MeteringUnit.REQUEST,
            unit_price=0.0001,  # $0.0001 per request over free tier
            free_allowance=10000,  # 10K requests free
        ),
        ResourceType.STORAGE_GB_MONTH: ResourcePrice(
            resource_type=ResourceType.STORAGE_GB_MONTH,
            unit=MeteringUnit.GB_MONTH,
            unit_price=0.10,  # $0.10 per GB/month over free tier
            free_allowance=10,  # 10 GB free
        ),
    },
    "basic": {
        ResourceType.CPU_HOUR: ResourcePrice(
            resource_type=ResourceType.CPU_HOUR,
            unit=MeteringUnit.HOUR,
            unit_price=0.05,  # $0.05 per CPU hour
            free_allowance=500,
        ),
        ResourceType.GPU_HOUR: ResourcePrice(
            resource_type=ResourceType.GPU_HOUR,
            unit=MeteringUnit.HOUR,
            unit_price=0.50,  # $0.50 per GPU hour
            free_allowance=10,
        ),
        ResourceType.API_REQUEST: ResourcePrice(
            resource_type=ResourceType.API_REQUEST,
            unit=MeteringUnit.REQUEST,
            unit_price=0.00005,
            free_allowance=100000,
        ),
        ResourceType.STORAGE_GB_MONTH: ResourcePrice(
            resource_type=ResourceType.STORAGE_GB_MONTH,
            unit=MeteringUnit.GB_MONTH,
            unit_price=0.08,
            free_allowance=100,
        ),
        ResourceType.INFERENCE_REQUEST: ResourcePrice(
            resource_type=ResourceType.INFERENCE_REQUEST,
            unit=MeteringUnit.REQUEST,
            unit_price=0.001,
            free_allowance=1000,
        ),
    },
    "professional": {
        ResourceType.CPU_HOUR: ResourcePrice(
            resource_type=ResourceType.CPU_HOUR,
            unit=MeteringUnit.HOUR,
            unit_price=0.04,
            free_allowance=2000,
        ),
        ResourceType.GPU_HOUR: ResourcePrice(
            resource_type=ResourceType.GPU_HOUR,
            unit=MeteringUnit.HOUR,
            unit_price=0.40,
            free_allowance=100,
        ),
        ResourceType.API_REQUEST: ResourcePrice(
            resource_type=ResourceType.API_REQUEST,
            unit=MeteringUnit.REQUEST,
            unit_price=0.00002,
            free_allowance=1000000,
        ),
        ResourceType.STORAGE_GB_MONTH: ResourcePrice(
            resource_type=ResourceType.STORAGE_GB_MONTH,
            unit=MeteringUnit.GB_MONTH,
            unit_price=0.05,
            free_allowance=500,
        ),
        ResourceType.INFERENCE_REQUEST: ResourcePrice(
            resource_type=ResourceType.INFERENCE_REQUEST,
            unit=MeteringUnit.REQUEST,
            unit_price=0.0005,
            free_allowance=10000,
        ),
        ResourceType.TRAINING_JOB_HOUR: ResourcePrice(
            resource_type=ResourceType.TRAINING_JOB_HOUR,
            unit=MeteringUnit.HOUR,
            unit_price=0.10,
            free_allowance=50,
        ),
    },
    "enterprise": {
        ResourceType.CPU_HOUR: ResourcePrice(
            resource_type=ResourceType.CPU_HOUR,
            unit=MeteringUnit.HOUR,
            unit_price=0.03,
            free_allowance=10000,
        ),
        ResourceType.GPU_HOUR: ResourcePrice(
            resource_type=ResourceType.GPU_HOUR,
            unit=MeteringUnit.HOUR,
            unit_price=0.30,
            free_allowance=1000,
        ),
        ResourceType.API_REQUEST: ResourcePrice(
            resource_type=ResourceType.API_REQUEST,
            unit=MeteringUnit.REQUEST,
            unit_price=0.00001,
            free_allowance=10000000,
        ),
        ResourceType.STORAGE_GB_MONTH: ResourcePrice(
            resource_type=ResourceType.STORAGE_GB_MONTH,
            unit=MeteringUnit.GB_MONTH,
            unit_price=0.03,
            free_allowance=2000,
        ),
        ResourceType.INFERENCE_REQUEST: ResourcePrice(
            resource_type=ResourceType.INFERENCE_REQUEST,
            unit=MeteringUnit.REQUEST,
            unit_price=0.0002,
            free_allowance=100000,
        ),
        ResourceType.TRAINING_JOB_HOUR: ResourcePrice(
            resource_type=ResourceType.TRAINING_JOB_HOUR,
            unit=MeteringUnit.HOUR,
            unit_price=0.08,
            free_allowance=500,
        ),
        ResourceType.NETWORK_EGRESS_GB: ResourcePrice(
            resource_type=ResourceType.NETWORK_EGRESS_GB,
            unit=MeteringUnit.GB,
            unit_price=0.05,
            free_allowance=1000,
        ),
    },
}


@dataclass
class UsageRecord:
    """A single usage record"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    resource_type: ResourceType = ResourceType.API_REQUEST
    amount: float = 0.0
    unit: MeteringUnit = MeteringUnit.COUNT
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Cost calculation
    plan: str = "free"
    unit_price: float = 0.0
    cost: float = 0.0

    def calculate_cost(self, plan: str, pricing: Dict[ResourceType, ResourcePrice]):
        """Calculate cost for this usage record"""
        price_info = pricing.get(self.resource_type)
        if not price_info:
            self.cost = 0.0
            return

        self.plan = plan
        self.unit_price = price_info.unit_price
        self.cost = self.amount * price_info.unit_price


@dataclass
class UsageSummary:
    """Summary of usage over a period"""

    tenant_id: str
    period_start: datetime
    period_end: datetime
    plan: str

    # Usage by resource type
    usage: Dict[ResourceType, float] = field(default_factory=dict)

    # Costs
    total_cost: float = 0.0
    breakdown: Dict[ResourceType, float] = field(default_factory=dict)

    # Free tier usage
    free_tier_used: Dict[ResourceType, float] = field(default_factory=dict)
    free_tier_remaining: Dict[ResourceType, float] = field(default_factory=dict)


class MeteringService:
    """
    Service for tracking resource usage.
    """

    def __init__(self):
        # In production, store in database or time-series DB
        self.usage_records: Dict[str, List[UsageRecord]] = {}
        # Aggregate counters for real-time tracking
        self.current_usage: Dict[str, Dict[ResourceType, float]] = {}

    def record_usage(
        self,
        tenant_id: str,
        resource_type: ResourceType,
        amount: float,
        unit: MeteringUnit = MeteringUnit.COUNT,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UsageRecord:
        """
        Record a usage event.

        Args:
            tenant_id: Tenant ID
            resource_type: Type of resource used
            amount: Amount used
            unit: Unit of measurement
            metadata: Additional metadata

        Returns:
            UsageRecord
        """
        record = UsageRecord(
            tenant_id=tenant_id,
            resource_type=resource_type,
            amount=amount,
            unit=unit,
            metadata=metadata or {},
        )

        # Add to records
        if tenant_id not in self.usage_records:
            self.usage_records[tenant_id] = []
        self.usage_records[tenant_id].append(record)

        # Update current usage
        if tenant_id not in self.current_usage:
            self.current_usage[tenant_id] = {}
        if resource_type not in self.current_usage[tenant_id]:
            self.current_usage[tenant_id][resource_type] = 0.0
        self.current_usage[tenant_id][resource_type] += amount

        return record

    def get_usage(
        self,
        tenant_id: str,
        resource_type: Optional[ResourceType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[UsageRecord]:
        """
        Get usage records for a tenant.

        Args:
            tenant_id: Tenant ID
            resource_type: Filter by resource type
            start_time: Start of time range
            end_time: End of time range

        Returns:
            List of usage records
        """
        records = self.usage_records.get(tenant_id, [])

        if resource_type:
            records = [r for r in records if r.resource_type == resource_type]

        if start_time:
            records = [r for r in records if r.timestamp >= start_time]

        if end_time:
            records = [r for r in records if r.timestamp <= end_time]

        return records

    def get_usage_summary(
        self,
        tenant_id: str,
        start_time: datetime,
        end_time: datetime,
        plan: str = "free",
    ) -> UsageSummary:
        """
        Get usage summary for a billing period.

        Args:
            tenant_id: Tenant ID
            start_time: Period start
            end_time: Period end
            plan: Tenant plan

        Returns:
            UsageSummary
        """
        records = self.get_usage(tenant_id, start_time=start_time, end_time=end_time)
        pricing = PRICING_PLANS.get(plan, PRICING_PLANS["free"])

        summary = UsageSummary(
            tenant_id=tenant_id,
            period_start=start_time,
            period_end=end_time,
            plan=plan,
        )

        # Aggregate by resource type
        for record in records:
            rt = record.resource_type
            if rt not in summary.usage:
                summary.usage[rt] = 0.0
            summary.usage[rt] += record.amount

        # Calculate costs
        for rt, amount in summary.usage.items():
            price_info = pricing.get(rt)
            if price_info:
                # Calculate free tier usage
                free_used = min(amount, price_info.free_allowance)
                billable = max(0, amount - price_info.free_allowance)
                cost = billable * price_info.unit_price

                summary.free_tier_used[rt] = free_used
                summary.free_tier_remaining[rt] = max(0, price_info.free_allowance - free_used)
                summary.breakdown[rt] = cost
                summary.total_cost += cost

        return summary

    def get_current_usage(
        self, tenant_id: str, resource_type: Optional[ResourceType] = None
    ) -> Dict[str, float]:
        """
        Get current usage counter for a tenant.

        Args:
            tenant_id: Tenant ID
            resource_type: Filter by resource type

        Returns:
            Dict of resource type to usage amount
        """
        usage = self.current_usage.get(tenant_id, {})

        if resource_type:
            return {resource_type.value: usage.get(resource_type, 0.0)}

        return {rt.value: amount for rt, amount in usage.items()}

    def reset_period_usage(self, tenant_id: str, period_start: datetime):
        """
        Reset usage counters for a new billing period.
        Archives old records.

        Args:
            tenant_id: Tenant ID
            period_start: Start of new period
        """
        # In production, archive records before this date
        old_records = [
            r for r in self.usage_records.get(tenant_id, []) if r.timestamp < period_start
        ]

        # Keep only records in current period
        self.usage_records[tenant_id] = [
            r for r in self.usage_records.get(tenant_id, []) if r.timestamp >= period_start
        ]

        return len(old_records)

    async def check_quota_limit(
        self,
        tenant_id: str,
        resource_type: ResourceType,
        requested_amount: float,
        quota_limit: float,
    ) -> tuple[bool, str]:
        """
        Check if a request is within quota limits.

        Args:
            tenant_id: Tenant ID
            resource_type: Resource type
            requested_amount: Amount being requested
            quota_limit: Maximum allowed

        Returns:
            Tuple of (allowed, error_message)
        """
        current = self.current_usage.get(tenant_id, {}).get(resource_type, 0.0)

        if current + requested_amount > quota_limit:
            return False, f"Quota exceeded for {resource_type.value}: {current}/{quota_limit}"

        return True, ""

    def get_top_consumers(
        self, resource_type: ResourceType, limit: int = 10
    ) -> List[tuple[str, float]]:
        """
        Get top consumers of a resource.

        Args:
            resource_type: Resource type
            limit: Number of results

        Returns:
            List of (tenant_id, usage) tuples
        """
        consumers = []

        for tenant_id, usage in self.current_usage.items():
            amount = usage.get(resource_type, 0.0)
            if amount > 0:
                consumers.append((tenant_id, amount))

        consumers.sort(key=lambda x: x[1], reverse=True)
        return consumers[:limit]


# Global service instance
metering_service = MeteringService()
