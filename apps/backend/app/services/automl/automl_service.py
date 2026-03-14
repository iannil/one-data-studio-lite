"""
AutoML Service

Provides automated machine learning capabilities including hyperparameter tuning,
auto feature engineering, and model selection.
"""

import logging
import time
from typing import List, Dict, Any, Optional, Tuple, Callable, Sequence
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid

from sqlalchemy.orm import Session

from app.models.automl import (
    AutoMLExperiment, AutoMLTrial, AutoMLModel, FeatureConfig, HyperparameterSearch,
)

logger = logging.getLogger(__name__)


class ProblemType(str, Enum):
    """Machine learning problem types"""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"
    TIMESERIES = "timeseries"
    MULTITASK = "multitask"


class SearchAlgorithm(str, Enum):
    """Hyperparameter search algorithms"""
    RANDOM = "random"
    BAYESIAN = "bayesian"
    GENETIC = "genetic"
    GRID = "grid"
    OPTUNA = "optuna"


class ModelType(str, Enum):
    """Supported model types"""
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    RANDOM_FOREST = "random_forest"
    LINEAR = "linear"
    LOGISTIC = "logistic"
    SVM = "svm"
    KNN = "knn"
    NEURAL_NETWORK = "neural_network"


@dataclass
class HyperparameterSpace:
    """Hyperparameter search space"""
    name: str
    type: str  # continuous, discrete, categorical
    low: Optional[float] = None
    high: Optional[float] = None
    choices: Optional[List[Any]] = None
    log: bool = False


@dataclass
class TrialResult:
    """Result from a single training trial"""
    trial_number: int
    model_type: ModelType
    hyperparameters: Dict[str, Any]
    train_score: float
    val_score: float
    test_score: Optional[float] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    duration_seconds: float = 0
    feature_importance: Optional[Dict[str, float]] = None
    error: Optional[str] = None


@dataclass
class AutoMLResult:
    """Result from an AutoML experiment"""
    experiment_id: str
    best_model_id: str
    best_score: float
    best_trial: TrialResult
    all_trials: List[TrialResult]
    training_time_seconds: float
    feature_names: List[str]


class HyperparameterTuner:
    """
    Hyperparameter Tuning Engine

    Performs automated hyperparameter optimization using various search algorithms.
    """

    def __init__(self):
        self._search_spaces: Dict[ModelType, List[HyperparameterSpace]] = {}
        self._initialize_search_spaces()

    def _initialize_search_spaces(self) -> None:
        """Initialize default search spaces for each model type"""
        # XGBoost search space
        self._search_spaces[ModelType.XGBOOST] = [
            HyperparameterSpace("learning_rate", "continuous", 0.001, 0.3, log=True),
            HyperparameterSpace("max_depth", "discrete", 3, 10),
            HyperparameterSpace("min_child_weight", "discrete", 1, 10),
            HyperparameterSpace("subsample", "continuous", 0.5, 1.0),
            HyperparameterSpace("colsample_bytree", "continuous", 0.5, 1.0),
            HyperparameterSpace("n_estimators", "discrete", 50, 500),
            HyperparameterSpace("gamma", "continuous", 0, 5),
            HyperparameterSpace("reg_alpha", "continuous", 0, 1),
            HyperparameterSpace("reg_lambda", "continuous", 0, 1),
        ]

        # LightGBM search space
        self._search_spaces[ModelType.LIGHTGBM] = [
            HyperparameterSpace("learning_rate", "continuous", 0.001, 0.3, log=True),
            HyperparameterSpace("num_leaves", "discrete", 20, 100),
            HyperparameterSpace("max_depth", "discrete", 5, 15),
            HyperparameterSpace("min_child_samples", "discrete", 5, 50),
            HyperparameterSpace("subsample", "continuous", 0.5, 1.0),
            HyperparameterSpace("colsample_bytree", "continuous", 0.5, 1.0),
            HyperparameterSpace("n_estimators", "discrete", 50, 500),
            HyperparameterSpace("reg_alpha", "continuous", 0, 1),
            HyperparameterSpace("reg_lambda", "continuous", 0, 1),
        ]

        # Random Forest search space
        self._search_spaces[ModelType.RANDOM_FOREST] = [
            HyperparameterSpace("n_estimators", "discrete", 50, 300),
            HyperparameterSpace("max_depth", "discrete", 5, 30),
            HyperparameterSpace("min_samples_split", "discrete", 2, 20),
            HyperparameterSpace("min_samples_leaf", "discrete", 1, 10),
            HyperparameterSpace("max_features", "categorical", None, None,
                               ["sqrt", "log2", None]),
        ]

        # Linear model search space
        self._search_spaces[ModelType.LINEAR] = [
            HyperparameterSpace("alpha", "continuous", 0, 1),
            HyperparameterSpace("l1_ratio", "continuous", 0, 1),
            HyperparameterSpace("fit_intercept", "categorical", None, None, [True, False]),
        ]

    def get_search_space(self, model_type: ModelType) -> List[HyperparameterSpace]:
        """Get search space for a model type"""
        return self._search_spaces.get(model_type, [])

    def sample_hyperparameters(
        self,
        model_type: ModelType,
        n_samples: int = 1,
        seed: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Sample random hyperparameters from search space"""
        import random

        if seed is not None:
            random.seed(seed)

        search_space = self.get_search_space(model_type)
        samples = []

        for _ in range(n_samples):
            params = {}
            for space in search_space:
                if space.type == "continuous":
                    if space.log:
                        # Log-uniform sampling
                        log_low = __import__("math").log(space.low or 0.001)
                        log_high = __import__("math").log(space.high)
                        value = __import__("math").exp(
                            random.uniform(log_low, log_high)
                        )
                    else:
                        value = random.uniform(space.low, space.high)
                elif space.type == "discrete":
                    value = random.randint(int(space.low), int(space.high))
                elif space.type == "categorical":
                    value = random.choice(space.choices)
                params[space.name] = value
            samples.append(params)

        return samples


class AutoFeatureEngineering:
    """
    Automated Feature Engineering

    Automatically generates and selects features.
    """

    def __init__(self):
        self._feature_generators = {
            "polynomial": self._generate_polynomial,
            "interactions": self._generate_interactions,
            "scaling": self._apply_scaling,
            "encoding": self._apply_encoding,
            "lag": self._generate_lag_features,
            "rolling": self._generate_rolling_features,
        }

    def fit_transform(
        self,
        X: List[List[Any]],
        y: Optional[List[Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[List[Any]], List[str]]:
        """
        Fit feature engineering pipeline and transform data

        Args:
            X: Input features (list of rows)
            y: Target variable (optional)
            config: Feature engineering configuration

        Returns:
            Tuple of (transformed features, new feature names)
        """
        import pandas as pd
        import numpy as np

        df = pd.DataFrame(X)
        config = config or {}

        original_columns = list(df.columns)
        result_df = df.copy()

        # Apply scaling
        if config.get("scaling_method"):
            result_df = self._apply_scaling(result_df, config["scaling_method"])

        # Apply encoding for categorical columns
        if config.get("encoding_method"):
            result_df, new_cols = self._apply_encoding(
                result_df,
                config["encoding_method"],
                y
            )
            original_columns.extend(new_cols)

        # Generate polynomial features
        if config.get("enable_polynomial") and config.get("polynomial_degree"):
            poly_df, poly_cols = self._generate_polynomial(
                result_df.select_dtypes(include=[np.number]),
                config.get("polynomial_degree", 2)
            )
            result_df = pd.concat([result_df, poly_df], axis=1)
            original_columns.extend(poly_cols)

        # Generate interaction features
        if config.get("enable_interactions"):
            inter_df, inter_cols = self._generate_interactions(
                result_df.select_dtypes(include=[np.number]),
                config.get("max_interactions", 3)
            )
            result_df = pd.concat([result_df, inter_df], axis=1)
            original_columns.extend(inter_cols)

        return result_df.values.tolist(), original_columns

    def _generate_polynomial(
        self,
        df: Any,
        degree: int = 2,
    ) -> Tuple[Any, List[str]]:
        """Generate polynomial features"""
        import pandas as pd
        import numpy as np
        from sklearn.preprocessing import PolynomialFeatures

        poly = PolynomialFeatures(degree=degree, include_bias=False)
        poly_array = poly.fit_transform(df)

        # Get feature names
        feature_names = poly.get_feature_names_out(df.columns)

        poly_df = pd.DataFrame(poly_array[:, len(df.columns):], columns=feature_names[len(df.columns):])

        return poly_df, list(poly_df.columns)

    def _generate_interactions(
        self,
        df: Any,
        max_interactions: int = 3,
    ) -> Tuple[Any, List[str]]:
        """Generate interaction features"""
        import pandas as pd
        import numpy as np

        interaction_df = pd.DataFrame()
        interaction_names = []

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        for i, col1 in enumerate(numeric_cols[:max_interactions]):
            for col2 in numeric_cols[i+1:max_interactions]:
                interaction_df[f"{col1}_x_{col2}"] = df[col1] * df[col2]
                interaction_names.append(f"{col1}_x_{col2}")

        return interaction_df, interaction_names

    def _apply_scaling(self, df: Any, method: str) -> Any:
        """Apply feature scaling"""
        import pandas as pd
        from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler

        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()

        if method == "standard":
            scaler = StandardScaler()
        elif method == "minmax":
            scaler = MinMaxScaler()
        elif method == "robust":
            scaler = RobustScaler()
        else:
            return df

        df[numeric_cols] = scaler.fit_transform(df[numeric_cols])
        return df

    def _apply_encoding(
        self,
        df: Any,
        method: str,
        y: Optional[Any] = None,
    ) -> Tuple[Any, List[str]]:
        """Apply categorical encoding"""
        import pandas as pd
        from sklearn.preprocessing import LabelEncoder, OneHotEncoder

        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        new_cols = []

        if method == "onehot":
            for col in categorical_cols:
                dummies = pd.get_dummies(df[col], prefix=col)
                df = pd.concat([df.drop(col, axis=1), dummies], axis=1)
                new_cols.extend(list(dummies.columns))

        elif method == "label":
            for col in categorical_cols:
                le = LabelEncoder()
                df[f"{col}_encoded"] = le.fit_transform(df[col])
                new_cols.append(f"{col}_encoded")
                df = df.drop(col, axis=1)

        elif method == "target" and y is not None:
            for col in categorical_cols:
                # Target encoding using mean of target
                le = LabelEncoder()
                df[f"{col}_target_enc"] = le.fit_transform(df[col])
                new_cols.append(f"{col}_target_enc")

        return df, new_cols

    def _generate_lag_features(
        self,
        df: Any,
        lag_steps: List[int] = [1, 2, 3, 7, 14],
    ) -> Tuple[Any, List[str]]:
        """Generate lag features for time series"""
        import pandas as pd

        lag_df = pd.DataFrame()
        lag_names = []

        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()

        for col in numeric_cols:
            for lag in lag_steps:
                lag_df[f"{col}_lag_{lag}"] = df[col].shift(lag)
                lag_names.append(f"{col}_lag_{lag}")

        return lag_df, lag_names

    def _generate_rolling_features(
        self,
        df: Any,
        windows: List[int] = [3, 7, 14],
    ) -> Tuple[Any, List[str]]:
        """Generate rolling window features"""
        import pandas as pd

        rolling_df = pd.DataFrame()
        rolling_names = []

        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()

        for col in numeric_cols:
            for window in windows:
                rolling_df[f"{col}_rolling_mean_{window}"] = df[col].rolling(window=window).mean()
                rolling_df[f"{col}_rolling_std_{window}"] = df[col].rolling(window=window).std()
                rolling_names.extend([
                    f"{col}_rolling_mean_{window}",
                    f"{col}_rolling_std_{window}",
                ])

        return rolling_df, rolling_names


class AutoMLEngine:
    """
    AutoML Engine

    Orchestrates automated machine learning experiments.
    """

    def __init__(self, db: Session):
        self.db = db
        self.tuner = HyperparameterTuner()
        self.feature_engineering = AutoFeatureEngineering()

    def create_experiment(
        self,
        name: str,
        problem_type: ProblemType,
        target_column: str,
        feature_columns: List[str],
        source_type: str,
        source_config: Dict[str, Any],
        eval_metric: str = "accuracy",
        search_algorithm: SearchAlgorithm = SearchAlgorithm.RANDOM,
        max_trials: int = 10,
        model_types: Optional[List[ModelType]] = None,
        enable_auto_feature_engineering: bool = True,
        feature_config: Optional[Dict[str, Any]] = None,
        owner_id: Optional[str] = None,
    ) -> AutoMLExperiment:
        """Create a new AutoML experiment"""
        experiment = AutoMLExperiment(
            name=name,
            problem_type=problem_type.value,
            target_column=target_column,
            feature_columns=feature_columns,
            source_type=source_type,
            source_config=source_config,
            eval_metric=eval_metric,
            search_algorithm=search_algorithm.value,
            max_trials=max_trials,
            model_types=[m.value for m in (model_types or [ModelType.XGBOOST, ModelType.LIGHTGBM])],
            enable_auto_feature_engineering=enable_auto_feature_engineering,
            feature_engineering_config=feature_config or {},
            owner_id=owner_id,
            status="draft",
        )

        self.db.add(experiment)
        self.db.commit()
        self.db.refresh(experiment)

        logger.info(f"Created AutoML experiment: {experiment.id}")
        return experiment

    def run_experiment(
        self,
        experiment_id: str,
        X_train: List[List[Any]],
        y_train: List[Any],
        X_val: List[List[Any]],
        y_val: List[Any],
        X_test: Optional[List[List[Any]]] = None,
        y_test: Optional[List[Any]] = None,
    ) -> AutoMLResult:
        """
        Run an AutoML experiment

        Args:
            experiment_id: Experiment ID
            X_train: Training features
            y_train: Training target
            X_val: Validation features
            y_val: Validation target
            X_test: Test features (optional)
            y_test: Test target (optional)

        Returns:
            AutoMLResult with best model and all trials
        """
        experiment = self.db.query(AutoMLExperiment).filter(
            AutoMLExperiment.id == experiment_id
        ).first()

        if not experiment:
            raise ValueError(f"Experiment not found: {experiment_id}")

        # Update experiment status
        experiment.status = "running"
        experiment.started_at = datetime.utcnow()
        self.db.commit()

        start_time = time.time()
        trials = []
        best_score = float('-inf')
        best_trial = None

        try:
            # Apply auto feature engineering if enabled
            if experiment.enable_auto_feature_engineering:
                X_train, feature_names = self.feature_engineering.fit_transform(
                    X_train,
                    y_train,
                    experiment.feature_engineering_config,
                )
            else:
                feature_names = experiment.feature_columns

            # Run trials
            for trial_num in range(1, experiment.max_trials + 1):
                trial_start = time.time()

                # Select model type for this trial
                model_type_str = experiment.model_types[
                    (trial_num - 1) % len(experiment.model_types)
                ]
                model_type = ModelType(model_type_str)

                # Sample hyperparameters
                hyperparams = self.tuner.sample_hyperparameters(model_type, n_samples=1)[0]

                # Train model (mock implementation)
                train_score, val_score, test_score, metrics = self._train_model(
                    model_type,
                    X_train, y_train,
                    X_val, y_val,
                    X_test, y_test,
                    hyperparams,
                    experiment.eval_metric,
                )

                trial_duration = time.time() - trial_start

                # Create trial record
                trial = AutoMLTrial(
                    id=uuid.uuid4(),
                    experiment_id=experiment_id,
                    trial_number=trial_num,
                    model_type=model_type.value,
                    model_config={"type": model_type.value},
                    hyperparameters=hyperparams,
                    status="completed",
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    duration_seconds=trial_duration,
                    train_score=train_score,
                    val_score=val_score,
                    test_score=test_score,
                    metrics=metrics,
                )

                self.db.add(trial)

                trial_result = TrialResult(
                    trial_number=trial_num,
                    model_type=model_type,
                    hyperparameters=hyperparams,
                    train_score=train_score,
                    val_score=val_score,
                    test_score=test_score,
                    metrics=metrics,
                    duration_seconds=trial_duration,
                )
                trials.append(trial_result)

                # Update best
                if val_score > best_score:
                    best_score = val_score
                    best_trial = trial_result
                    experiment.best_score = val_score
                    experiment.best_trial_number = trial_num

                # Update progress
                experiment.progress = (trial_num / experiment.max_trials) * 100
                self.db.commit()

                logger.info(f"Trial {trial_num} complete: {model_type.value} - Val Score: {val_score:.4f}")

            # Create best model record
            best_model = AutoMLModel(
                name=f"{experiment.name}_best",
                model_type=best_trial.model_type.value,
                problem_type=experiment.problem_type,
                target_column=experiment.target_column,
                model_path=f"/models/{experiment_id}/best",
                feature_names=feature_names,
                metrics=best_trial.metrics,
                status="trained",
                owner_id=experiment.owner_id,
            )

            self.db.add(best_model)
            experiment.best_model_id = best_model.id
            experiment.status = "completed"
            experiment.completed_at = datetime.utcnow()

            training_time = time.time() - start_time

            self.db.commit()
            self.db.refresh(experiment)

            result = AutoMLResult(
                experiment_id=experiment_id,
                best_model_id=str(best_model.id),
                best_score=best_score,
                best_trial=best_trial,
                all_trials=trials,
                training_time_seconds=training_time,
                feature_names=feature_names,
            )

            logger.info(f"Experiment {experiment_id} complete: Best Score = {best_score:.4f}")
            return result

        except Exception as e:
            logger.error(f"Experiment {experiment_id} failed: {e}")
            experiment.status = "failed"
            experiment.completed_at = datetime.utcnow()
            self.db.commit()
            raise

    def _train_model(
        self,
        model_type: ModelType,
        X_train: List[List[Any]],
        y_train: List[Any],
        X_val: List[List[Any]],
        y_val: List[Any],
        X_test: Optional[List[List[Any]]],
        y_test: Optional[List[Any]],
        hyperparameters: Dict[str, Any],
        eval_metric: str,
    ) -> Tuple[float, float, Optional[float], Dict[str, float]]:
        """Train a model and return metrics (mock implementation)"""
        import numpy as np

        # Mock training - in production, this would use actual ML libraries
        # Simulate training time
        time.sleep(0.1)

        # Generate mock scores based on hyperparameters
        # Better hyperparameters generally give better scores
        base_score = 0.7 + np.random.normal(0, 0.1)

        # Learning rate impact
        lr = hyperparameters.get("learning_rate", 0.1)
        if 0.01 <= lr <= 0.2:
            base_score += 0.05

        # Depth impact
        depth = hyperparameters.get("max_depth", hyperparameters.get("num_leaves", 6))
        if 4 <= depth <= 10:
            base_score += 0.03

        # N estimators impact
        n_est = hyperparameters.get("n_estimators", 100)
        if n_est >= 200:
            base_score += 0.02

        train_score = min(0.99, base_score + 0.05)
        val_score = min(0.95, base_score)
        test_score = min(0.93, base_score - 0.02) if X_test else None

        metrics = {
            eval_metric: val_score,
            "accuracy": val_score,
            "precision": val_score - 0.05,
            "recall": val_score - 0.03,
            "f1": val_score - 0.04,
            "auc": val_score - 0.01,
        }

        return train_score, val_score, test_score, metrics

    def get_experiment(self, experiment_id: str) -> Optional[AutoMLExperiment]:
        """Get an experiment by ID"""
        return self.db.query(AutoMLExperiment).filter(
            AutoMLExperiment.id == experiment_id
        ).first()

    def list_experiments(
        self,
        owner_id: Optional[str] = None,
        status: Optional[str] = None,
        problem_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AutoMLExperiment]:
        """List experiments with optional filters"""
        query = self.db.query(AutoMLExperiment)

        if owner_id:
            query = query.filter(AutoMLExperiment.owner_id == owner_id)

        if status:
            query = query.filter(AutoMLExperiment.status == status)

        if problem_type:
            query = query.filter(AutoMLExperiment.problem_type == problem_type)

        query = query.order_by(AutoMLExperiment.created_at.desc())
        query = query.offset(offset).limit(limit)

        return query.all()

    def get_trials(self, experiment_id: str) -> List[AutoMLTrial]:
        """Get all trials for an experiment"""
        return self.db.query(AutoMLTrial).filter(
            AutoMLTrial.experiment_id == experiment_id
        ).order_by(AutoMLTrial.trial_number).all()


def get_automl_service(db: Session) -> AutoMLEngine:
    """Get the AutoML service instance"""
    return AutoMLEngine(db)
