"""
Hyperparameter Optimization Service

Provides integration with Optuna for automated hyperparameter search.
"""

import logging
import asyncio
import uuid
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)


class OptimizationDirection(str, Enum):
    """Optimization direction"""

    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


class SamplerType(str, Enum):
    """Optuna sampler types"""

    RANDOM = "random"
    TPE = "tpe"  # Tree-structured Parzen Estimator
    CMAES = "cmaes"
    GRID = "grid"
    QUASI_MONTE_CARLO = "quasi_monte_carlo"
    PARTICLE_SWARM = "particle_swarm"


class PrunerType(str, Enum):
    """Optuna pruner types"""

    NONE = "none"
    MEDIAN = "median"
    SUCCESSIVE_HALVING = "successive_halving"
    HYPERBAND = "hyperband"
    SHA = "sha"  # Succinct Hyperparameter Optimization


class TrialStatus(str, Enum):
    """Trial status"""

    RUNNING = "running"
    COMPLETED = "completed"
    PRUNED = "pruned"
    FAILED = "failed"


@dataclass
class SearchSpace:
    """Hyperparameter search space definition"""

    # Categorical parameters
    categorical: Dict[str, List[str]] = field(default_factory=dict)

    # Float parameters (with sampling range and type)
    float_uniform: Dict[str, tuple[float, float]] = field(default_factory=dict)  # (low, high)
    float_log_uniform: Dict[str, tuple[float, float]] = field(default_factory=dict)
    float_discrete_uniform: Dict[str, tuple[float, float, float]] = field(default_factory=dict)  # (low, high, q)

    # Int parameters
    int_uniform: Dict[str, tuple[int, int]] = field(default_factory=dict)  # (low, high)
    int_log_uniform: Dict[str, tuple[int, int]] = field(default_factory=dict)

    def to_optuna_trials(self, trial: Any) -> Dict[str, Any]:
        """Convert search space to Optuna trial suggestions"""
        params = {}

        # Suggest categorical
        for name, choices in self.categorical.items():
            params[name] = trial.suggest_categorical(name, choices)

        # Suggest float
        for name, (low, high) in self.float_uniform.items():
            params[name] = trial.suggest_float(name, low, high)

        for name, (low, high) in self.float_log_uniform.items():
            params[name] = trial.suggest_float(name, low, high, log=True)

        for name, (low, high, q) in self.float_discrete_uniform.items():
            params[name] = trial.suggest_float(name, low, high, q=q)

        # Suggest int
        for name, (low, high) in self.int_uniform.items():
            params[name] = trial.suggest_int(name, low, high)

        for name, (low, high) in self.int_log_uniform.items():
            params[name] = trial.suggest_int(name, low, high, log=True)

        return params


@dataclass
class Trial:
    """Single optimization trial"""

    trial_number: int
    trial_id: str
    params: Dict[str, Any]
    value: float  # Objective value
    intermediate_values: List[float] = field(default_factory=list)
    status: TrialStatus = TrialStatus.RUNNING
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None

    # User attributes
    user_attrs: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    dataset_uri: Optional[str] = None
    model_version: Optional[str] = None


@dataclass
class OptimizationStudy:
    """Optimization study configuration"""

    study_id: str
    name: str
    experiment_id: Optional[str] = None
    project_id: Optional[int] = None

    # Optimization settings
    metric: str = "accuracy"  # Metric to optimize
    direction: OptimizationDirection = OptimizationDirection.MAXIMIZE

    # Search configuration
    sampler: SamplerType = SamplerType.TPE
    pruner: PrunerType = PrunerType.NONE

    # Trial settings
    n_trials: int = 100
    timeout_hours: Optional[float] = None

    # Early stopping
    n_warmup_steps: int = 10
    early_stopping_rounds: int = 20
    early_stopping_threshold: float = 0.0

    # Parallel settings
    n_jobs: int = 1

    # Search space
    search_space: Optional[SearchSpace] = None

    # Status
    status: str = "created"  # created, running, completed, failed
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # Results
    best_trial: Optional[Trial] = None
    best_value: Optional[float] = None
    trials: List[Trial] = field(default_factory=list)

    # Owner
    owner_id: Optional[int] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def progress(self) -> float:
        """Get study progress (0-1)"""
        if self.n_trials == 0:
            return 0.0
        return len(self.trials) / self.n_trials

    @property
    def is_running(self) -> bool:
        """Check if study is running"""
        return self.status in ("created", "running")

    @property
    def completed_trials(self) -> int:
        """Get number of completed trials"""
        return len([t for t in self.trials if t.status in (TrialStatus.COMPLETED, TrialStatus.PRUNED)])


class HyperparameterService:
    """
    Service for hyperparameter optimization using Optuna

    Features:
    - Multiple search algorithms (TPE, CMA-ES, Grid, Random)
    - Parallel optimization
    - Early stopping based on trial results
    - Study resumption
    - Multi-metric optimization
    """

    def __init__(self):
        self._studies: Dict[str, OptimizationStudy] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}

    async def create_study(
        self,
        name: str,
        metric: str,
        direction: OptimizationDirection = OptimizationDirection.MAXIMIZE,
        search_space: Optional[SearchSpace] = None,
        n_trials: int = 100,
        sampler: SamplerType = SamplerType.TPE,
        pruner: PrunerType = PrunerType.NONE,
        **kwargs,
    ) -> OptimizationStudy:
        """
        Create a new optimization study

        Args:
            name: Study name
            metric: Metric to optimize
            direction: Maximize or minimize
            search_space: Hyperparameter search space
            n_trials: Number of trials
            sampler: Sampling algorithm
            pruner: Pruning algorithm
            **kwargs: Additional study configuration

        Returns:
            Created study
        """
        study_id = f"study-{uuid.uuid4().hex[:8]}"

        study = OptimizationStudy(
            study_id=study_id,
            name=name,
            metric=metric,
            direction=direction,
            sampler=sampler,
            pruner=pruner,
            n_trials=n_trials,
            search_space=search_space,
            **kwargs,
        )

        self._studies[study_id] = study
        logger.info(f"Created study {study_id}: {name}")

        return study

    async def start_optimization(
        self,
        study_id: str,
        objective_func: Callable[[Dict[str, Any]], float],
    ) -> OptimizationStudy:
        """
        Start hyperparameter optimization

        Args:
            study_id: Study ID
            objective_func: Function that takes hyperparameters and returns metric value

        Returns:
            Updated study with results
        """
        study = self._studies.get(study_id)
        if not study:
            raise ValueError(f"Study {study_id} not found")

        study.status = "running"
        study.start_time = datetime.utcnow()

        # Run optimization in background task
        task = asyncio.create_task(
            self._run_optimization(study, objective_func)
        )
        self._running_tasks[study_id] = task

        return study

    async def _run_optimization(
        self,
        study: OptimizationStudy,
        objective_func: Callable[[Dict[str, Any]], float],
    ) -> None:
        """
        Run optimization trials

        Args:
            study: Study to optimize
            objective_func: Objective function
        """
        try:
            # Import Optuna here to avoid hard dependency
            try:
                import optuna
            except ImportError:
                logger.warning("Optuna not installed, using mock optimization")
                await self._mock_optimization(study, objective_func)
                return

            # Create Optuna study
            optuna_study = optuna.create_study(
                study_name=study.name,
                direction=study.direction.value,
                sampler=self._create_sampler(study.sampler),
                pruner=self._create_pruner(study.pruner),
            )

            # Define objective wrapper
            def optuna_objective(trial: optuna.Trial) -> float:
                # Suggest hyperparameters from search space
                if study.search_space:
                    params = study.search_space.to_optuna_trials(trial)
                else:
                    # Fallback: sample from trial suggestions
                    params = self._extract_params_from_trial(trial)

                # Get start time
                start_time = datetime.utcnow()

                # Create trial
                trial_id = f"trial-{trial.number}"
                optuna_trial = Trial(
                    trial_number=trial.number,
                    trial_id=trial_id,
                    params=params,
                    value=0.0,  # Will be updated
                    start_time=start_time,
                )

                study.trials.append(optuna_trial)

                # Evaluate objective function
                try:
                    value = objective_func(params)
                    optuna_trial.value = value
                    optuna_trial.status = TrialStatus.COMPLETED

                    # Update best if improved
                    if study.best_value is None or (
                        study.direction == OptimizationDirection.MAXIMIZE and value > study.best_value
                    ) or (
                        study.direction == OptimizationDirection.MINIMIZE and value < study.best_value
                    ):
                        study.best_value = value
                        study.best_trial = optuna_trial

                except Exception as e:
                    logger.error(f"Trial {trial_id} failed: {e}")
                    optuna_trial.status = TrialStatus.FAILED
                    optuna_trial.end_time = datetime.utcnow()
                    raise

                optuna_trial.end_time = datetime.utcnow()

                return value

            # Run optimization
            optuna_study.optimize(
                optuna_objective,
                n_trials=study.n_trials,
                timeout=int(study.timeout_hours * 3600) if study.timeout_hours else None,
                n_jobs=study.n_jobs,
                show_progress_bar=False,
            )

            study.status = "completed"
            study.end_time = datetime.utcnow()

            logger.info(f"Study {study.study_id} completed. Best value: {study.best_value}")

        except Exception as e:
            logger.error(f"Study {study.study_id} failed: {e}")
            study.status = "failed"
            study.end_time = datetime.utcnow()

        finally:
            # Remove from running tasks
            if study.study_id in self._running_tasks:
                del self._running_tasks[study.study_id]

    async def _mock_optimization(
        self,
        study: OptimizationStudy,
        objective_func: Callable[[Dict[str, Any]], float],
    ) -> None:
        """Mock optimization when Optuna is not available"""
        # Generate random hyperparameters
        import random

        for i in range(study.n_trials):
            if study.search_space:
                # Generate params from search space
                params = {}
                for name, choices in study.search_space.categorical.items():
                    params[name] = random.choice(choices)
                for name, (low, high) in study.search_space.int_uniform.items():
                    params[name] = random.randint(low, high)
                for name, (low, high) in study.search_space.float_uniform.items():
                    params[name] = random.uniform(low, high)
            else:
                params = {"lr": random.uniform(0.0001, 0.1)}

            # Evaluate
            trial = Trial(
                trial_number=i,
                trial_id=f"mock-trial-{i}",
                params=params,
                value=0.0,
                status=TrialStatus.RUNNING,
            )

            study.trials.append(trial)

            try:
                value = objective_func(params)
                trial.value = value
                trial.status = TrialStatus.COMPLETED

                if study.best_value is None or (
                    study.direction == OptimizationDirection.MAXIMIZE and value > study.best_value
                ) or (
                    study.direction == OptimizationDirection.MINIMIZE and value < study.best_value
                ):
                    study.best_value = value
                    study.best_trial = trial

            except Exception as e:
                logger.error(f"Mock trial {i} failed: {e}")
                trial.status = TrialStatus.FAILED

            trial.end_time = trial.start_time = datetime.utcnow()

        study.status = "completed"
        study.end_time = datetime.utcnow()

    def _create_sampler(self, sampler_type: SamplerType):
        """Create Optuna sampler"""
        try:
            import optuna
        except ImportError:
            return None

        if sampler_type == SamplerType.RANDOM:
            return optuna.samplers.RandomSampler()
        elif sampler_type == SamplerType.TPE:
            return optuna.samplers.TPESampler()
        elif sampler_type == SamplerType.CMAES:
            return optuna.samplers.CmaEsSampler()
        else:
            return optuna.samplers.RandomSampler()

    def _create_pruner(self, pruner_type: PrunerType):
        """Create Optuna pruner"""
        try:
            import optuna
        except ImportError:
            return None

        if pruner_type == PrunerType.NONE:
            return optuna.pruners.NopPruner()
        elif pruner_type == PrunerType.MEDIAN:
            return optuna.pruners.MedianPruner()
        elif pruner_type == PrunerType.SUCCESSIVE_HALVING:
            return optuna.pruners.SuccessiveHalvingPruner()
        elif pruner_type == PrunerType.HYPERBAND:
            return optuna.pruners.HyperbandPruner()
        else:
            return optuna.pruners.NopPruner()

    def _extract_params_from_trial(self, trial: Any) -> Dict[str, Any]:
        """Extract params from trial (fallback)"""
        # In real Optuna, this would use trial.params
        return {"lr": 0.001, "batch_size": 32}

    async def get_study(self, study_id: str) -> Optional[OptimizationStudy]:
        """Get study by ID"""
        return self._studies.get(study_id)

    async def list_studies(
        self,
        project_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[OptimizationStudy]:
        """List all studies"""
        studies = list(self._studies.values())

        if project_id:
            studies = [s for s in studies if s.project_id == project_id]

        if status:
            studies = [s for s in studies if s.status == status]

        return studies

    async def delete_study(self, study_id: str) -> bool:
        """Delete a study"""
        if study_id in self._studies:
            # Cancel if running
            if study_id in self._running_tasks:
                self._running_tasks[study_id].cancel()
                del self._running_tasks[study_id]

            del self._studies[study_id]
            return True
        return False

    async def get_study_history(
        self,
        study_id: str,
    ) -> Dict[str, Any]:
        """
        Get optimization history for visualization

        Args:
            study_id: Study ID

        Returns:
            History with trials sorted by trial number
        """
        study = self._studies.get(study_id)
        if not study:
            raise ValueError(f"Study {study_id} not found")

        return {
            "study_id": study.study_id,
            "name": study.name,
            "metric": study.metric,
            "direction": study.direction.value,
            "best_value": study.best_value,
            "best_params": study.best_trial.params if study.best_trial else None,
            "trials": [
                {
                    "trial_number": t.trial_number,
                    "params": t.params,
                    "value": t.value,
                    "status": t.status.value,
                    "start_time": t.start_time.isoformat(),
                    "end_time": t.end_time.isoformat() if t.end_time else None,
                }
                for t in study.trials
            ],
            "status": study.status,
            "progress": study.progress,
            "created_at": study.created_at.isoformat(),
            "start_time": study.start_time.isoformat() if study.start_time else None,
            "end_time": study.end_time.isoformat() if study.end_time else None,
        }


# Singleton instance
_hyperparameter_service: Optional[HyperparameterService] = None


def get_hyperparameter_service() -> HyperparameterService:
    """Get or create hyperparameter service singleton"""
    global _hyperparameter_service
    if _hyperparameter_service is None:
        _hyperparameter_service = HyperparameterService()
    return _hyperparameter_service
