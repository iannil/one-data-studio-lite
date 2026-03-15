"""
Model Application Marketplace Service

Provides model application templates and deployment management.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AppCategory(str, Enum):
    """Application categories"""
    CHATBOT = "chatbot"
    IMAGE_GENERATION = "image_generation"
    TEXT_GENERATION = "text_generation"
    VOICE_ASSISTANT = "voice_assistant"
    RECOMMENDATION = "recommendation"
    SEARCH = "search"
    ANALYTICS = "analytics"
    MONITORING = "monitoring"
    AUTOMATION = "automation"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    CODE_ASSISTANT = "code_assistant"
    CUSTOM = "custom"


class AppStatus(str, Enum):
    """Application status"""
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class DeploymentStatus(str, Enum):
    """Deployment status"""
    DRAFT = "draft"
    PENDING = "pending"
    BUILDING = "building"
    DEPLOYING = "deploying"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    SCALING = "scaling"


@dataclass
class AppResource:
    """Resource requirement"""
    resource_type: str  # cpu, memory, gpu, storage
    request: str
    limit: str


@dataclass
class AppEnvironment:
    """Environment variable"""
    name: str
    value: Optional[str] = None
    secret: bool = False
    required: bool = True


@dataclass
class AppVolume:
    """Storage volume"""
    name: str
    path: str
    size_gb: int
    storage_class: str = "standard"


@dataclass
class AppPort:
    """Port configuration"""
    port: int
    protocol: str = "tcp"
    service: bool = True  # Expose as service


@dataclass
class AppHealthCheck:
    """Health check configuration"""
    path: str = "/health"
    interval_seconds: int = 30
    timeout_seconds: int = 5
    failure_threshold: int = 3
    success_threshold: int = 1


@dataclass
class AppScalingPolicy:
    """Auto-scaling policy"""
    min_replicas: int = 1
    max_replicas: int = 10
    target_cpu_utilization: Optional[int] = None
    target_memory_utilization: Optional[int] = None
    target_requests_per_second: Optional[int] = None


@dataclass
class AppTemplate:
    """Application template"""
    id: str
    name: str
    display_name: str
    description: str
    category: AppCategory
    icon_url: Optional[str]
    author: str
    version: str
    
    # Model configuration
    model_id: Optional[str] = None  # Reference to algorithm or model
    model_version: Optional[str] = None
    
    # Container configuration
    image: Optional[str] = None
    build_context: Optional[str] = None
    
    # Resources
    resources: List[AppResource] = field(default_factory=list)
    
    # Configuration
    environments: List[AppEnvironment] = field(default_factory=list)
    volumes: List[AppVolume] = field(default_factory=list)
    ports: List[AppPort] = field(default_factory=list)
    
    # Health and scaling
    health_check: Optional[AppHealthCheck] = None
    scaling_policy: Optional[AppScalingPolicy] = None
    
    # UI Configuration
    config_schema: Optional[Dict[str, Any]] = None  # JSON schema for user config
    default_config: Optional[Dict[str, Any]] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    featured: bool = False
    verified: bool = False
    downloads: int = 0
    rating: float = 0.0
    rating_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ModelApp:
    """Model application instance"""
    app_id: str
    template_id: str
    name: str
    description: Optional[str]
    user_id: str
    
    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)
    environment_overrides: Dict[str, str] = field(default_factory=dict)
    
    # Deployment config
    replicas: int = 1
    resources: List[AppResource] = field(default_factory=list)
    
    # Status
    status: DeploymentStatus = DeploymentStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class AppDeployment:
    """Application deployment instance"""
    deployment_id: str
    app_id: str
    name: str
    namespace: str = "default"
    
    # Deployment spec
    replicas: int = 1
    image: Optional[str] = None
    resources: List[AppResource] = field(default_factory=list)
    environments: List[AppEnvironment] = field(default_factory=list)
    volumes: List[AppVolume] = field(default_factory=list)
    ports: List[AppPort] = field(default_factory=list)
    health_check: Optional[AppHealthCheck] = None
    
    # Status
    status: DeploymentStatus = DeploymentStatus.PENDING
    endpoint: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    
    # Error info
    error_message: Optional[str] = None
    deployment_log: List[str] = field(default_factory=list)


class AppMarketplace:
    """
    Model application marketplace service

    Manages app templates and deployment lifecycle.
    """

    def __init__(self, db: Session):
        self.db = db
        self._templates: Dict[str, AppTemplate] = {}
        self._apps: Dict[str, ModelApp] = {}
        self._deployments: Dict[str, AppDeployment] = {}
        self._initialize_templates()

    def _initialize_templates(self):
        """Initialize built-in app templates"""
        builtin_templates = [
            # Chatbot
            AppTemplate(
                id="chatbot-gpt",
                name="chatbot-gpt",
                display_name="GPT Chatbot",
                description="Chatbot powered by GPT models",
                category=AppCategory.CHATBOT,
                icon_url="/icons/chatbot.png",
                author="Platform Team",
                version="1.0.0",
                model_id="gpt-3.5-turbo",
                resources=[
                    AppResource("cpu", "500m", "2"),
                    AppResource("memory", "1Gi", "4Gi"),
                ],
                environments=[
                    AppEnvironment("MODEL_NAME", "gpt-3.5-turbo"),
                    AppEnvironment("API_KEY", secret=True, required=True),
                    AppEnvironment("MAX_TOKENS", "2048"),
                    AppEnvironment("TEMPERATURE", "0.7"),
                ],
                ports=[AppPort(8000)],
                health_check=AppHealthCheck(path="/health"),
                scaling_policy=AppScalingPolicy(min_replicas=1, max_replicas=5),
                config_schema={
                    "type": "object",
                    "properties": {
                        "model_name": {"type": "string"},
                        "max_tokens": {"type": "integer", "minimum": 1, "maximum": 4096},
                        "temperature": {"type": "number", "minimum": 0, "maximum": 2},
                        "system_prompt": {"type": "string"},
                    },
                },
                default_config={
                    "model_name": "gpt-3.5-turbo",
                    "max_tokens": 2048,
                    "temperature": 0.7,
                },
                tags=["chatbot", "nlp", "conversation"],
                verified=True,
            ),
            # Image Generation
            AppTemplate(
                id="stable-diffusion-app",
                name="stable-diffusion-app",
                display_name="Stable Diffusion",
                description="Text-to-image generation with Stable Diffusion",
                category=AppCategory.IMAGE_GENERATION,
                icon_url="/icons/image-gen.png",
                author="Platform Team",
                version="1.0.0",
                model_id="stable-diffusion",
                resources=[
                    AppResource("cpu", "1", "4"),
                    AppResource("memory", "8Gi", "16Gi"),
                    AppResource("gpu", "1", "1"),
                ],
                environments=[
                    AppEnvironment("MODEL_ID", "stable-diffusion-v2-1"),
                    AppEnvironment("IMAGE_SIZE", "512x512"),
                    AppEnvironment("STEPS", "50"),
                    AppEnvironment("GUIDANCE_SCALE", "7.5"),
                ],
                ports=[AppPort(8000)],
                health_check=AppHealthCheck(path="/health"),
                scaling_policy=AppScalingPolicy(min_replicas=1, max_replicas=3),
                tags=["image", "generation", "diffusion"],
                verified=True,
            ),
            # Text Summarization
            AppTemplate(
                id="summarizer-app",
                name="summarizer-app",
                display_name="Text Summarizer",
                description="Summarize long text documents",
                category=AppCategory.SUMMARIZATION,
                icon_url="/icons/summarizer.png",
                author="Platform Team",
                version="1.0.0",
                resources=[
                    AppResource("cpu", "500m", "2"),
                    AppResource("memory", "2Gi", "8Gi"),
                ],
                environments=[
                    AppEnvironment("MODEL_NAME", "facebook/bart-large-cnn"),
                    AppEnvironment("MAX_LENGTH", "1024"),
                ],
                ports=[AppPort(8000)],
                health_check=AppHealthCheck(path="/health"),
                tags=["nlp", "summarization", "document"],
                verified=True,
            ),
            # Code Assistant
            AppTemplate(
                id="code-assistant-app",
                name="code-assistant-app",
                display_name="Code Assistant",
                description="AI-powered code completion and generation",
                category=AppCategory.CODE_ASSISTANT,
                icon_url="/icons/code.png",
                author="Platform Team",
                version="1.0.0",
                resources=[
                    AppResource("cpu", "1", "4"),
                    AppResource("memory", "4Gi", "16Gi"),
                ],
                environments=[
                    AppEnvironment("MODEL_NAME", "codellama-13b"),
                    AppEnvironment("MAX_TOKENS", "512"),
                    AppEnvironment("TEMPERATURE", "0.2"),
                ],
                ports=[AppPort(8000)],
                health_check=AppHealthCheck(path="/health"),
                tags=["code", "development", "llm"],
                verified=True,
            ),
            # Voice Assistant
            AppTemplate(
                id="voice-assistant-app",
                name="voice-assistant-app",
                display_name="Voice Assistant",
                description="Voice-enabled AI assistant",
                category=AppCategory.VOICE_ASSISTANT,
                icon_url="/icons/voice.png",
                author="Platform Team",
                version="1.0.0",
                resources=[
                    AppResource("cpu", "1", "4"),
                    AppResource("memory", "4Gi", "8Gi"),
                ],
                environments=[
                    AppEnvironment("STT_MODEL", "whisper-large"),
                    AppEnvironment("LLM_MODEL", "gpt-3.5-turbo"),
                    AppEnvironment("TTS_MODEL", "tts-1"),
                ],
                ports=[AppPort(8000)],
                health_check=AppHealthCheck(path="/health"),
                tags=["voice", "audio", "assistant"],
            ),
            # Recommendation Service
            AppTemplate(
                id="recommendation-app",
                name="recommendation-app",
                display_name="Recommendation Service",
                description="Personalized recommendation engine",
                category=AppCategory.RECOMMENDATION,
                icon_url="/icons/recommendation.png",
                author="Platform Team",
                version="1.0.0",
                resources=[
                    AppResource("cpu", "500m", "2"),
                    AppResource("memory", "2Gi", "8Gi"),
                ],
                environments=[
                    AppEnvironment("MODEL_TYPE", "ncf"),
                    AppEnvironment("EMBEDDING_DIM", "64"),
                ],
                ports=[AppPort(8000)],
                health_check=AppHealthCheck(path="/health"),
                scaling_policy=AppScalingPolicy(min_replicas=2, max_replicas=10),
                tags=["recommendation", "personalization"],
                verified=True,
            ),
            # Translation
            AppTemplate(
                id="translation-app",
                name="translation-app",
                display_name="Translation Service",
                description="Multi-language translation service",
                category=AppCategory.TRANSLATION,
                icon_url="/icons/translate.png",
                author="Platform Team",
                version="1.0.0",
                resources=[
                    AppResource("cpu", "500m", "2"),
                    AppResource("memory", "2Gi", "4Gi"),
                ],
                environments=[
                    AppEnvironment("MODEL_NAME", "facebook/nllb-200-3.3B"),
                ],
                ports=[AppPort(8000)],
                health_check=AppHealthCheck(path="/health"),
                scaling_policy=AppScalingPolicy(min_replicas=1, max_replicas=5),
                tags=["translation", "nlp", "multilingual"],
            ),
            # Analytics Dashboard
            AppTemplate(
                id="analytics-app",
                name="analytics-app",
                display_name="Analytics Dashboard",
                description="Data analytics and visualization dashboard",
                category=AppCategory.ANALYTICS,
                icon_url="/icons/analytics.png",
                author="Platform Team",
                version="1.0.0",
                resources=[
                    AppResource("cpu", "500m", "2"),
                    AppResource("memory", "1Gi", "4Gi"),
                ],
                ports=[AppPort(8050)],
                health_check=AppHealthCheck(path="/api/health"),
                tags=["analytics", "dashboard", "visualization"],
                verified=True,
            ),
        ]

        for template in builtin_templates:
            self._templates[template.id] = template

    async def list_templates(
        self,
        category: Optional[AppCategory] = None,
        search: Optional[str] = None,
        featured_only: bool = False,
        verified_only: bool = False,
        limit: int = 100,
    ) -> List[AppTemplate]:
        """List app templates"""
        templates = list(self._templates.values())

        if category:
            templates = [t for t in templates if t.category == category]
        if featured_only:
            templates = [t for t in templates if t.featured]
        if verified_only:
            templates = [t for t in templates if t.verified]

        if search:
            search_lower = search.lower()
            templates = [
                t for t in templates
                if search_lower in t.name.lower() or
                search_lower in t.display_name.lower() or
                search_lower in t.description.lower() or
                any(search_lower in tag for tag in t.tags)
            ]

        return templates[:limit]

    async def get_template(self, template_id: str) -> Optional[AppTemplate]:
        """Get template by ID"""
        return self._templates.get(template_id)

    async def create_app(
        self,
        template_id: str,
        name: str,
        user_id: str,
        config: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
    ) -> Optional[ModelApp]:
        """Create app from template"""
        template = await self.get_template(template_id)
        if not template:
            return None

        app_id = f"app-{user_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Merge default config with user config
        final_config = template.default_config.copy() if template.default_config else {}
        if config:
            final_config.update(config)

        app = ModelApp(
            app_id=app_id,
            template_id=template_id,
            name=name,
            description=description,
            user_id=user_id,
            config=final_config,
            resources=template.resources.copy(),
            status=DeploymentStatus.DRAFT,
        )

        self._apps[app_id] = app

        return app

    async def get_app(self, app_id: str) -> Optional[ModelApp]:
        """Get app by ID"""
        return self._apps.get(app_id)

    async def list_apps(
        self,
        user_id: Optional[str] = None,
        status: Optional[DeploymentStatus] = None,
    ) -> List[ModelApp]:
        """List apps"""
        apps = list(self._apps.values())

        if user_id:
            apps = [a for a in apps if a.user_id == user_id]
        if status:
            apps = [a for a in apps if a.status == status]

        return apps

    async def update_app(
        self,
        app_id: str,
        config: Optional[Dict[str, Any]] = None,
        replicas: Optional[int] = None,
    ) -> Optional[ModelApp]:
        """Update app configuration"""
        app = await self.get_app(app_id)
        if not app:
            return None

        if config:
            app.config.update(config)
        if replicas is not None:
            app.replicas = replicas

        app.updated_at = datetime.now()
        return app

    async def delete_app(self, app_id: str) -> bool:
        """Delete an app"""
        if app_id in self._apps:
            # Stop any running deployments
            for deployment in self._deployments.values():
                if deployment.app_id == app_id and deployment.status == DeploymentStatus.RUNNING:
                    await self.stop_deployment(deployment.deployment_id)
            del self._apps[app_id]
            return True
        return False

    async def deploy_app(
        self,
        app_id: str,
        name: Optional[str] = None,
        namespace: str = "default",
        replicas: Optional[int] = None,
        environments: Optional[List[AppEnvironment]] = None,
    ) -> Optional[AppDeployment]:
        """Deploy an app"""
        app = await self.get_app(app_id)
        if not app:
            return None

        template = await self.get_template(app.template_id)
        if not template:
            return None

        deployment_id = f"deploy-{app_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Build environment list
        env_list = template.environments.copy()
        if app.environment_overrides:
            for env in env_list:
                if env.name in app.environment_overrides:
                    env.value = app.environment_overrides[env.name]
        if environments:
            env_list.extend(environments)

        deployment = AppDeployment(
            deployment_id=deployment_id,
            app_id=app_id,
            name=name or f"{app.name}-deployment",
            namespace=namespace,
            replicas=replicas or app.replicas,
            resources=app.resources,
            environments=env_list,
            ports=template.ports,
            health_check=template.health_check,
            status=DeploymentStatus.PENDING,
        )

        self._deployments[deployment_id] = deployment

        # Start deployment asynchronously
        # In production, this would interact with K8s/Docker
        deployment.status = DeploymentStatus.RUNNING
        deployment.started_at = datetime.now()
        deployment.endpoint = f"{deployment.name}.{namespace}.svc.cluster.local"

        # Update app status
        app.status = DeploymentStatus.RUNNING

        return deployment

    async def get_deployment(self, deployment_id: str) -> Optional[AppDeployment]:
        """Get deployment by ID"""
        return self._deployments.get(deployment_id)

    async def list_deployments(
        self,
        app_id: Optional[str] = None,
        status: Optional[DeploymentStatus] = None,
    ) -> List[AppDeployment]:
        """List deployments"""
        deployments = list(self._deployments.values())

        if app_id:
            deployments = [d for d in deployments if d.app_id == app_id]
        if status:
            deployments = [d for d in deployments if d.status == status]

        return deployments

    async def stop_deployment(self, deployment_id: str) -> bool:
        """Stop a deployment"""
        deployment = await self.get_deployment(deployment_id)
        if not deployment:
            return False

        deployment.status = DeploymentStatus.STOPPED
        deployment.stopped_at = datetime.now()
        deployment.endpoint = None

        # Update app status
        app = await self.get_app(deployment.app_id)
        if app:
            app.status = DeploymentStatus.STOPPED

        return True

    async def scale_deployment(
        self,
        deployment_id: str,
        replicas: int,
    ) -> bool:
        """Scale a deployment"""
        deployment = await self.get_deployment(deployment_id)
        if not deployment:
            return False

        deployment.replicas = replicas
        deployment.status = DeploymentStatus.SCALING

        # In production, would interact with K8s/Docker to scale

        deployment.status = DeploymentStatus.RUNNING
        return True

    async def get_deployment_logs(
        self,
        deployment_id: str,
        tail_lines: int = 100,
    ) -> List[str]:
        """Get deployment logs"""
        deployment = await self.get_deployment(deployment_id)
        if not deployment:
            return []

        # Return log tail
        return deployment.deployment_log[-tail_lines:]

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get all categories with counts"""
        category_counts = {}
        for template in self._templates.values():
            cat = template.category.value
            if cat not in category_counts:
                category_counts[cat] = 0
            category_counts[cat] += 1

        return [
            {"name": cat, "count": count, "display_name": cat.replace("_", " ").title()}
            for cat, count in sorted(category_counts.items())
        ]

    async def get_featured_templates(self, limit: int = 6) -> List[AppTemplate]:
        """Get featured templates"""
        return [t for t in self._templates.values() if t.featured][:limit]


# Singleton
_marketplace: Optional[AppMarketplace] = None


def get_app_marketplace(db: Session) -> AppMarketplace:
    """Get or create the app marketplace instance"""
    return AppMarketplace(db)
