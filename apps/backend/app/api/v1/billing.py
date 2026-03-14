"""
Billing API Endpoints

APIs for managing billing, invoices, and payments.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.models.user import User
from app.services.billing.billing import (
    billing_service,
    Invoice,
    InvoiceStatus,
    PaymentMethod,
    PaymentStatus,
    BillingPeriod,
)
from app.services.billing.metering import (
    metering_service,
    ResourceType,
    UsageReport,
)


router = APIRouter()


# Request/Response Schemas
class SubscriptionCreateRequest(BaseModel):
    plan: str = Field(..., description="Subscription plan: free, basic, professional, enterprise")
    billing_period: str = Field("monthly", description="Billing period: monthly, quarterly, yearly")
    trial_days: int = Field(0, ge=0, le=90, description="Trial period in days")


class SubscriptionUpdateRequest(BaseModel):
    plan: str = Field(..., description="New plan")


class SubscriptionResponse(BaseModel):
    id: str
    tenant_id: str
    plan: str
    billing_period: str
    base_price: float
    currency: str
    status: str
    trial_start: Optional[datetime]
    trial_end: Optional[datetime]
    current_period_start: datetime
    current_period_end: Optional[datetime]
    discount_percent: float
    discount_amount: float


class InvoiceResponse(BaseModel):
    id: str
    tenant_id: str
    invoice_number: str
    period_start: datetime
    period_end: datetime
    billing_period: str
    subtotal: float
    tax_amount: float
    tax_rate: float
    discount_amount: float
    total: float
    status: str
    due_date: Optional[datetime]
    line_items: List[Dict[str, Any]]
    payment_method: Optional[str]
    created_at: datetime


class UsageResponse(BaseModel):
    tenant_id: str
    period_start: datetime
    period_end: datetime
    usage: Dict[str, float]
    total_cost: float
    breakdown: Dict[str, float]
    free_tier_used: Dict[str, float]
    free_tier_remaining: Dict[str, float]


class PaymentCreateRequest(BaseModel):
    invoice_id: str
    amount: float
    method: str = Field("credit_card", description="Payment method")
    gateway: str = Field("stripe", description="Payment gateway")


class PaymentResponse(BaseModel):
    id: str
    invoice_id: str
    amount: float
    currency: str
    method: str
    status: str
    card_last4: str
    card_brand: str
    created_at: datetime
    completed_at: Optional[datetime]


class UsageRecordRequest(BaseModel):
    tenant_id: str
    resource_type: str
    amount: float
    unit: str = "count"
    metadata: Optional[Dict[str, Any]] = None


# Subscription Endpoints
@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(current_user: User = Depends(get_current_user)):
    """Get current subscription"""
    # For simplicity, use user ID as tenant ID
    tenant_id = str(current_user.id)
    subscription = billing_service.get_subscription(tenant_id)

    if not subscription:
        # Create default free subscription
        subscription = billing_service.create_subscription(tenant_id, "free")

    return SubscriptionResponse(
        id=subscription.id,
        tenant_id=subscription.tenant_id,
        plan=subscription.plan,
        billing_period=subscription.billing_period.value,
        base_price=subscription.base_price,
        currency=subscription.currency,
        status=subscription.status,
        trial_start=subscription.trial_start,
        trial_end=subscription.trial_end,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        discount_percent=subscription.discount_percent,
        discount_amount=subscription.discount_amount,
    )


@router.post("/subscription", response_model=SubscriptionResponse)
async def create_subscription(
    request: SubscriptionCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a new subscription"""
    tenant_id = str(current_user.id)

    # Check if subscription exists
    existing = billing_service.get_subscription(tenant_id)
    if existing and existing.status == "active":
        raise HTTPException(status_code=400, detail="Active subscription already exists")

    subscription = billing_service.create_subscription(
        tenant_id=tenant_id,
        plan=request.plan,
        billing_period=BillingPeriod(request.billing_period),
        trial_days=request.trial_days,
    )

    return SubscriptionResponse(
        id=subscription.id,
        tenant_id=subscription.tenant_id,
        plan=subscription.plan,
        billing_period=subscription.billing_period.value,
        base_price=subscription.base_price,
        currency=subscription.currency,
        status=subscription.status,
        trial_start=subscription.trial_start,
        trial_end=subscription.trial_end,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        discount_percent=subscription.discount_percent,
        discount_amount=subscription.discount_amount,
    )


@router.put("/subscription", response_model=SubscriptionResponse)
async def update_subscription(
    request: SubscriptionUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    """Update subscription plan"""
    tenant_id = str(current_user.id)

    subscription = billing_service.update_subscription_plan(tenant_id, request.plan)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return SubscriptionResponse(
        id=subscription.id,
        tenant_id=subscription.tenant_id,
        plan=subscription.plan,
        billing_period=subscription.billing_period.value,
        base_price=subscription.base_price,
        currency=subscription.currency,
        status=subscription.status,
        trial_start=subscription.trial_start,
        trial_end=subscription.trial_end,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        discount_percent=subscription.discount_percent,
        discount_amount=subscription.discount_amount,
    )


@router.delete("/subscription")
async def cancel_subscription(current_user: User = Depends(get_current_user)):
    """Cancel subscription"""
    tenant_id = str(current_user.id)
    success = billing_service.cancel_subscription(tenant_id)

    if not success:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return {"message": "Subscription cancelled"}


# Invoice Endpoints
@router.get("/invoices", response_model=List[InvoiceResponse])
async def list_invoices(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """List invoices for current tenant"""
    tenant_id = str(current_user.id)

    invoice_status = InvoiceStatus(status) if status else None
    invoices = billing_service.get_tenant_invoices(tenant_id, invoice_status)

    return [
        InvoiceResponse(
            id=inv.id,
            tenant_id=inv.tenant_id,
            invoice_number=inv.invoice_number,
            period_start=inv.period_start,
            period_end=inv.period_end,
            billing_period=inv.billing_period.value,
            subtotal=inv.subtotal,
            tax_amount=inv.tax_amount,
            tax_rate=inv.tax_rate,
            discount_amount=inv.discount_amount,
            total=inv.total,
            status=inv.status.value,
            due_date=inv.due_date,
            line_items=[
                {
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit": item.unit,
                    "unit_price": item.unit_price,
                    "amount": item.amount,
                }
                for item in inv.line_items
            ],
            payment_method=inv.payment_method.value if inv.payment_method else None,
            created_at=inv.created_at,
        )
        for inv in invoices[:limit]
    ]


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get invoice details"""
    invoice = billing_service.get_invoice(invoice_id)

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Verify tenant access
    if invoice.tenant_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    return InvoiceResponse(
        id=invoice.id,
        tenant_id=invoice.tenant_id,
        invoice_number=invoice.invoice_number,
        period_start=invoice.period_start,
        period_end=invoice.period_end,
        billing_period=invoice.billing_period.value,
        subtotal=invoice.subtotal,
        tax_amount=invoice.tax_amount,
        tax_rate=invoice.tax_rate,
        discount_amount=invoice.discount_amount,
        total=invoice.total,
        status=invoice.status.value,
        due_date=invoice.due_date,
        line_items=[
            {
                "description": item.description,
                "quantity": item.quantity,
                "unit": item.unit,
                "unit_price": item.unit_price,
                "amount": item.amount,
            }
            for item in invoice.line_items
        ],
        payment_method=invoice.payment_method.value if invoice.payment_method else None,
        created_at=invoice.created_at,
    )


@router.post("/invoices/generate")
async def generate_invoice(
    period_start: Optional[datetime] = Query(None),
    period_end: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Generate invoice for billing period"""
    tenant_id = str(current_user.id)

    # Default to last month if not specified
    if not period_end:
        period_end = datetime.utcnow()
    if not period_start:
        period_start = period_end - timedelta(days=30)

    invoice = billing_service.generate_invoice(tenant_id, period_start, period_end)

    return InvoiceResponse(
        id=invoice.id,
        tenant_id=invoice.tenant_id,
        invoice_number=invoice.invoice_number,
        period_start=invoice.period_start,
        period_end=invoice.period_end,
        billing_period=invoice.billing_period.value,
        subtotal=invoice.subtotal,
        tax_amount=invoice.tax_amount,
        tax_rate=invoice.tax_rate,
        discount_amount=invoice.discount_amount,
        total=invoice.total,
        status=invoice.status.value,
        due_date=invoice.due_date,
        line_items=[
            {
                "description": item.description,
                "quantity": item.quantity,
                "unit": item.unit,
                "unit_price": item.unit_price,
                "amount": item.amount,
            }
            for item in invoice.line_items
        ],
        payment_method=invoice.payment_method.value if invoice.payment_method else None,
        created_at=invoice.created_at,
    )


# Payment Endpoints
@router.post("/payments", response_model=PaymentResponse)
async def create_payment(
    request: PaymentCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a payment"""
    tenant_id = str(current_user.id)

    # Verify invoice belongs to tenant
    invoice = billing_service.get_invoice(request.invoice_id)
    if not invoice or invoice.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Invoice not found")

    payment = billing_service.create_payment(
        invoice_id=request.invoice_id,
        amount=request.amount,
        method=PaymentMethod(request.method),
        gateway=request.gateway,
    )

    return PaymentResponse(
        id=payment.id,
        invoice_id=payment.invoice_id,
        amount=payment.amount,
        currency=payment.currency,
        method=payment.method.value,
        status=payment.status.value,
        card_last4=payment.card_last4,
        card_brand=payment.card_brand,
        created_at=payment.created_at,
        completed_at=payment.completed_at,
    )


@router.get("/payments", response_model=List[PaymentResponse])
async def list_payments(current_user: User = Depends(get_current_user)):
    """List payments for current tenant"""
    tenant_id = str(current_user.id)
    payments = billing_service.get_tenant_payments(tenant_id)

    return [
        PaymentResponse(
            id=p.id,
            invoice_id=p.invoice_id,
            amount=p.amount,
            currency=p.currency,
            method=p.method.value,
            status=p.status.value,
            card_last4=p.card_last4,
            card_brand=p.card_brand,
            created_at=p.created_at,
            completed_at=p.completed_at,
        )
        for p in payments
    ]


# Usage Endpoints
@router.get("/usage")
async def get_usage(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Get usage summary for a period"""
    tenant_id = str(current_user.id)

    # Default to current month
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    subscription = billing_service.get_subscription(tenant_id)
    plan = subscription.plan if subscription else "free"

    summary = metering_service.get_usage_summary(tenant_id, start_date, end_date, plan)

    return {
        "tenant_id": summary.tenant_id,
        "period_start": summary.period_start,
        "period_end": summary.period_end,
        "plan": summary.plan,
        "usage": {rt.value: amt for rt, amt in summary.usage.items()},
        "total_cost": summary.total_cost,
        "breakdown": {rt.value: amt for rt, amt in summary.breakdown.items()},
        "free_tier_used": {rt.value: amt for rt, amt in summary.free_tier_used.items()},
        "free_tier_remaining": {rt.value: amt for rt, amt in summary.free_tier_remaining.items()},
    }


@router.get("/usage/current")
async def get_current_usage(current_user: User = Depends(get_current_user)):
    """Get current real-time usage counters"""
    tenant_id = str(current_user.id)
    usage = metering_service.get_current_usage(tenant_id)

    return {
        "tenant_id": tenant_id,
        "usage": usage,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/usage/record")
async def record_usage(
    request: UsageRecordRequest,
    current_user: User = Depends(get_current_user),
):
    """Record a usage event (internal API)"""
    # This would typically be protected with an internal API key
    record = metering_service.record_usage(
        tenant_id=request.tenant_id,
        resource_type=ResourceType(request.resource_type),
        amount=request.amount,
        unit=request.unit,
        metadata=request.metadata,
    )

    return {
        "id": record.id,
        "tenant_id": record.tenant_id,
        "resource_type": record.resource_type.value,
        "amount": record.amount,
        "timestamp": record.timestamp,
    }


# Billing Summary
@router.get("/summary")
async def get_billing_summary(current_user: User = Depends(get_current_user)):
    """Get billing summary for current tenant"""
    tenant_id = str(current_user.id)
    summary = billing_service.get_billing_summary(tenant_id)

    return summary


# Usage Report
@router.get("/report")
async def get_usage_report(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Get detailed usage report"""
    tenant_id = str(current_user.id)

    # Default to current month
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    report = billing_service.generate_usage_report(tenant_id, start_date, end_date)

    return {
        "tenant_id": report.tenant_id,
        "period_start": report.period_start,
        "period_end": report.period_end,
        "cpu_hours": report.cpu_hours,
        "gpu_hours": report.gpu_hours,
        "storage_gb": report.storage_gb,
        "api_requests": report.api_requests,
        "inference_requests": report.inference_requests,
        "training_jobs": report.training_jobs,
        "compute_cost": round(report.compute_cost, 2),
        "storage_cost": round(report.storage_cost, 2),
        "api_cost": round(report.api_cost, 2),
        "total_cost": round(report.total_cost, 2),
    }
