"""
Billing and Invoice Service

Handles invoice generation, payment processing, and billing management.
"""

import uuid
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.billing.metering import (
    metering_service,
    ResourceType,
    MeteringUnit,
    UsageSummary,
    PRICING_PLANS,
)


class BillingPeriod(str, Enum):
    """Billing period types"""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class InvoiceStatus(str, Enum):
    """Invoice status"""

    DRAFT = "draft"
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    """Payment methods"""

    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    ALIPAY = "alipay"
    WECHAT_PAY = "wechat_pay"
    INVOICE = "invoice"  # For enterprise customers


class PaymentStatus(str, Enum):
    """Payment status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


@dataclass
class LineItem:
    """Invoice line item"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    resource_type: Optional[ResourceType] = None
    quantity: float = 0.0
    unit: str = ""
    unit_price: float = 0.0
    amount: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Invoice:
    """Billing invoice"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    invoice_number: str = ""

    # Period
    period_start: datetime = field(default_factory=datetime.utcnow)
    period_end: datetime = field(default_factory=datetime.utcnow)
    billing_period: BillingPeriod = BillingPeriod.MONTHLY

    # Amounts
    subtotal: float = 0.0
    tax_amount: float = 0.0
    tax_rate: float = 0.0  # Tax rate as percentage (e.g., 10.0 for 10%)
    discount_amount: float = 0.0
    total: float = 0.0

    # Status
    status: InvoiceStatus = InvoiceStatus.DRAFT
    due_date: Optional[datetime] = None

    # Line items
    line_items: List[LineItem] = field(default_factory=list)

    # Usage summary
    usage_summary: Optional[UsageSummary] = None

    # Payment
    payment_method: Optional[PaymentMethod] = None
    payment_id: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def calculate_total(self):
        """Calculate invoice total"""
        self.subtotal = sum(item.amount for item in self.line_items)
        self.tax_amount = self.subtotal * (self.tax_rate / 100)
        self.total = self.subtotal + self.tax_amount - self.discount_amount

    def add_line_item(
        self,
        description: str,
        quantity: float,
        unit_price: float,
        unit: str = "",
        resource_type: Optional[ResourceType] = None,
    ):
        """Add a line item to the invoice"""
        item = LineItem(
            description=description,
            resource_type=resource_type,
            quantity=quantity,
            unit=unit,
            unit_price=unit_price,
            amount=quantity * unit_price,
        )
        self.line_items.append(item)
        self.calculate_total()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "invoice_number": self.invoice_number,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "billing_period": self.billing_period.value,
            "subtotal": round(self.subtotal, 2),
            "tax_amount": round(self.tax_amount, 2),
            "tax_rate": self.tax_rate,
            "discount_amount": round(self.discount_amount, 2),
            "total": round(self.total, 2),
            "status": self.status.value,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "line_items": [
                {
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit": item.unit,
                    "unit_price": round(item.unit_price, 4),
                    "amount": round(item.amount, 2),
                }
                for item in self.line_items
            ],
            "payment_method": self.payment_method.value if self.payment_method else None,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Payment:
    """Payment record"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    invoice_id: str = ""
    tenant_id: str = ""

    amount: float = 0.0
    currency: str = "USD"
    method: PaymentMethod = PaymentMethod.CREDIT_CARD

    status: PaymentStatus = PaymentStatus.PENDING

    # Payment gateway details
    gateway: str = ""  # stripe, paypal, etc.
    gateway_transaction_id: str = ""
    gateway_response: Dict[str, Any] = field(default_factory=dict)

    # Card details (stored tokenized)
    card_last4: str = ""
    card_brand: str = ""

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None

    # Refund
    refunded_amount: float = 0.0
    refund_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "invoice_id": self.invoice_id,
            "amount": round(self.amount, 2),
            "currency": self.currency,
            "method": self.method.value,
            "status": self.status.value,
            "card_last4": self.card_last4,
            "card_brand": self.card_brand,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "refunded_amount": round(self.refunded_amount, 2),
        }


@dataclass
class BillingSubscription:
    """Subscription plan"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""

    plan: str = "free"
    billing_period: BillingPeriod = BillingPeriod.MONTHLY

    # Pricing
    base_price: float = 0.0
    currency: str = "USD"

    # Status
    status: str = "active"  # active, cancelled, past_due, suspended
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None

    # Next billing
    current_period_start: datetime = field(default_factory=datetime.utcnow)
    current_period_end: Optional[datetime] = None

    # Payment method
    payment_method_id: Optional[str] = None

    # Discounts
    discount_percent: float = 0.0
    discount_amount: float = 0.0

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UsageReport:
    """Usage report for a period"""

    tenant_id: str
    period_start: datetime
    period_end: datetime

    # Resource usage
    cpu_hours: float = 0.0
    gpu_hours: float = 0.0
    storage_gb: float = 0.0
    api_requests: int = 0
    inference_requests: int = 0
    training_jobs: int = 0

    # Cost breakdown
    compute_cost: float = 0.0
    storage_cost: float = 0.0
    api_cost: float = 0.0
    total_cost: float = 0.0

    # Daily breakdown
    daily_usage: List[Dict[str, Any]] = field(default_factory=list)


class BillingService:
    """
    Service for managing billing and invoices.
    """

    def __init__(self):
        # In production, store in database
        self.invoices: Dict[str, Invoice] = {}
        self.payments: Dict[str, Payment] = {}
        self.subscriptions: Dict[str, BillingSubscription] = {}
        self.invoice_counter = 1000

    def get_subscription(self, tenant_id: str) -> Optional[BillingSubscription]:
        """Get subscription for a tenant"""
        return self.subscriptions.get(tenant_id)

    def create_subscription(
        self,
        tenant_id: str,
        plan: str,
        billing_period: BillingPeriod = BillingPeriod.MONTHLY,
        trial_days: int = 0,
    ) -> BillingSubscription:
        """Create a new subscription"""
        now = datetime.utcnow()

        # Calculate period end
        if billing_period == BillingPeriod.MONTHLY:
            period_end = now + timedelta(days=30)
        elif billing_period == BillingPeriod.QUARTERLY:
            period_end = now + timedelta(days=90)
        else:  # yearly
            period_end = now + timedelta(days=365)

        subscription = BillingSubscription(
            tenant_id=tenant_id,
            plan=plan,
            billing_period=billing_period,
            base_price=PRICING_PLANS[plan].get(ResourceType.CPU_HOUR).unit_price if PRICING_PLANS.get(plan) else 0,
            current_period_start=now,
            current_period_end=period_end,
        )

        if trial_days > 0:
            subscription.trial_start = now
            subscription.trial_end = now + timedelta(days=trial_days)

        self.subscriptions[tenant_id] = subscription
        return subscription

    def update_subscription_plan(
        self, tenant_id: str, new_plan: str
    ) -> Optional[BillingSubscription]:
        """Update subscription plan"""
        subscription = self.subscriptions.get(tenant_id)
        if not subscription:
            return None

        subscription.plan = new_plan
        subscription.updated_at = datetime.utcnow()
        return subscription

    def cancel_subscription(self, tenant_id: str) -> bool:
        """Cancel subscription"""
        subscription = self.subscriptions.get(tenant_id)
        if not subscription:
            return False

        subscription.status = "cancelled"
        subscription.updated_at = datetime.utcnow()
        return True

    def generate_invoice(
        self,
        tenant_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> Invoice:
        """
        Generate an invoice for a billing period.

        Args:
            tenant_id: Tenant ID
            period_start: Period start
            period_end: Period end

        Returns:
            Generated invoice
        """
        subscription = self.get_subscription(tenant_id)
        plan = subscription.plan if subscription else "free"

        # Get usage summary
        usage_summary = metering_service.get_usage_summary(
            tenant_id, period_start, period_end, plan
        )

        # Create invoice
        self.invoice_counter += 1
        invoice = Invoice(
            tenant_id=tenant_id,
            invoice_number=f"INV-{datetime.utcnow().strftime('%Y%m')}-{self.invoice_counter:06d}",
            period_start=period_start,
            period_end=period_end,
            billing_period=BillingPeriod.MONTHLY,
            usage_summary=usage_summary,
            due_date=period_end + timedelta(days=30),  # Net 30
        )

        # Add line items for each resource type
        for resource_type, amount in usage_summary.usage.items():
            price_info = PRICING_PLANS[plan].get(resource_type)
            if not price_info:
                continue

            # Calculate billable amount (over free tier)
            free_used = usage_summary.free_tier_used.get(resource_type, 0)
            billable = max(0, amount - price_info.free_allowance)

            if billable > 0:
                unit_name = price_info.unit.value
                if resource_type == ResourceType.CPU_HOUR:
                    description = f"Compute (CPU Hours)"
                elif resource_type == ResourceType.GPU_HOUR:
                    description = f"Compute (GPU Hours)"
                elif resource_type == ResourceType.STORAGE_GB_MONTH:
                    description = f"Storage (GB/month)"
                elif resource_type == ResourceType.API_REQUEST:
                    description = f"API Requests"
                elif resource_type == ResourceType.INFERENCE_REQUEST:
                    description = f"Model Inference Requests"
                else:
                    description = f"{resource_type.value}"

                invoice.add_line_item(
                    description=description,
                    quantity=billable,
                    unit_price=price_info.unit_price,
                    unit=unit_name,
                    resource_type=resource_type,
                )

        # Calculate total
        invoice.calculate_total()

        self.invoices[invoice.id] = invoice

        # Update subscription with invoice
        if subscription:
            subscription.current_period_start = period_end
            if subscription.current_period_end:
                if subscription.billing_period == BillingPeriod.MONTHLY:
                    subscription.current_period_end = period_end + timedelta(days=30)
                elif subscription.billing_period == BillingPeriod.QUARTERLY:
                    subscription.current_period_end = period_end + timedelta(days=90)
                else:
                    subscription.current_period_end = period_end + timedelta(days=365)

        return invoice

    def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """Get invoice by ID"""
        return self.invoices.get(invoice_id)

    def get_tenant_invoices(
        self, tenant_id: str, status: Optional[InvoiceStatus] = None
    ) -> List[Invoice]:
        """Get all invoices for a tenant"""
        invoices = [inv for inv in self.invoices.values() if inv.tenant_id == tenant_id]

        if status:
            invoices = [inv for inv in invoices if inv.status == status]

        return sorted(invoices, key=lambda x: x.created_at, reverse=True)

    def update_invoice_status(
        self, invoice_id: str, status: InvoiceStatus
    ) -> Optional[Invoice]:
        """Update invoice status"""
        invoice = self.invoices.get(invoice_id)
        if not invoice:
            return None

        invoice.status = status
        invoice.updated_at = datetime.utcnow()
        return invoice

    def create_payment(
        self,
        invoice_id: str,
        amount: float,
        method: PaymentMethod,
        gateway: str = "stripe",
    ) -> Payment:
        """Create a payment"""
        invoice = self.invoices.get(invoice_id)
        if not invoice:
            raise ValueError("Invoice not found")

        payment = Payment(
            invoice_id=invoice_id,
            tenant_id=invoice.tenant_id,
            amount=amount,
            method=method,
            gateway=gateway,
        )

        self.payments[payment.id] = payment

        # Update invoice
        invoice.payment_id = payment.id
        invoice.payment_method = method

        return payment

    def complete_payment(self, payment_id: str, transaction_id: str) -> Optional[Payment]:
        """Mark payment as completed"""
        payment = self.payments.get(payment_id)
        if not payment:
            return None

        payment.status = PaymentStatus.COMPLETED
        payment.gateway_transaction_id = transaction_id
        payment.completed_at = datetime.utcnow()

        # Update invoice status
        if payment.invoice_id:
            invoice = self.invoices.get(payment.invoice_id)
            if invoice:
                invoice.status = InvoiceStatus.PAID

        return payment

    def fail_payment(self, payment_id: str, reason: str) -> Optional[Payment]:
        """Mark payment as failed"""
        payment = self.payments.get(payment_id)
        if not payment:
            return None

        payment.status = PaymentStatus.FAILED
        payment.failed_at = datetime.utcnow()
        payment.gateway_response["error"] = reason

        # Update invoice status
        if payment.invoice_id:
            invoice = self.invoices.get(payment.invoice_id)
            if invoice:
                invoice.status = InvoiceStatus.OVERDUE

        return payment

    def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID"""
        return self.payments.get(payment_id)

    def get_tenant_payments(self, tenant_id: str) -> List[Payment]:
        """Get all payments for a tenant"""
        return [
            p for p in self.payments.values() if p.tenant_id == tenant_id
        ]

    def generate_usage_report(
        self,
        tenant_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> UsageReport:
        """Generate a detailed usage report"""
        subscription = self.get_subscription(tenant_id)
        plan = subscription.plan if subscription else "free"

        usage_summary = metering_service.get_usage_summary(
            tenant_id, period_start, period_end, plan
        )

        report = UsageReport(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            cpu_hours=usage_summary.usage.get(ResourceType.CPU_HOUR, 0),
            gpu_hours=usage_summary.usage.get(ResourceType.GPU_HOUR, 0),
            storage_gb=usage_summary.usage.get(ResourceType.STORAGE_GB_MONTH, 0),
            api_requests=int(usage_summary.usage.get(ResourceType.API_REQUEST, 0)),
            inference_requests=int(usage_summary.usage.get(ResourceType.INFERENCE_REQUEST, 0)),
            training_jobs=int(usage_summary.usage.get(ResourceType.TRAINING_JOB_HOUR, 0)),
            total_cost=usage_summary.total_cost,
        )

        # Calculate cost breakdown
        for rt, cost in usage_summary.breakdown.items():
            if rt in [ResourceType.CPU_HOUR, ResourceType.GPU_HOUR, ResourceType.TRAINING_JOB_HOUR]:
                report.compute_cost += cost
            elif rt == ResourceType.STORAGE_GB_MONTH:
                report.storage_cost += cost
            elif rt in [ResourceType.API_REQUEST, ResourceType.INFERENCE_REQUEST]:
                report.api_cost += cost

        return report

    def check_overdue_invoices(self) -> List[Invoice]:
        """Check and update overdue invoices"""
        now = datetime.utcnow()
        overdue = []

        for invoice in self.invoices.values():
            if invoice.status == InvoiceStatus.PENDING and invoice.due_date:
                if now > invoice.due_date:
                    invoice.status = InvoiceStatus.OVERDUE
                    overdue.append(invoice)

        return overdue

    def get_billing_summary(self, tenant_id: str) -> Dict[str, Any]:
        """Get billing summary for a tenant"""
        subscription = self.get_subscription(tenant_id)
        invoices = self.get_tenant_invoices(tenant_id)

        # Calculate totals
        total_paid = sum(inv.total for inv in invoices if inv.status == InvoiceStatus.PAID)
        total_pending = sum(inv.total for inv in invoices if inv.status == InvoiceStatus.PENDING)
        total_overdue = sum(inv.total for inv in invoices if inv.status == InvoiceStatus.OVERDUE)

        return {
            "subscription": {
                "plan": subscription.plan if subscription else "free",
                "status": subscription.status if subscription else "active",
                "current_period_end": subscription.current_period_end.isoformat() if subscription and subscription.current_period_end else None,
            },
            "invoices": {
                "total_count": len(invoices),
                "paid_amount": round(total_paid, 2),
                "pending_amount": round(total_pending, 2),
                "overdue_amount": round(total_overdue, 2),
            },
            "latest_invoice": invoices[0].to_dict() if invoices else None,
        }

    def apply_discount(
        self, invoice_id: str, discount_amount: float, discount_percent: float = 0
    ) -> Optional[Invoice]:
        """Apply discount to an invoice"""
        invoice = self.invoices.get(invoice_id)
        if not invoice:
            return None

        if discount_percent > 0:
            invoice.discount_amount = invoice.subtotal * (discount_percent / 100)
        else:
            invoice.discount_amount = discount_amount

        invoice.calculate_total()
        invoice.updated_at = datetime.utcnow()

        return invoice


# Global service instance
billing_service = BillingService()
