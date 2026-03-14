"""
Canary Deployment Service for Model Serving

Provides canary deployment capabilities with progressive traffic shifting,
automated promotion/rollback based on metrics.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class CanaryPhase(str, Enum):
    """Canary deployment phases"""

    INITIALIZING = "initializing"
    TRAFFIC_SHIFT = "traffic_shift"
    MONITORING = "monitoring"
    PROMOTED = "promoted"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class CanaryStrategy(str, Enum):
    """Canary deployment strategies"""

    LINEAR = "linear"  # Linear traffic increase
    EXPONENTIAL = "exponential"  # Exponential traffic increase
    CUSTOM = "custom"  # Custom schedule


class MetricThreshold(str, Enum):
    """Metric thresholds for canary evaluation"""

    ERROR_RATE = "error_rate"
    LATENCY_P95 = "latency_p95"
    LATENCY_P99 = "latency_p99"
    REQUEST_RATE = "request_rate"
    CUSTOM = "custom"


@dataclass
class CanaryStep:
    """A single step in canary deployment"""

    step_number: int
    traffic_percentage: int
    duration_minutes: int
    min_requests: int = 100

    # Pass/fail criteria
    max_error_rate: Optional[float] = None
    max_latency_p95_ms: Optional[float] = None

    # State
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"  # pending, in_progress, passed, failed

    # Actual metrics
    actual_error_rate: float = 0.0
    actual_latency_p95_ms: float = 0.0
    total_requests: int = 0

    def is_complete(self) -> bool:
        """Check if step is complete"""
        return self.status in ("passed", "failed")

    def check_pass_criteria(self) -> bool:
        """Check if step passed its criteria"""
        if self.max_error_rate is not None and self.actual_error_rate > self.max_error_rate:
            return False
        if self.max_latency_p95_ms is not None and self.actual_latency_p95_ms > self.max_latency_p95_ms:
            return False
        return True


@dataclass
class CanaryDeployment:
    """Canary deployment configuration"""

    deployment_id: str
    name: str
    service_name: str

    # Model versions
    baseline_model_uri: str
    baseline_version: str
    canary_model_uri: str
    canary_version: str

    # Strategy
    strategy: CanaryStrategy = CanaryStrategy.LINEAR
    steps: List[CanaryStep] = field(default_factory=list)

    # Auto-operations
    auto_promote: bool = True
    auto_rollback: bool = True

    # Rollback configuration
    rollback_threshold: float = 0.10  # 10% degradation triggers rollback
    rollback_on_5xx: bool = True
    rollback_on_latency_spike: bool = True
    latency_spike_threshold: float = 2.0  # 2x baseline latency

    # Status
    phase: CanaryPhase = CanaryPhase.INITIALIZING
    current_step_index: int = 0
    status_message: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Metadata
    project_id: Optional[int] = None
    owner_id: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def current_step(self) -> Optional[CanaryStep]:
        """Get current step"""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    @property
    def is_running(self) -> bool:
        """Check if deployment is running"""
        return self.phase in (
            CanaryPhase.TRAFFIC_SHIFT,
            CanaryPhase.MONITORING,
        )

    @property
    def is_complete(self) -> bool:
        """Check if deployment is complete"""
        return self.phase in (
            CanaryPhase.PROMOTED,
            CanaryPhase.ROLLED_BACK,
            CanaryPhase.FAILED,
        )

    @property
    def current_traffic_percentage(self) -> int:
        """Get current canary traffic percentage"""
        step = self.current_step
        return step.traffic_percentage if step else 0

    @property
    def progress_percentage(self) -> float:
        """Get deployment progress"""
        if not self.steps:
            return 0.0
        completed = sum(1 for s in self.steps if s.is_complete())
        return (completed / len(self.steps)) * 100


@dataclass
class CanaryMetrics:
    """Metrics for canary evaluation"""

    # Request counts
    baseline_request_count: int = 0
    canary_request_count: int = 0

    # Error rates
    baseline_error_rate: float = 0.0
    canary_error_rate: float = 0.0

    # Latency (ms)
    baseline_latency_p50: float = 0.0
    baseline_latency_p95: float = 0.0
    baseline_latency_p99: float = 0.0
    canary_latency_p50: float = 0.0
    canary_latency_p95: float = 0.0
    canary_latency_p99: float = 0.0

    # Timestamp
    collected_at: datetime = field(default_factory=datetime.utcnow)

    def calculate_degradation(self) -> Dict[str, float]:
        """Calculate degradation percentages"""
        degradation = {}

        # Error rate degradation
        if self.baseline_error_rate > 0:
            error_degradation = (self.canary_error_rate - self.baseline_error_rate) / self.baseline_error_rate
            degradation["error_rate"] = error_degradation
        else:
            degradation["error_rate"] = 0.0 if self.canary_error_rate == 0 else 1.0

        # Latency degradation
        if self.baseline_latency_p95 > 0:
            latency_degradation = (self.canary_latency_p95 - self.baseline_latency_p95) / self.baseline_latency_p95
            degradation["latency_p95"] = latency_degradation
        else:
            degradation["latency_p95"] = 0.0

        if self.baseline_latency_p99 > 0:
            latency_degradation = (self.canary_latency_p99 - self.baseline_latency_p99) / self.baseline_latency_p99
            degradation["latency_p99"] = latency_degradation
        else:
            degradation["latency_p99"] = 0.0

        return degradation


class CanaryService:
    """
    Service for managing canary deployments

    Features:
    - Progressive traffic shifting
    - Automated promotion/rollback
    - Custom canary strategies
    - Real-time monitoring
    """

    def __init__(self):
        """Initialize canary service"""
        self._deployments: Dict[str, CanaryDeployment] = {}
        self._metrics_history: Dict[str, List[CanaryMetrics]] = {}
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}

    async def create_canary_deployment(
        self,
        service_name: str,
        baseline_model_uri: str,
        canary_model_uri: str,
        strategy: CanaryStrategy = CanaryStrategy.LINEAR,
        steps: Optional[int] = 5,
        duration_minutes: int = 60,
        **kwargs,
    ) -> CanaryDeployment:
        """
        Create a new canary deployment

        Args:
            service_name: Name of the service
            baseline_model_uri: Baseline model URI
            canary_model_uri: Canary model URI
            strategy: Canary strategy
            steps: Number of canary steps (for auto-generated steps)
            duration_minutes: Total duration for auto-generated steps
            **kwargs: Additional configuration

        Returns:
            Created deployment
        """
        deployment_id = str(uuid.uuid4())

        # Generate steps if not provided
        canary_steps = kwargs.pop("canary_steps", None)
        if canary_steps is None:
            canary_steps = self._generate_canary_steps(
                strategy=strategy,
                num_steps=steps,
                total_duration_minutes=duration_minutes,
                **kwargs,
            )

        deployment = CanaryDeployment(
            deployment_id=deployment_id,
            name=kwargs.get("name", f"canary-{service_name}"),
            service_name=service_name,
            baseline_model_uri=baseline_model_uri,
            baseline_version=kwargs.get("baseline_version", "current"),
            canary_model_uri=canary_model_uri,
            canary_version=kwargs.get("canary_version", "canary"),
            strategy=strategy,
            steps=canary_steps,
            auto_promote=kwargs.get("auto_promote", True),
            auto_rollback=kwargs.get("auto_rollback", True),
            rollback_threshold=kwargs.get("rollback_threshold", 0.10),
            **kwargs,
        )

        self._deployments[deployment_id] = deployment
        self._metrics_history[deployment_id] = []

        logger.info(f"Created canary deployment: {deployment_id}")

        return deployment

    def _generate_canary_steps(
        self,
        strategy: CanaryStrategy,
        num_steps: int,
        total_duration_minutes: int,
        **kwargs,
    ) -> List[CanaryStep]:
        """Generate canary deployment steps"""
        steps = []
        step_duration = total_duration_minutes // num_steps

        for i in range(num_steps):
            if strategy == CanaryStrategy.LINEAR:
                # Linear: 10%, 20%, 40%, 70%, 100%
                traffic_pct = int(100 * (i + 1) / num_steps)
            elif strategy == CanaryStrategy.EXPONENTIAL:
                # Exponential: 5%, 10%, 20%, 40%, 100%
                traffic_pct = min(100, int(5 * (2 ** i)))
            else:
                traffic_pct = int(100 * (i + 1) / num_steps)

            step = CanaryStep(
                step_number=i + 1,
                traffic_percentage=traffic_pct,
                duration_minutes=step_duration,
                min_requests=kwargs.get("min_requests_per_step", 100),
                max_error_rate=kwargs.get("max_error_rate", 0.05),
                max_latency_p95_ms=kwargs.get("max_latency_p95_ms"),
            )
            steps.append(step)

        return steps

    async def start_deployment(self, deployment_id: str) -> CanaryDeployment:
        """Start a canary deployment"""
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        deployment.phase = CanaryPhase.TRAFFIC_SHIFT
        deployment.started_at = datetime.utcnow()

        # Start monitoring task
        task = asyncio.create_task(self._monitor_deployment(deployment_id))
        self._monitoring_tasks[deployment_id] = task

        logger.info(f"Started canary deployment: {deployment_id}")
        return deployment

    async def _monitor_deployment(self, deployment_id: str):
        """Monitor deployment progress"""
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            return

        while deployment.is_running:
            try:
                # Check current step
                step = deployment.current_step
                if not step:
                    # All steps completed
                    if deployment.auto_promote:
                        await self.promote_canary(deployment_id)
                    break

                # Start step if not started
                if step.status == "pending":
                    step.status = "in_progress"
                    step.started_at = datetime.utcnow()
                    await self._apply_traffic_split(deployment_id, step.traffic_percentage)

                # Check if step should complete
                if await self._check_step_complete(deployment_id, step):
                    if step.check_pass_criteria():
                        step.status = "passed"
                        step.completed_at = datetime.utcnow()
                        deployment.current_step_index += 1

                        # Check if all steps passed
                        if deployment.current_step_index >= len(deployment.steps):
                            if deployment.auto_promote:
                                await self.promote_canary(deployment_id)
                            break
                    else:
                        # Step failed
                        if deployment.auto_rollback:
                            await self.rollback_deployment(deployment_id, "Step failed pass criteria")
                        else:
                            deployment.phase = CanaryPhase.FAILED
                            deployment.status_message = f"Step {step.step_number} failed criteria"
                        break

                await asyncio.sleep(10)  # Check every 10 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error monitoring deployment {deployment_id}: {e}")
                await asyncio.sleep(30)

    async def _check_step_complete(
        self,
        deployment_id: str,
        step: CanaryStep,
    ) -> bool:
        """Check if canary step is complete"""
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            return False

        # Check if duration elapsed
        if step.started_at:
            elapsed = (datetime.utcnow() - step.started_at).total_seconds() / 60
            if elapsed < step.duration_minutes:
                return False

        # Get current metrics
        metrics = await self._collect_metrics(deployment_id)
        if not metrics:
            return False

        # Check minimum requests
        if metrics.canary_request_count < step.min_requests:
            return False

        # Update step metrics
        step.actual_error_rate = metrics.canary_error_rate
        step.actual_latency_p95_ms = metrics.canary_latency_p95
        step.total_requests = metrics.canary_request_count

        # Check if we should fail early due to severe degradation
        if deployment.auto_rollback:
            degradation = metrics.calculate_degradation()
            if degradation.get("error_rate", 0) > deployment.rollback_threshold * 2:
                # Severe error rate spike, fail immediately
                return True

        return True

    async def _collect_metrics(self, deployment_id: str) -> Optional[CanaryMetrics]:
        """Collect metrics for canary evaluation"""
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            return None

        # In production, query Prometheus/datadog
        # For now, return mock metrics that gradually improve
        history = self._metrics_history.get(deployment_id, [])

        if not history:
            # Initial metrics
            metrics = CanaryMetrics(
                baseline_request_count=1000,
                canary_request_count=100,
                baseline_error_rate=0.01,
                canary_error_rate=0.012,
                baseline_latency_p95=100.0,
                canary_latency_p95=110.0,
            )
        else:
            # Simulated metrics that improve over time
            last = history[-1]
            metrics = CanaryMetrics(
                baseline_request_count=last.baseline_request_count + 100,
                canary_request_count=last.canary_request_count + 50,
                baseline_error_rate=0.01,
                canary_error_rate=max(0.008, last.canary_error_rate * 0.95),
                baseline_latency_p95=100.0,
                canary_latency_p95=max(95.0, last.canary_latency_p95 * 0.98),
            )

        self._metrics_history[deployment_id].append(metrics)
        return metrics

    async def _apply_traffic_split(
        self,
        deployment_id: str,
        canary_traffic_percentage: int,
    ):
        """Apply traffic split via Istio/service mesh"""
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            return

        logger.info(
            f"Applying traffic split for {deployment_id}: "
            f"canary={canary_traffic_percentage}%, baseline={100-canary_traffic_percentage}%"
        )

        # In production, update Istio VirtualService or similar
        await asyncio.sleep(0.1)

    async def promote_canary(self, deployment_id: str) -> CanaryDeployment:
        """Promote canary to 100% traffic"""
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        # Shift all traffic to canary
        await self._apply_traffic_split(deployment_id, 100)

        deployment.phase = CanaryPhase.PROMOTED
        deployment.completed_at = datetime.utcnow()
        deployment.status_message = "Canary successfully promoted"

        # Cancel monitoring task
        if deployment_id in self._monitoring_tasks:
            self._monitoring_tasks[deployment_id].cancel()
            del self._monitoring_tasks[deployment_id]

        logger.info(f"Promoted canary deployment: {deployment_id}")
        return deployment

    async def rollback_deployment(
        self,
        deployment_id: str,
        reason: str = "Manual rollback",
    ) -> CanaryDeployment:
        """Rollback canary deployment"""
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        # Shift all traffic back to baseline
        await self._apply_traffic_split(deployment_id, 0)

        deployment.phase = CanaryPhase.ROLLED_BACK
        deployment.completed_at = datetime.utcnow()
        deployment.status_message = f"Rolled back: {reason}"

        # Cancel monitoring task
        if deployment_id in self._monitoring_tasks:
            self._monitoring_tasks[deployment_id].cancel()
            del self._monitoring_tasks[deployment_id]

        logger.warning(f"Rolled back canary deployment {deployment_id}: {reason}")
        return deployment

    async def pause_deployment(self, deployment_id: str) -> CanaryDeployment:
        """Pause a canary deployment at current step"""
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        deployment.phase = CanaryPhase.MONITORING

        if deployment_id in self._monitoring_tasks:
            self._monitoring_tasks[deployment_id].cancel()
            del self._monitoring_tasks[deployment_id]

        logger.info(f"Paused canary deployment: {deployment_id}")
        return deployment

    async def resume_deployment(self, deployment_id: str) -> CanaryDeployment:
        """Resume a paused canary deployment"""
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        deployment.phase = CanaryPhase.TRAFFIC_SHIFT

        # Restart monitoring
        task = asyncio.create_task(self._monitor_deployment(deployment_id))
        self._monitoring_tasks[deployment_id] = task

        logger.info(f"Resumed canary deployment: {deployment_id}")
        return deployment

    async def set_traffic_percentage(
        self,
        deployment_id: str,
        traffic_percentage: int,
    ) -> CanaryDeployment:
        """Manually set canary traffic percentage"""
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        if not 0 <= traffic_percentage <= 100:
            raise ValueError("Traffic percentage must be between 0 and 100")

        await self._apply_traffic_split(deployment_id, traffic_percentage)

        # Update current step if manual override
        step = deployment.current_step
        if step:
            step.traffic_percentage = traffic_percentage

        logger.info(f"Set traffic for {deployment_id} to {traffic_percentage}%")
        return deployment

    async def record_metrics(
        self,
        deployment_id: str,
        metrics: CanaryMetrics,
    ):
        """Record metrics for deployment"""
        if deployment_id not in self._metrics_history:
            self._metrics_history[deployment_id] = []

        self._metrics_history[deployment_id].append(metrics)

    async def get_deployment_status(
        self,
        deployment_id: str,
    ) -> Dict[str, Any]:
        """Get deployment status"""
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        metrics_history = self._metrics_history.get(deployment_id, [])
        latest_metrics = metrics_history[-1] if metrics_history else None

        steps_status = []
        for step in deployment.steps:
            steps_status.append({
                "step_number": step.step_number,
                "traffic_percentage": step.traffic_percentage,
                "duration_minutes": step.duration_minutes,
                "status": step.status,
                "started_at": step.started_at.isoformat() if step.started_at else None,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                "actual_error_rate": step.actual_error_rate,
                "actual_latency_p95_ms": step.actual_latency_p95_ms,
                "total_requests": step.total_requests,
            })

        return {
            "deployment_id": deployment.deployment_id,
            "name": deployment.name,
            "service_name": deployment.service_name,
            "phase": deployment.phase.value,
            "current_step": deployment.current_step_index + 1,
            "total_steps": len(deployment.steps),
            "progress_percentage": deployment.progress_percentage,
            "current_traffic_percentage": deployment.current_traffic_percentage,
            "is_running": deployment.is_running,
            "is_complete": deployment.is_complete,
            "status_message": deployment.status_message,
            "baseline_model": deployment.baseline_model_uri,
            "canary_model": deployment.canary_model_uri,
            "steps": steps_status,
            "latest_metrics": {
                "canary_error_rate": latest_metrics.canary_error_rate if latest_metrics else None,
                "canary_latency_p95_ms": latest_metrics.canary_latency_p95 if latest_metrics else None,
                "canary_request_count": latest_metrics.canary_request_count if latest_metrics else None,
            },
            "created_at": deployment.created_at.isoformat(),
            "started_at": deployment.started_at.isoformat() if deployment.started_at else None,
            "completed_at": deployment.completed_at.isoformat() if deployment.completed_at else None,
        }

    async def list_deployments(
        self,
        service_name: Optional[str] = None,
        phase: Optional[CanaryPhase] = None,
    ) -> List[CanaryDeployment]:
        """List canary deployments"""
        deployments = list(self._deployments.values())

        if service_name:
            deployments = [d for d in deployments if d.service_name == service_name]

        if phase:
            deployments = [d for d in deployments if d.phase == phase]

        return deployments

    async def delete_deployment(self, deployment_id: str) -> bool:
        """Delete a canary deployment"""
        if deployment_id not in self._deployments:
            return False

        deployment = self._deployments[deployment_id]
        if deployment.is_running:
            await self.rollback_deployment(deployment_id, "Deployment deleted")

        del self._deployments[deployment_id]
        if deployment_id in self._metrics_history:
            del self._metrics_history[deployment_id]
        if deployment_id in self._monitoring_tasks:
            self._monitoring_tasks[deployment_id].cancel()
            del self._monitoring_tasks[deployment_id]

        return True


# Singleton instance
_canary_service: Optional[CanaryService] = None


def get_canary_service() -> CanaryService:
    """Get or create canary service singleton"""
    global _canary_service
    if _canary_service is None:
        _canary_service = CanaryService()
    return _canary_service
