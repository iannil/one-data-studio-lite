"""
A/B Testing Service for Model Serving

Provides A/B testing capabilities for model inference services,
including traffic routing, metrics collection, and statistical analysis.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import uuid

logger = logging.getLogger(__name__)


class TrafficSplitMethod(str, Enum):
    """Traffic split methods for A/B testing"""

    FIXED = "fixed"  # Fixed percentage split
    EPSILON_GREEDY = "epsilon_greedy"  # Explore-exploit
    THOMPSON_SAMPLING = "thompson_sampling"  # Bayesian bandit
    UCB1 = "ucb1"  # Upper Confidence Bound


class SuccessMetricType(str, Enum):
    """Types of success metrics"""

    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    CONVERSION_RATE = "conversion_rate"
    REVENUE = "revenue"
    CUSTOM = "custom"


@dataclass
class ModelVariant:
    """A single model variant in A/B testing"""

    variant_id: str
    name: str
    model_uri: str
    model_version: str

    # Traffic configuration
    traffic_percentage: int = 50  # 0-100
    min_traffic: int = 1  # Minimum traffic percentage

    # Performance tracking
    request_count: int = 0
    success_count: int = 0
    error_count: int = 0

    # Metrics
    latency_sum_ms: float = 0
    latency_samples: int = 0

    # Custom metrics
    custom_metrics: Dict[str, float] = field(default_factory=dict)

    # Status
    is_enabled: bool = True
    is_winner: bool = False

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.request_count == 0:
            return 0.0
        return self.success_count / self.request_count

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency"""
        if self.latency_samples == 0:
            return 0.0
        return self.latency_sum_ms / self.latency_samples

    def record_request(self, success: bool, latency_ms: float):
        """Record a request result"""
        self.request_count += 1
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
        self.latency_sum_ms += latency_ms
        self.latency_samples += 1
        self.updated_at = datetime.utcnow()

    def update_custom_metric(self, metric_name: str, value: float):
        """Update a custom metric value"""
        self.custom_metrics[metric_name] = value
        self.updated_at = datetime.utcnow()


@dataclass
class ABTestExperiment:
    """A/B testing experiment configuration"""

    experiment_id: str
    name: str
    description: Optional[str] = None

    # Variants
    variants: List[ModelVariant] = field(default_factory=list)
    control_variant_id: Optional[str] = None

    # Traffic configuration
    split_method: TrafficSplitMethod = TrafficSplitMethod.FIXED
    epsilon: float = 0.1  # For epsilon-greedy

    # Success criteria
    success_metric: SuccessMetricType = SuccessMetricType.ACCURACY
    success_mode: str = "max"  # "max" or "min"
    min_sample_size: int = 100
    confidence_level: float = 0.95

    # Duration
    duration_hours: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # Status
    is_active: bool = True
    is_paused: bool = False
    winner_variant_id: Optional[str] = None

    # Metadata
    project_id: Optional[int] = None
    owner_id: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def get_variant_by_id(self, variant_id: str) -> Optional[ModelVariant]:
        """Get variant by ID"""
        for variant in self.variants:
            if variant.variant_id == variant_id:
                return variant
        return None

    def get_control_variant(self) -> Optional[ModelVariant]:
        """Get control variant"""
        if self.control_variant_id:
            return self.get_variant_by_id(self.control_variant_id)
        return self.variants[0] if self.variants else None

    def get_enabled_variants(self) -> List[ModelVariant]:
        """Get all enabled variants"""
        return [v for v in self.variants if v.is_enabled]

    def is_running(self) -> bool:
        """Check if experiment is currently running"""
        if not self.is_active or self.is_paused:
            return False
        if self.start_time and self.start_time > datetime.utcnow():
            return False
        if self.end_time and self.end_time < datetime.utcnow():
            return False
        return True

    def has_minimum_samples(self) -> bool:
        """Check if all variants have minimum samples"""
        return all(
            v.request_count >= self.min_sample_size
            for v in self.get_enabled_variants()
        )


@dataclass
class StatisticalTestResult:
    """Result of statistical significance test"""

    is_significant: bool
    p_value: float
    confidence_interval: Tuple[float, float]
    effect_size: float
    test_statistic: float
    test_name: str = "z_test"

    # Variant comparison
    control_metric: float
    treatment_metric: float
    relative_improvement: float

    # Recommendation
    should_promote: bool = False
    recommendation: str = ""


class ABTestingService:
    """
    Service for managing A/B testing experiments

    Features:
    - Multiple traffic split strategies
    - Statistical significance testing
    - Automatic winner selection
    - Real-time metrics tracking
    """

    def __init__(self):
        """Initialize A/B testing service"""
        self._experiments: Dict[str, ABTestExperiment] = {}
        self._results_cache: Dict[str, StatisticalTestResult] = {}

    async def create_experiment(
        self,
        name: str,
        variants: List[Dict[str, Any]],
        success_metric: SuccessMetricType = SuccessMetricType.ACCURACY,
        split_method: TrafficSplitMethod = TrafficSplitMethod.FIXED,
        **kwargs,
    ) -> ABTestExperiment:
        """
        Create a new A/B testing experiment

        Args:
            name: Experiment name
            variants: List of variant configurations
            success_metric: Metric to optimize
            split_method: Traffic split strategy
            **kwargs: Additional configuration

        Returns:
            Created experiment
        """
        experiment_id = str(uuid.uuid4())

        # Create variant objects
        variant_objs = []
        for i, variant_config in enumerate(variants):
            variant = ModelVariant(
                variant_id=str(uuid.uuid4()),
                name=variant_config.get("name", f"variant_{i+1}"),
                model_uri=variant_config["model_uri"],
                model_version=variant_config.get("model_version", "latest"),
                traffic_percentage=variant_config.get("traffic_percentage", 100 // len(variants)),
            )
            variant_objs.append(variant)

        # Set control as first variant
        control_id = variant_objs[0].variant_id if variant_objs else None

        experiment = ABTestExperiment(
            experiment_id=experiment_id,
            name=name,
            variants=variant_objs,
            control_variant_id=control_id,
            success_metric=success_metric,
            split_method=split_method,
            **kwargs,
        )

        self._experiments[experiment_id] = experiment
        logger.info(f"Created A/B test experiment: {experiment_id}")

        return experiment

    async def update_traffic_split(
        self,
        experiment_id: str,
        traffic_distribution: Dict[str, int],
    ) -> bool:
        """
        Update traffic split for variants

        Args:
            experiment_id: Experiment ID
            traffic_distribution: Map variant_id to traffic percentage

        Returns:
            True if updated successfully
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        # Validate percentages sum to 100
        total = sum(traffic_distribution.values())
        if total != 100:
            raise ValueError(f"Traffic percentages must sum to 100, got {total}")

        # Update traffic percentages
        for variant in experiment.variants:
            if variant.variant_id in traffic_distribution:
                variant.traffic_percentage = traffic_distribution[variant.variant_id]

        experiment.updated_at = datetime.utcnow()
        logger.info(f"Updated traffic split for experiment {experiment_id}")

        return True

    async def route_request(
        self,
        experiment_id: str,
        request_id: str,
    ) -> Optional[str]:
        """
        Route a request to appropriate variant

        Args:
            experiment_id: Experiment ID
            request_id: Unique request identifier

        Returns:
            Selected variant ID
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment or not experiment.is_running():
            return None

        enabled_variants = experiment.get_enabled_variants()
        if not enabled_variants:
            return None

        if experiment.split_method == TrafficSplitMethod.FIXED:
            return self._route_fixed(enabled_variants, request_id)
        elif experiment.split_method == TrafficSplitMethod.EPSILON_GREEDY:
            return self._route_epsilon_greedy(experiment, enabled_variants)
        elif experiment.split_method == TrafficSplitMethod.THOMPSON_SAMPLING:
            return self._route_thompson_sampling(experiment, enabled_variants)
        elif experiment.split_method == TrafficSplitMethod.UCB1:
            return self._route_ucb1(experiment, enabled_variants)

        return enabled_variants[0].variant_id

    def _route_fixed(self, variants: List[ModelVariant], request_id: str) -> str:
        """Fixed percentage routing based on hash"""
        # Use consistent hash for same request
        hash_val = int(hashlib.sha256(request_id.encode()).hexdigest(), 16)
        bucket = hash_val % 100

        cumulative = 0
        for variant in variants:
            cumulative += variant.traffic_percentage
            if bucket < cumulative:
                return variant.variant_id

        return variants[-1].variant_id

    def _route_epsilon_greedy(
        self,
        experiment: ABTestExperiment,
        variants: List[ModelVariant],
    ) -> str:
        """Epsilon-greedy routing"""
        import random

        if random.random() < experiment.epsilon:
            # Explore: random variant
            import random
            return random.choice(variants).variant_id
        else:
            # Exploit: best variant so far
            return self._get_best_variant(experiment, variants)

    def _route_thompson_sampling(
        self,
        experiment: ABTestExperiment,
        variants: List[ModelVariant],
    ) -> str:
        """Thompson sampling (Bayesian bandit)"""
        import random
        import math

        best_variant = variants[0]
        best_sample = -1

        for variant in variants:
            # Beta distribution sampling
            alpha = variant.success_count + 1
            beta = variant.error_count + 1
            sample = random.betavariate(alpha, beta)

            if sample > best_sample:
                best_sample = sample
                best_variant = variant

        return best_variant.variant_id

    def _route_ucb1(
        self,
        experiment: ABTestExperiment,
        variants: List[ModelVariant],
    ) -> str:
        """UCB1 (Upper Confidence Bound) routing"""
        import math

        total_requests = sum(v.request_count for v in variants)
        best_variant = variants[0]
        best_score = -1

        for variant in variants:
            if variant.request_count == 0:
                return variant.variant_id

            # UCB1 score
            exploration = math.sqrt(2 * math.log(total_requests) / variant.request_count)
            score = variant.success_rate + exploration

            if score > best_score:
                best_score = score
                best_variant = variant

        return best_variant.variant_id

    def _get_best_variant(
        self,
        experiment: ABTestExperiment,
        variants: List[ModelVariant],
    ) -> str:
        """Get best variant based on success metric"""
        if experiment.success_mode == "max":
            best = max(variants, key=lambda v: v.success_rate)
        else:
            best = min(variants, key=lambda v: v.success_rate)
        return best.variant_id

    async def record_metric(
        self,
        experiment_id: str,
        variant_id: str,
        success: bool,
        latency_ms: float = 0,
        custom_metrics: Optional[Dict[str, float]] = None,
    ):
        """
        Record a request metric

        Args:
            experiment_id: Experiment ID
            variant_id: Variant that handled the request
            success: Whether request was successful
            latency_ms: Request latency
            custom_metrics: Optional custom metric values
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return

        variant = experiment.get_variant_by_id(variant_id)
        if not variant:
            return

        variant.record_request(success, latency_ms)

        if custom_metrics:
            for name, value in custom_metrics.items():
                variant.update_custom_metric(name, value)

    async def get_experiment_results(
        self,
        experiment_id: str,
    ) -> Dict[str, Any]:
        """
        Get experiment results and statistics

        Args:
            experiment_id: Experiment ID

        Returns:
            Experiment results
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        variant_results = []
        for variant in experiment.variants:
            result = {
                "variant_id": variant.variant_id,
                "name": variant.name,
                "traffic_percentage": variant.traffic_percentage,
                "request_count": variant.request_count,
                "success_rate": variant.success_rate,
                "avg_latency_ms": variant.avg_latency_ms,
                "is_enabled": variant.is_enabled,
                "is_winner": variant.is_winner,
                "custom_metrics": variant.custom_metrics,
            }
            variant_results.append(result)

        return {
            "experiment_id": experiment.experiment_id,
            "name": experiment.name,
            "is_active": experiment.is_active,
            "is_running": experiment.is_running(),
            "has_minimum_samples": experiment.has_minimum_samples(),
            "success_metric": experiment.success_metric.value,
            "variants": variant_results,
        }

    async def run_significance_test(
        self,
        experiment_id: str,
        treatment_variant_id: str,
    ) -> StatisticalTestResult:
        """
        Run statistical significance test

        Args:
            experiment_id: Experiment ID
            treatment_variant_id: Treatment variant to compare against control

        Returns:
            Statistical test result
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        control = experiment.get_control_variant()
        treatment = experiment.get_variant_by_id(treatment_variant_id)

        if not control or not treatment:
            raise ValueError("Control or treatment variant not found")

        # Perform z-test for proportions
        control_rate = control.success_rate
        treatment_rate = treatment.success_rate

        result = self._z_test_proportions(
            control.success_count,
            control.request_count,
            treatment.success_count,
            treatment.request_count,
            experiment.confidence_level,
        )

        # Determine if treatment is better
        if experiment.success_mode == "max":
            relative_improvement = (treatment_rate - control_rate) / max(control_rate, 0.001)
            result.should_promote = result.is_significant and treatment_rate > control_rate
        else:
            relative_improvement = (control_rate - treatment_rate) / max(control_rate, 0.001)
            result.should_promote = result.is_significant and treatment_rate < control_rate

        result.control_metric = control_rate
        result.treatment_metric = treatment_rate
        result.relative_improvement = relative_improvement

        # Generate recommendation
        if result.should_promote:
            result.recommendation = (
                f"Treatment variant shows {relative_improvement:.1%} improvement "
                f"with {result.confidence_level:.0%} confidence. Consider promoting."
            )
        elif result.is_significant:
            result.recommendation = (
                f"Difference is significant but treatment is worse. "
                f"{'Keep control' if experiment.success_mode == 'max' else 'Consider promoting (lower is better)'}"
            )
        else:
            result.recommendation = (
                f"Not enough statistical significance. Collect more samples "
                f"(current: {min(control.request_count, treatment.request_count)}, "
                f"minimum: {experiment.min_sample_size})"
            )

        self._results_cache[experiment_id] = result
        return result

    def _z_test_proportions(
        self,
        control_success: int,
        control_total: int,
        treatment_success: int,
        treatment_total: int,
        confidence_level: float = 0.95,
    ) -> StatisticalTestResult:
        """
        Perform z-test for two proportions

        Returns:
            Test result
        """
        import math
        from scipy import stats

        if control_total == 0 or treatment_total == 0:
            return StatisticalTestResult(
                is_significant=False,
                p_value=1.0,
                confidence_interval=(0, 0),
                effect_size=0,
                test_statistic=0,
            )

        p1 = control_success / control_total
        p2 = treatment_success / treatment_total

        # Pooled proportion
        p_pooled = (control_success + treatment_success) / (control_total + treatment_total)

        # Standard error
        se = math.sqrt(p_pooled * (1 - p_pooled) * (1/control_total + 1/treatment_total))

        if se == 0:
            return StatisticalTestResult(
                is_significant=False,
                p_value=1.0,
                confidence_interval=(0, 0),
                effect_size=0,
                test_statistic=0,
            )

        # Z statistic
        z = (p2 - p1) / se

        # Two-tailed p-value
        p_value = 2 * (1 - stats.norm.cdf(abs(z)))

        # Critical value for confidence level
        alpha = 1 - confidence_level
        critical_value = stats.norm.ppf(1 - alpha / 2)

        is_significant = abs(z) > critical_value

        # Confidence interval for difference
        margin = critical_value * se
        ci_lower = (p2 - p1) - margin
        ci_upper = (p2 - p1) + margin

        # Effect size (Cohen's h)
        effect_size = 2 * (math.asin(math.sqrt(p2)) - math.asin(math.sqrt(p1)))

        return StatisticalTestResult(
            is_significant=is_significant,
            p_value=p_value,
            confidence_interval=(ci_lower, ci_upper),
            effect_size=effect_size,
            test_statistic=z,
        )

    async def select_winner(
        self,
        experiment_id: str,
        winner_variant_id: Optional[str] = None,
    ) -> ABTestExperiment:
        """
        Select winner variant and end experiment

        Args:
            experiment_id: Experiment ID
            winner_variant_id: Winner variant (auto-select if None)

        Returns:
            Updated experiment
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        if winner_variant_id:
            # Manual selection
            winner = experiment.get_variant_by_id(winner_variant_id)
            if not winner:
                raise ValueError(f"Variant {winner_variant_id} not found")
        else:
            # Auto-select based on metrics
            enabled = experiment.get_enabled_variants()
            if experiment.success_mode == "max":
                winner = max(enabled, key=lambda v: v.success_rate)
            else:
                winner = min(enabled, key=lambda v: v.success_rate)
            winner_variant_id = winner.variant_id

        # Mark winner and end experiment
        for variant in experiment.variants:
            variant.is_winner = (variant.variant_id == winner_variant_id)

        experiment.winner_variant_id = winner_variant_id
        experiment.is_active = False
        experiment.updated_at = datetime.utcnow()

        logger.info(f"Experiment {experiment_id} winner selected: {winner_variant_id}")
        return experiment

    async def pause_experiment(self, experiment_id: str) -> bool:
        """Pause an experiment"""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return False
        experiment.is_paused = True
        experiment.updated_at = datetime.utcnow()
        return True

    async def resume_experiment(self, experiment_id: str) -> bool:
        """Resume a paused experiment"""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return False
        experiment.is_paused = False
        experiment.updated_at = datetime.utcnow()
        return True

    async def delete_experiment(self, experiment_id: str) -> bool:
        """Delete an experiment"""
        if experiment_id in self._experiments:
            del self._experiments[experiment_id]
            if experiment_id in self._results_cache:
                del self._results_cache[experiment_id]
            return True
        return False

    async def list_experiments(
        self,
        project_id: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> List[ABTestExperiment]:
        """List experiments with filters"""
        experiments = list(self._experiments.values())

        if project_id is not None:
            experiments = [e for e in experiments if e.project_id == project_id]

        if is_active is not None:
            experiments = [e for e in experiments if e.is_active == is_active]

        return experiments

    async def get_experiment(self, experiment_id: str) -> Optional[ABTestExperiment]:
        """Get experiment by ID"""
        return self._experiments.get(experiment_id)


# Singleton instance
_ab_testing_service: Optional[ABTestingService] = None


def get_ab_testing_service() -> ABTestingService:
    """Get or create A/B testing service singleton"""
    global _ab_testing_service
    if _ab_testing_service is None:
        _ab_testing_service = ABTestingService()
    return _ab_testing_service


# Import hashlib at module level for _route_fixed
import hashlib
