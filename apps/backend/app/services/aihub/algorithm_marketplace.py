"""
Algorithm Marketplace Service

Provides algorithm discovery, subscription, and deployment integration.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AlgorithmCategory(str, Enum):
    """Algorithm categories"""
    COMPUTER_VISION = "computer_vision"
    NLP = "nlp"
    RECOMMENDATION = "recommendation"
    TIME_SERIES = "time_series"
    ANOMALY_DETECTION = "anomaly_detection"
    CLUSTERING = "clustering"
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    REINFORCEMENT_LEARNING = "reinforcement_learning"
    GENERATIVE_AI = "generative_ai"
    MULTIMODAL = "multimodal"
    GRAPH = "graph"
    TABULAR = "tabular"
    AUDIO = "audio"
    CUSTOM = "custom"


class AlgorithmFramework(str, Enum):
    """ML/DL frameworks"""
    PYTORCH = "pytorch"
    TENSORFLOW = "tensorflow"
    KERAS = "keras"
    SKLEARN = "sklearn"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    CATBOOST = "catboost"
    HUGGINGFACE = "huggingface"
    ONNX = "onnx"
    OPENVINO = "openvino"
    TENSORRT = "tensorrt"
    JAX = "jax"
    FLAX = "flax"
    CUSTOM = "custom"


class AlgorithmLicense(str, Enum):
    """License types"""
    APACHE_2_0 = "apache-2.0"
    MIT = "mit"
    GPL_3_0 = "gpl-3.0"
    BSD_3_CLAUSE = "bsd-3-clause"
    LGPL = "lgpl"
    MPL_2_0 = "mpl-2.0"
    CUSTOM = "custom"
    PROPRIETARY = "proprietary"


@dataclass
class AlgorithmAuthor:
    """Algorithm author information"""
    name: str
    email: Optional[str] = None
    organization: Optional[str] = None
    website: Optional[str] = None


@dataclass
class AlgorithmMetric:
    """Algorithm performance metric"""
    name: str
    value: float
    dataset: Optional[str] = None
    unit: Optional[str] = None


@dataclass
class AlgorithmDependency:
    """Algorithm dependency"""
    name: str
    version: Optional[str] = None
    source: str = "pypi"  # pypi, conda, git, local


@dataclass
class AlgorithmHyperparameter:
    """Algorithm hyperparameter"""
    name: str
    type: str  # int, float, str, bool, categorical
    default_value: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    choices: Optional[List[str]] = None
    description: Optional[str] = None


@dataclass
class AlgorithmVersion:
    """Algorithm version"""
    version: str
    created_at: datetime
    changelog: Optional[str] = None
    download_url: Optional[str] = None
    checksum: Optional[str] = None
    file_size_bytes: Optional[int] = None
    dependencies: List[AlgorithmDependency] = field(default_factory=list)
    is_deprecated: bool = False
    tags: List[str] = field(default_factory=list)


@dataclass
class Algorithm:
    """Algorithm definition"""
    id: str
    name: str
    display_name: str
    description: str
    category: AlgorithmCategory
    framework: AlgorithmFramework
    license: AlgorithmLicense
    author: AlgorithmAuthor
    repository_url: Optional[str] = None
    documentation_url: Optional[str] = None
    paper_url: Optional[str] = None
    icon_url: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    versions: List[AlgorithmVersion] = field(default_factory=list)
    latest_version: str = "1.0.0"
    metrics: List[AlgorithmMetric] = field(default_factory=list)
    hyperparameters: List[AlgorithmHyperparameter] = field(default_factory=list)
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    requirements: List[str] = field(default_factory=list)
    is_public: bool = True
    is_verified: bool = False
    downloads: int = 0
    rating: float = 0.0
    rating_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class AlgorithmSubscription:
    """Algorithm subscription"""
    subscription_id: str
    algorithm_id: str
    user_id: str
    subscribed_at: datetime
    version: Optional[str] = None
    auto_update: bool = True
    is_active: bool = True


@dataclass
class AlgorithmDeploymentConfig:
    """Algorithm deployment configuration"""
    algorithm_id: str
    version: str
    instance_type: str  # cpu, gpu, gpu-multi
    replicas: int = 1
    resources: Dict[str, str] = field(default_factory=dict)
    environment_vars: Dict[str, str] = field(default_factory=dict)
    mount_paths: Dict[str, str] = field(default_factory=dict)


@dataclass
class AlgorithmDeployment:
    """Algorithm deployment instance"""
    deployment_id: str
    algorithm_id: str
    config: AlgorithmDeploymentConfig
    status: str  # pending, running, stopped, failed
    created_at: datetime
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    endpoint: Optional[str] = None
    logs: List[str] = field(default_factory=list)


class AlgorithmMarketplace:
    """
    Algorithm marketplace service

    Manages algorithm discovery, subscription, and deployment.
    """

    def __init__(self, db: Session, catalog_path: Optional[str] = None):
        self.db = db
        self.catalog_path = Path(catalog_path or "/opt/aihub/algorithms")
        self._algorithms: Dict[str, Algorithm] = {}
        self._subscriptions: Dict[str, AlgorithmSubscription] = {}
        self._deployments: Dict[str, AlgorithmDeployment] = {}
        self._load_catalog()

    def _load_catalog(self):
        """Load algorithm catalog"""
        # In production, this would load from database or file system
        # For now, initialize with some built-in algorithms
        self._initialize_builtin_algorithms()

    def _initialize_builtin_algorithms(self):
        """Initialize built-in algorithms"""
        builtin_algorithms = [
            # Computer Vision
            Algorithm(
                id="resnet50",
                name="resnet50",
                display_name="ResNet-50",
                description="Deep residual network for image classification",
                category=AlgorithmCategory.COMPUTER_VISION,
                framework=AlgorithmFramework.PYTORCH,
                license=AlgorithmLicense.APACHE_2_0,
                author=AlgorithmAuthor(
                    name="Kaiming He",
                    organization="Facebook AI Research"
                ),
                repository_url="https://github.com/pytorch/vision",
                tags=["image-classification", "cnn", "pretrained"],
                versions=[
                    AlgorithmVersion(version="1.0", created_at=datetime.now())
                ],
                metrics=[
                    AlgorithmMetric(name="Top-1 Accuracy", value=76.13, dataset="ImageNet"),
                    AlgorithmMetric(name="Top-5 Accuracy", value=92.86, dataset="ImageNet"),
                ],
                hyperparameters=[
                    AlgorithmHyperparameter("num_classes", "int", 1000, min_value=1, description="Number of output classes"),
                    AlgorithmHyperparameter("pretrained", "bool", True, description="Use pretrained weights"),
                ],
            ),
            # NLP
            Algorithm(
                id="bert-base",
                name="bert-base",
                display_name="BERT Base",
                description="Bidirectional Encoder Representations from Transformers",
                category=AlgorithmCategory.NLP,
                framework=AlgorithmFramework.HUGGINGFACE,
                license=AlgorithmLicense.APACHE_2_0,
                author=AlgorithmAuthor(
                    name="Jacob Devlin",
                    organization="Google AI Language"
                ),
                repository_url="https://github.com/google-research/bert",
                tags=["transformer", "pretrained", "language-model"],
                versions=[
                    AlgorithmVersion(version="1.0", created_at=datetime.now())
                ],
                metrics=[
                    AlgorithmMetric(name="GLUE Score", value=78.2, dataset="GLUE"),
                ],
                hyperparameters=[
                    AlgorithmHyperparameter("num_labels", "int", 2, min_value=1),
                    AlgorithmHyperparameter("max_length", "int", 512, min_value=1),
                ],
            ),
            # Clustering
            Algorithm(
                id="kmeans",
                name="kmeans",
                display_name="K-Means Clustering",
                description="Unsupervised clustering algorithm",
                category=AlgorithmCategory.CLUSTERING,
                framework=AlgorithmFramework.SKLEARN,
                license=AlgorithmLicense.BSD_3_CLAUSE,
                author=AlgorithmAuthor(
                    organization="scikit-learn"
                ),
                tags=["clustering", "unsupervised", "classic"],
                versions=[
                    AlgorithmVersion(version="1.0", created_at=datetime.now())
                ],
                hyperparameters=[
                    AlgorithmHyperparameter("n_clusters", "int", 8, min_value=1, description="Number of clusters"),
                    AlgorithmHyperparameter("algorithm", "str", "auto", choices=["auto", "full", "elkan"]),
                    AlgorithmHyperparameter("max_iter", "int", 300, min_value=1),
                ],
            ),
            # XGBoost
            Algorithm(
                id="xgboost-classifier",
                name="xgboost-classifier",
                display_name="XGBoost Classifier",
                description="Gradient boosting tree classifier",
                category=AlgorithmCategory.CLASSIFICATION,
                framework=AlgorithmFramework.XGBOOST,
                license=AlgorithmLicense.APACHE_2_0,
                author=AlgorithmAuthor(
                    name="Tianqi Chen",
                    organization="University of Washington"
                ),
                repository_url="https://github.com/dmlc/xgboost",
                tags=["boosting", "tree", "tabular"],
                versions=[
                    AlgorithmVersion(version="1.7.0", created_at=datetime.now())
                ],
                hyperparameters=[
                    AlgorithmHyperparameter("max_depth", "int", 6, min_value=1, max_value=20),
                    AlgorithmHyperparameter("learning_rate", "float", 0.3, min_value=0.0, max_value=1.0),
                    AlgorithmHyperparameter("n_estimators", "int", 100, min_value=1),
                    AlgorithmHyperparameter("subsample", "float", 1.0, min_value=0.0, max_value=1.0),
                ],
            ),
            # Anomaly Detection
            Algorithm(
                id="isolation-forest",
                name="isolation-forest",
                display_name="Isolation Forest",
                description="Anomaly detection using isolation forest",
                category=AlgorithmCategory.ANOMALY_DETECTION,
                framework=AlgorithmFramework.SKLEARN,
                license=AlgorithmLicense.BSD_3_CLAUSE,
                author=AlgorithmAuthor(
                    name="Fei Tony Liu",
                    organization="Monash University"
                ),
                tags=["anomaly", "unsupervised", "forest"],
                versions=[
                    AlgorithmVersion(version="1.0", created_at=datetime.now())
                ],
                hyperparameters=[
                    AlgorithmHyperparameter("n_estimators", "int", 100, min_value=1),
                    AlgorithmHyperparameter("contamination", "float", 0.1, min_value=0.0, max_value=0.5),
                    AlgorithmHyperparameter("max_samples", "int", 256, min_value=1),
                ],
            ),
            # Time Series
            Algorithm(
                id="prophet",
                name="prophet",
                display_name="Prophet",
                description="Time series forecasting by Facebook",
                category=AlgorithmCategory.TIME_SERIES,
                framework=AlgorithmFramework.CUSTOM,
                license=AlgorithmLicense.MIT,
                author=AlgorithmAuthor(
                    organization="Meta"
                ),
                repository_url="https://github.com/facebook/prophet",
                tags=["forecasting", "time-series", "business"],
                versions=[
                    AlgorithmVersion(version="1.1.4", created_at=datetime.now())
                ],
                hyperparameters=[
                    AlgorithmHyperparameter("growth", "str", "linear", choices=["linear", "logistic"]),
                    AlgorithmHyperparameter("yearly_seasonality", "bool", True),
                    AlgorithmHyperparameter("weekly_seasonality", "bool", True),
                    AlgorithmHyperparameter("daily_seasonality", "bool", False),
                ],
            ),
            # Generative AI
            Algorithm(
                id="stable-diffusion",
                name="stable-diffusion",
                display_name="Stable Diffusion",
                description="Text-to-image diffusion model",
                category=AlgorithmCategory.GENERATIVE_AI,
                framework=AlgorithmFramework.PYTORCH,
                license=AlgorithmLicense.CUSTOM,
                author=AlgorithmAuthor(
                    organization="Stability AI"
                ),
                repository_url="https://github.com/Stability-AI/stablediffusion",
                tags=["diffusion", "text-to-image", "generation"],
                versions=[
                    AlgorithmVersion(version="2.1", created_at=datetime.now())
                ],
                is_verified=True,
                rating=4.8,
                rating_count=1250,
            ),
            # Recommendation
            Algorithm(
                id="ncf",
                name="ncf",
                display_name="Neural Collaborative Filtering",
                description="Neural network for collaborative filtering",
                category=AlgorithmCategory.RECOMMENDATION,
                framework=AlgorithmFramework.PYTORCH,
                license=AlgorithmLicense.MIT,
                author=AlgorithmAuthor(
                    organization="Facebook AI Research"
                ),
                repository_url="https://github.com/facebookresearch/recommenders",
                tags=["recommendation", "collaborative-filtering", "neural"],
                versions=[
                    AlgorithmVersion(version="1.0", created_at=datetime.now())
                ],
                hyperparameters=[
                    AlgorithmHyperparameter("embedding_dim", "int", 64, min_value=8, max_value=256),
                    AlgorithmHyperparameter("learning_rate", "float", 0.001, min_value=0.0001, max_value=0.1),
                ],
            ),
        ]

        for algo in builtin_algorithms:
            self._algorithms[algo.id] = algo

    async def list_algorithms(
        self,
        category: Optional[AlgorithmCategory] = None,
        framework: Optional[AlgorithmFramework] = None,
        search: Optional[str] = None,
        tags: Optional[List[str]] = None,
        verified_only: bool = False,
        limit: int = 100,
    ) -> List[Algorithm]:
        """
        List algorithms matching criteria

        Args:
            category: Filter by category
            framework: Filter by framework
            search: Search in name/description
            tags: Filter by tags
            verified_only: Only verified algorithms
            limit: Max results

        Returns:
            List of matching algorithms
        """
        algorithms = list(self._algorithms.values())

        if category:
            algorithms = [a for a in algorithms if a.category == category]
        if framework:
            algorithms = [a for a in algorithms if a.framework == framework]
        if tags:
            algorithms = [a for a in algorithms if any(t in a.tags for t in tags)]
        if verified_only:
            algorithms = [a for a in algorithms if a.is_verified]

        if search:
            search_lower = search.lower()
            algorithms = [
                a for a in algorithms
                if search_lower in a.name.lower() or
                search_lower in a.display_name.lower() or
                search_lower in a.description.lower()
            ]

        return algorithms[:limit]

    async def get_algorithm(self, algorithm_id: str) -> Optional[Algorithm]:
        """Get algorithm by ID"""
        return self._algorithms.get(algorithm_id)

    async def subscribe_algorithm(
        self,
        algorithm_id: str,
        user_id: str,
        version: Optional[str] = None,
        auto_update: bool = True,
    ) -> Optional[AlgorithmSubscription]:
        """Subscribe to an algorithm"""
        algorithm = await self.get_algorithm(algorithm_id)
        if not algorithm:
            return None

        subscription_id = f"sub-{algorithm_id}-{user_id}"

        subscription = AlgorithmSubscription(
            subscription_id=subscription_id,
            algorithm_id=algorithm_id,
            user_id=user_id,
            subscribed_at=datetime.now(),
            version=version or algorithm.latest_version,
            auto_update=auto_update,
        )

        self._subscriptions[subscription_id] = subscription

        # Increment download counter
        algorithm.downloads += 1

        return subscription

    async def unsubscribe_algorithm(self, subscription_id: str) -> bool:
        """Unsubscribe from an algorithm"""
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
            return True
        return False

    async def list_subscriptions(
        self,
        user_id: str,
    ) -> List[AlgorithmSubscription]:
        """List user's algorithm subscriptions"""
        return [
            s for s in self._subscriptions.values()
            if s.user_id == user_id
        ]

    async def deploy_algorithm(
        self,
        algorithm_id: str,
        user_id: str,
        config: AlgorithmDeploymentConfig,
    ) -> Optional[AlgorithmDeployment]:
        """Deploy an algorithm"""
        algorithm = await self.get_algorithm(algorithm_id)
        if not algorithm:
            return None

        deployment_id = f"dep-{algorithm_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        deployment = AlgorithmDeployment(
            deployment_id=deployment_id,
            algorithm_id=algorithm_id,
            config=config,
            status="pending",
            created_at=datetime.now(),
        )

        self._deployments[deployment_id] = deployment

        # Start deployment asynchronously
        # In production, this would interact with K8s/Docker

        return deployment

    async def get_deployment(self, deployment_id: str) -> Optional[AlgorithmDeployment]:
        """Get deployment by ID"""
        return self._deployments.get(deployment_id)

    async def list_deployments(
        self,
        user_id: Optional[str] = None,
        algorithm_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[AlgorithmDeployment]:
        """List deployments"""
        deployments = list(self._deployments.values())

        if user_id:
            deployments = [d for d in deployments if d.config.user_id == user_id]
        if algorithm_id:
            deployments = [d for d in deployments if d.algorithm_id == algorithm_id]
        if status:
            deployments = [d for d in deployments if d.status == status]

        return deployments

    async def get_algorithm_versions(
        self,
        algorithm_id: str,
    ) -> List[AlgorithmVersion]:
        """Get all versions of an algorithm"""
        algorithm = await self.get_algorithm(algorithm_id)
        return algorithm.versions if algorithm else []

    async def rate_algorithm(
        self,
        algorithm_id: str,
        user_id: str,
        rating: float,
    ) -> bool:
        """Rate an algorithm (1-5)"""
        if not 1 <= rating <= 5:
            return False

        algorithm = await self.get_algorithm(algorithm_id)
        if not algorithm:
            return False

        # Simple rating update (in production, would track per-user ratings)
        algorithm.rating_count += 1
        algorithm.rating = ((algorithm.rating * (algorithm.rating_count - 1)) + rating) / algorithm.rating_count

        return True

    async def search_by_use_case(
        self,
        use_case: str,
        limit: int = 10,
    ) -> List[Algorithm]:
        """Search algorithms by use case description"""
        # Use keyword matching and category mapping
        use_case_lower = use_case.lower()

        # Keyword to category mapping
        category_keywords = {
            AlgorithmCategory.COMPUTER_VISION: ["image", "video", "vision", "visual", "object detection", "segmentation"],
            AlgorithmCategory.NLP: ["text", "language", "nlp", "sentiment", "translation", "summarization"],
            AlgorithmCategory.TIME_SERIES: ["forecast", "prediction", "time series", "temporal"],
            AlgorithmCategory.ANOMALY_DETECTION: ["anomaly", "outlier", "fraud", "detection"],
            AlgorithmCategory.CLUSTERING: ["cluster", "group", "segment"],
            AlgorithmCategory.CLASSIFICATION: ["classify", "category", "class"],
            AlgorithmCategory.RECOMMENDATION: ["recommend", "personalize", "ranking"],
            AlgorithmCategory.GENERATIVE_AI: ["generate", "generative", "creation", "synthesis"],
        }

        matching_algorithms = []

        for algo in self._algorithms.values():
            # Check direct keyword match
            if any(kw in use_case_lower for kw in
                   [algo.name] + algo.tags + algo.description.split()):
                matching_algorithms.append(algo)
                continue

            # Check category keywords
            for cat, keywords in category_keywords.items():
                if algo.category == cat and any(kw in use_case_lower for kw in keywords):
                    matching_algorithms.append(algo)
                    break

        return matching_algorithms[:limit]

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get all categories with counts"""
        category_counts = {}
        for algo in self._algorithms.values():
            cat = algo.category.value
            if cat not in category_counts:
                category_counts[cat] = 0
            category_counts[cat] += 1

        return [
            {"name": cat, "count": count, "display_name": cat.replace("_", " ").title()}
            for cat, count in sorted(category_counts.items())
        ]

    async def get_frameworks(self) -> List[str]:
        """Get all available frameworks"""
        frameworks = set(algo.framework.value for algo in self._algorithms.values())
        return sorted(frameworks)


# Singleton
_marketplace: Optional[AlgorithmMarketplace] = None


def get_algorithm_marketplace(db: Session, catalog_path: Optional[str] = None) -> AlgorithmMarketplace:
    """Get or create the algorithm marketplace instance"""
    return AlgorithmMarketplace(db, catalog_path)
