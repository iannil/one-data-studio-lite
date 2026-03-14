"""
Billing Models

Database models for billing, invoices, and payments.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    Numeric,
    Integer,
    Float,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import User


class Tenant(Base):
    """Tenant/Organization for multi-tenancy"""
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    # Plan
    plan: Mapped[str] = mapped_column(String(50), default="free")  # free, basic, professional, enterprise
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Status
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, suspended, cancelled

    # Billing
    billing_email: Mapped[Optional[str]] = mapped_column(String(255))
    billing_address: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    tax_id: Mapped[Optional[str]] = mapped_column(String(100))

    # Settings
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default={})

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=lambda: datetime.utcnow()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=lambda: datetime.utcnow()
    )


class TenantMember(Base):
    """Tenant member relationships"""
    __tablename__ = "tenant_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )

    role: Mapped[str] = mapped_column(String(50))  # owner, admin, member, viewer

    # Invitation
    invited_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    invited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=lambda: datetime.utcnow()
    )


class Subscription(Base):
    """Subscription for a tenant"""
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE")
    )

    # Plan
    plan: Mapped[str] = mapped_column(String(50))
    billing_period: Mapped[str] = mapped_column(String(20))  # monthly, quarterly, yearly

    # Pricing
    base_price: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")

    # Status
    status: Mapped[str] = mapped_column(String(50), default="active")
    trial_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    trial_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Periods
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Payment
    payment_method_id: Mapped[Optional[str]] = mapped_column(String(255))

    # Discounts
    discount_percent: Mapped[float] = mapped_column(Float, default=0.0)
    discount_amount: Mapped[float] = mapped_column(Float, default=0.0)

    # Cancellation
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=lambda: datetime.utcnow()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=lambda: datetime.utcnow()
    )


class PaymentMethod(Base):
    """Payment methods for a tenant"""
    __tablename__ = "payment_methods"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)  # Gateway ID
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE")
    )

    # Type
    type: Mapped[str] = mapped_column(String(50))  # card, bank_account, etc.
    provider: Mapped[str] = mapped_column(String(50))  # stripe, paypal, etc.

    # Card details (tokenized)
    card_last4: Mapped[Optional[str]] = mapped_column(String(4))
    card_brand: Mapped[Optional[str]] = mapped_column(String(50))
    card_exp_month: Mapped[Optional[int]] = mapped_column(Integer)
    card_exp_year: Mapped[Optional[int]] = mapped_column(Integer)

    # Bank details (tokenized)
    bank_name: Mapped[Optional[str]] = mapped_column(String(255))
    bank_last4: Mapped[Optional[str]] = mapped_column(String(4))

    # Status
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Metadata
    metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default={})

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=lambda: datetime.utcnow()
    )


class Invoice(Base):
    """Billing invoices"""
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE")
    )
    subscription_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscriptions.id")
    )

    # Invoice number
    invoice_number: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    # Period
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Amounts
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0)
    tax_rate: Mapped[float] = mapped_column(Float, default=0.0)
    discount_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")

    # Status
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, pending, paid, overdue, cancelled
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Line items (stored as JSON)
    line_items: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)
    memo: Mapped[Optional[str]] = mapped_column(Text)

    # Metadata
    metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default={})

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=lambda: datetime.utcnow()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=lambda: datetime.utcnow()
    )


class InvoiceLineItem(Base):
    """Individual line items for invoices"""
    __tablename__ = "invoice_line_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE")
    )

    # Item details
    description: Mapped[str] = mapped_column(String(500))
    quantity: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(50))
    unit_price: Mapped[float] = mapped_column(Float)
    amount: Mapped[float] = mapped_column(Float)

    # Resource reference
    resource_type: Mapped[Optional[str]] = mapped_column(String(100))
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Metadata
    metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default={})

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=lambda: datetime.utcnow()
    )


class Payment(Base):
    """Payment records"""
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE")
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id")
    )

    # Amount
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="USD")

    # Method
    method: Mapped[str] = mapped_column(String(50))  # card, bank_transfer, etc.
    payment_method_id: Mapped[Optional[str]] = mapped_column(String(255))

    # Gateway
    gateway: Mapped[str] = mapped_column(String(50))  # stripe, paypal, etc.
    gateway_transaction_id: Mapped[Optional[str]] = mapped_column(String(255))
    gateway_response: Mapped[dict[str, Any]] = mapped_column(JSONB, default={})

    # Status
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, processing, completed, failed, refunded

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=lambda: datetime.utcnow()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Refund
    refunded_amount: Mapped[float] = mapped_column(Float, default=0.0)
    refund_reason: Mapped[Optional[str]] = mapped_column(Text)
    refunded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Metadata
    metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default={})


class UsageRecord(Base):
    """Resource usage records for metering"""
    __tablename__ = "usage_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE")
    )

    # Resource
    resource_type: Mapped[str] = mapped_column(String(100), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(50))

    # Cost
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    cost: Mapped[float] = mapped_column(Float, default=0.0)

    # Timestamp
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=lambda: datetime.utcnow(), index=True
    )

    # Source
    source: Mapped[Optional[str]] = mapped_column(String(100))  # api, job, inference, etc.
    source_id: Mapped[Optional[str]] = mapped_column(String(255))  # Reference to source entity

    # Metadata
    metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default={})


class Credit(Base):
    """Credit balance for tenants"""
    __tablename__ = "credits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE")
    )

    # Amount
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="USD")

    # Type
    type: Mapped[str] = mapped_column(String(50))  # promo, refund, bonus, etc.
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Status
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, used, expired

    # Expiration
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Usage
    used_amount: Mapped[float] = mapped_column(Float, default=0.0)

    # Reference
    invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=lambda: datetime.utcnow()
    )


class BillingAlert(Base):
    """Billing alerts and notifications"""
    __tablename__ = "billing_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE")
    )

    # Alert type
    alert_type: Mapped[str] = mapped_column(String(50))  # budget, quota, invoice, etc.
    severity: Mapped[str] = mapped_column(String(20))  # info, warning, critical

    # Message
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)

    # Status
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, acknowledged, resolved

    # Metadata
    metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default={})

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=lambda: datetime.utcnow()
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
