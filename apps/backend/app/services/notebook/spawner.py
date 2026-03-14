"""
Spawner Configuration for Jupyter Hub

Defines the resource profiles and image templates available for notebook servers.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ResourceProfile(BaseModel):
    """Resource profile for notebook servers"""

    id: str
    name: str
    description: str
    cpu_limit: float
    cpu_guarantee: float
    mem_limit: str
    mem_guarantee: str
    gpu_limit: int = 0
    default: bool = False


class NotebookImage(BaseModel):
    """Notebook image template"""

    id: str
    name: str
    description: str
    image: str
    icon: str = "python"
    packages: List[str] = []
    default: bool = False
    gpu_required: bool = False
    gpu_recommended: bool = False


class SpawnerConfig:
    """
    Spawner configuration manager

    Manages available resource profiles and notebook images.
    """

    # Default resource profiles
    RESOURCE_PROFILES: List[ResourceProfile] = [
        ResourceProfile(
            id="small",
            name="Small",
            description="0.5 CPU, 1GB RAM",
            cpu_limit=0.5,
            cpu_guarantee=0.25,
            mem_limit="1G",
            mem_guarantee="512M",
            gpu_limit=0,
        ),
        ResourceProfile(
            id="medium",
            name="Medium",
            description="2 CPU, 4GB RAM",
            cpu_limit=2,
            cpu_guarantee=0.5,
            mem_limit="4G",
            mem_guarantee="1G",
            gpu_limit=0,
            default=True,
        ),
        ResourceProfile(
            id="large",
            name="Large",
            description="4 CPU, 8GB RAM",
            cpu_limit=4,
            cpu_guarantee=1,
            mem_limit="8G",
            mem_guarantee="2G",
            gpu_limit=0,
        ),
        ResourceProfile(
            id="gpu-small",
            name="GPU Small",
            description="2 CPU, 8GB RAM, 1 GPU",
            cpu_limit=2,
            cpu_guarantee=0.5,
            mem_limit="8G",
            mem_guarantee="2G",
            gpu_limit=1,
        ),
        ResourceProfile(
            id="gpu-large",
            name="GPU Large",
            description="8 CPU, 16GB RAM, 2 GPU",
            cpu_limit=8,
            cpu_guarantee=2,
            mem_limit="16G",
            mem_guarantee="4G",
            gpu_limit=2,
        ),
    ]

    # Notebook images
    NOTEBOOK_IMAGES: List[NotebookImage] = [
        NotebookImage(
            id="pytorch",
            name="PyTorch",
            description="PyTorch 2.0 with CUDA support",
            image="one-data-studio/notebook-pytorch:latest",
            icon="pytorch",
            packages=["torch", "torchvision", "torchaudio"],
            default=True,
            gpu_recommended=True,
        ),
        NotebookImage(
            id="tensorflow",
            name="TensorFlow",
            description="TensorFlow 2.14 with Keras",
            image="one-data-studio/notebook-tensorflow:latest",
            icon="tensorflow",
            packages=["tensorflow", "keras"],
            gpu_recommended=True,
        ),
        NotebookImage(
            id="sklearn",
            name="Scikit-learn",
            description="Python data science stack",
            image="one-data-studio/notebook-sklearn:latest",
            icon="sklearn",
            packages=["scikit-learn", "pandas", "numpy", "matplotlib"],
        ),
        NotebookImage(
            id="nlp",
            name="NLP",
            description="NLP with Transformers and spaCy",
            image="one-data-studio/notebook-nlp:latest",
            icon="nlp",
            packages=["transformers", "spacy", "datasets"],
            gpu_recommended=True,
        ),
        NotebookImage(
            id="minimal",
            name="Minimal",
            description="Minimal Python environment",
            image="one-data-studio/notebook-minimal:latest",
            icon="python",
            packages=["python", "ipykernel"],
        ),
    ]

    @classmethod
    def get_resource_profile(cls, profile_id: str) -> Optional[ResourceProfile]:
        """Get a resource profile by ID"""
        for profile in cls.RESOURCE_PROFILES:
            if profile.id == profile_id:
                return profile
        return None

    @classmethod
    def get_default_resource_profile(cls) -> ResourceProfile:
        """Get the default resource profile"""
        for profile in cls.RESOURCE_PROFILES:
            if profile.default:
                return profile
        return cls.RESOURCE_PROFILES[0]

    @classmethod
    def get_notebook_image(cls, image_id: str) -> Optional[NotebookImage]:
        """Get a notebook image by ID"""
        for image in cls.NOTEBOOK_IMAGES:
            if image.id == image_id:
                return image
        return None

    @classmethod
    def get_default_notebook_image(cls) -> NotebookImage:
        """Get the default notebook image"""
        for image in cls.NOTEBOOK_IMAGES:
            if image.default:
                return image
        return cls.NOTEBOOK_IMAGES[0]

    @classmethod
    def get_available_profiles(cls, gpu_available: bool = False) -> List[ResourceProfile]:
        """Get available resource profiles, optionally filtered by GPU availability"""
        if gpu_available:
            return cls.RESOURCE_PROFILES
        return [p for p in cls.RESOURCE_PROFILES if p.gpu_limit == 0]

    @classmethod
    def get_available_images(cls, gpu_available: bool = False) -> List[NotebookImage]:
        """Get available notebook images, optionally filtered by GPU requirements"""
        if gpu_available:
            return cls.NOTEBOOK_IMAGES
        return [i for i in cls.NOTEBOOK_IMAGES if not i.gpu_required]

    @classmethod
    def calculate_spawner_config(
        cls,
        image_id: Optional[str] = None,
        profile_id: Optional[str] = None,
        user_quota: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate spawner configuration based on image, profile, and user quota

        Args:
            image_id: Notebook image ID
            profile_id: Resource profile ID
            user_quota: User quota limits (optional)

        Returns:
            Spawner configuration dictionary
        """
        # Get notebook image
        image = cls.get_notebook_image(image_id) if image_id else cls.get_default_notebook_image()
        if not image:
            image = cls.get_default_notebook_image()

        # Get resource profile
        profile = cls.get_resource_profile(profile_id) if profile_id else cls.get_default_resource_profile()
        if not profile:
            profile = cls.get_default_resource_profile()

        # Apply user quota if provided
        cpu_limit = profile.cpu_limit
        cpu_guarantee = profile.cpu_guarantee
        mem_limit = profile.mem_limit
        mem_guarantee = profile.mem_guarantee
        gpu_limit = profile.gpu_limit

        if user_quota:
            if "cpu" in user_quota:
                cpu_limit = min(cpu_limit, user_quota["cpu"])
            if "memory" in user_quota:
                # Convert memory quota (in GB) to format
                mem_gb = int(user_quota["memory"].rstrip("G"))
                current_gb = int(mem_limit.rstrip("G"))
                mem_limit = f"{min(mem_gb, current_gb)}G"
            if "gpu" in user_quota:
                gpu_limit = min(gpu_limit, user_quota["gpu"])

        # Build configuration
        config = {
            "image_spec": image.image,
            "cpu_limit": cpu_limit,
            "cpu_guarantee": cpu_guarantee,
            "mem_limit": mem_limit,
            "mem_guarantee": mem_guarantee,
            "extra_resource_limits": {},
        }

        # Add GPU if requested
        if gpu_limit > 0:
            config["extra_resource_limits"]["nvidia.com/gpu"] = str(gpu_limit)

        return config
