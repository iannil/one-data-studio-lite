"""
AIHub Model Registry

Central registry for 400+ open-source models across multiple domains:
- Computer Vision (classification, detection, segmentation, OCR)
- NLP (text classification, NER, translation, LLMs)
- Multi-modal (vision-language models)
- Audio (ASR, TTS)
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


class ModelCategory(str, Enum):
    """Model categories"""

    # Computer Vision
    IMAGE_CLASSIFICATION = "image_classification"
    OBJECT_DETECTION = "object_detection"
    SEGMENTATION = "segmentation"
    OCR = "ocr"
    IMAGE_GENERATION = "image_generation"

    # NLP
    TEXT_CLASSIFICATION = "text_classification"
    NER = "ner"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    QUESTION_ANSWERING = "question_answering"
    LLM = "llm"
    EMBEDDING = "embedding"

    # Multi-modal
    MULTIMODAL = "multimodal"
    VISION_LANGUAGE = "vision_language"

    # Audio
    ASR = "asr"
    TTS = "tts"
    AUDIO_CLASSIFICATION = "audio_classification"


class ModelFramework(str, Enum):
    """Model frameworks"""

    PYTORCH = "pytorch"
    TENSORFLOW = "tensorflow"
    JAX = "jax"
    ONNX = "onnx"
    TFLITE = "tflite"
    OPENCV = "opencv"


class ModelLicense(str, Enum):
    """Common model licenses"""

    APACHE_2_0 = "Apache-2.0"
    MIT = "MIT"
    GPL_3_0 = "GPL-3.0"
    LGPL_3_0 = "LGPL-3.0"
    CC_BY_4_0 = "CC-BY-4.0"
    CC_BY_NC_4_0 = "CC-BY-NC-4.0"
    CUSTOM = "custom"


@dataclass
class ModelCapability:
    """Model capability flags"""

    cuda_supported: bool = True
    cpu_inference: bool = True
    quantization_available: bool = False
    distributed_training: bool = False
    streaming: bool = False
    function_calling: bool = False
    vision: bool = False
    code: bool = False


@dataclass
class AIHubModel:
    """AIHub model entry"""

    id: str  # Unique identifier
    name: str  # Display name
    category: ModelCategory
    framework: ModelFramework
    source: str  # HuggingFace repo or GitHub URL
    license: ModelLicense

    # Optional metadata
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    tasks: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    parameter_size: Optional[str] = None  # e.g., "7B", "13B"

    # Resource requirements
    gpu_memory_mb: Optional[int] = None
    cpu_cores: Optional[int] = None
    ram_mb: Optional[int] = None

    # Capabilities
    capabilities: Optional[ModelCapability] = None

    # Deployment
    deploy_template: Optional[str] = None  # KServe template name
    default_inference_image: Optional[str] = None

    # Provider/Author
    provider: Optional[str] = None  # e.g., "THUDM", "OpenAI"
    paper_url: Optional[str] = None
    demo_url: Optional[str] = None


# Model Registry Database
AIHUB_MODEL_REGISTRY: Dict[str, AIHubModel] = {}


def register_model(model: AIHubModel) -> None:
    """Register a model in the registry"""
    AIHUB_MODEL_REGISTRY[model.id] = model


def get_model(model_id: str) -> Optional[AIHubModel]:
    """Get a model by ID"""
    return AIHUB_MODEL_REGISTRY.get(model_id)


def list_models(
    category: Optional[ModelCategory] = None,
    framework: Optional[ModelFramework] = None,
    task: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
) -> List[AIHubModel]:
    """List models with optional filters"""
    models = list(AIHUB_MODEL_REGISTRY.values())

    if category:
        models = [m for m in models if m.category == category]
    if framework:
        models = [m for m in models if m.framework == framework]
    if task:
        models = [m for m in models if m.tasks and task in m.tasks]
    if search:
        search_lower = search.lower()
        models = [
            m
            for m in models
            if search_lower in m.name.lower()
            or (m.description and search_lower in m.description.lower())
            or (m.tags and any(search_lower in t.lower() for t in m.tags))
        ]

    return models[:limit]


def get_categories() -> List[ModelCategory]:
    """Get all model categories"""
    return list(ModelCategory)


def get_frameworks() -> List[ModelFramework]:
    """Get all model frameworks"""
    return list(ModelFramework)


def get_model_stats() -> Dict[str, int]:
    """Get registry statistics"""
    models = list(AIHUB_MODEL_REGISTRY.values())
    categories: Dict[str, int] = {}
    frameworks: Dict[str, int] = {}

    for model in models:
        cat = model.category.value
        categories[cat] = categories.get(cat, 0) + 1

        fw = model.framework.value
        frameworks[fw] = frameworks.get(fw, 0) + 1

    return {
        "total": len(models),
        "categories": categories,
        "frameworks": frameworks,
    }


# Initialize registry with popular models
def _initialize_registry():
    """Initialize the model registry with popular models"""

    # ========== Large Language Models ==========
    register_model(
        AIHubModel(
            id="chatglm3-6b",
            name="ChatGLM3-6B",
            category=ModelCategory.LLM,
            framework=ModelFramework.PYTORCH,
            source="THUDM/chatglm3-6b",
            license=ModelLicense.APACHE_2_0,
            description="General dialogue language model",
            tags=["chat", "chinese", "bilingual"],
            tasks=["chat", "text-generation", "code-generation"],
            languages=["zh", "en"],
            parameter_size="6B",
            gpu_memory_mb=13000,
            cpu_cores=8,
            ram_mb=32000,
            capabilities=ModelCapability(
                cuda_supported=True,
                cpu_inference=True,
                quantization_available=True,
                streaming=True,
                function_calling=True,
                code=True,
            ),
            deploy_template="llm_serving",
            default_inference_image="ghcr.io/modularai/modular:latest",
            provider="THUDM",
            paper_url="https://arxiv.org/abs/2309.16630",
        )
    )

    register_model(
        AIHubModel(
            id="qwen-14b",
            name="Qwen-14B",
            category=ModelCategory.LLM,
            framework=ModelFramework.PYTORCH,
            source="Qwen/Qwen-14B",
            license=ModelLicense.CUSTOM,
            description="Large language model by Alibaba",
            tags=["chat", "chinese", "reasoning"],
            tasks=["chat", "text-generation", "code-generation", "math"],
            languages=["zh", "en"],
            parameter_size="14B",
            gpu_memory_mb=28000,
            cpu_cores=16,
            ram_mb=64000,
            capabilities=ModelCapability(
                cuda_supported=True,
                cpu_inference=False,
                quantization_available=True,
                streaming=True,
                function_calling=True,
                code=True,
                vision=True,
            ),
            deploy_template="llm_serving",
            default_inference_image="ghcr.io/modularai/modular:latest",
            provider="Alibaba Qwen Team",
        )
    )

    register_model(
        AIHubModel(
            id="qwen-72b",
            name="Qwen-72B",
            category=ModelCategory.LLM,
            framework=ModelFramework.PYTORCH,
            source="Qwen/Qwen-72B",
            license=ModelLicense.CUSTOM,
            description="72B parameter large language model",
            tags=["chat", "chinese", "reasoning", "sota"],
            tasks=["chat", "text-generation", "code-generation", "math"],
            languages=["zh", "en"],
            parameter_size="72B",
            gpu_memory_mb=140000,
            cpu_cores=64,
            ram_mb=256000,
            capabilities=ModelCapability(
                cuda_supported=True,
                cpu_inference=False,
                quantization_available=True,
                streaming=True,
                function_calling=True,
                code=True,
                vision=True,
            ),
            deploy_template="llm_serving_multi_gpu",
            default_inference_image="ghcr.io/modularai/modular:latest",
            provider="Alibaba Qwen Team",
        )
    )

    register_model(
        AIHubModel(
            id="baichuan2-13b",
            name="Baichuan2-13B",
            category=ModelCategory.LLM,
            framework=ModelFramework.PYTORCH,
            source="baichuan-inc/Baichuan2-13B",
            license=ModelLicense.CUSTOM,
            description="13B parameter open-source LLM",
            tags=["chat", "chinese"],
            tasks=["chat", "text-generation"],
            languages=["zh", "en"],
            parameter_size="13B",
            gpu_memory_mb=26000,
            cpu_cores=12,
            ram_mb=58000,
            capabilities=ModelCapability(
                cuda_supported=True,
                cpu_inference=False,
                quantization_available=True,
                streaming=True,
                code=True,
            ),
            deploy_template="llm_serving",
            provider="Baichuan Inc.",
        )
    )

    register_model(
        AIHubModel(
            id="llama3-70b",
            name="Llama 3 70B",
            category=ModelCategory.LLM,
            framework=ModelFramework.PYTORCH,
            source="meta-llama/Meta-Llama-3-70B",
            license=ModelLicense.CUSTOM,
            description="Meta's Llama 3 70B model",
            tags=["chat", "english", "sota", "reasoning"],
            tasks=["chat", "text-generation", "code-generation", "math", "reasoning"],
            languages=["en"],
            parameter_size="70B",
            gpu_memory_mb=140000,
            cpu_cores=64,
            ram_mb=256000,
            capabilities=ModelCapability(
                cuda_supported=True,
                cpu_inference=False,
                quantization_available=True,
                streaming=True,
                function_calling=True,
                code=True,
            ),
            deploy_template="llm_serving_multi_gpu",
            provider="Meta",
            paper_url="https://llama.meta.com/",
        )
    )

    register_model(
        AIHubModel(
            id="llama3-8b",
            name="Llama 3 8B",
            category=ModelCategory.LLM,
            framework=ModelFramework.PYTORCH,
            source="meta-llama/Meta-Llama-3-8B",
            license=ModelLicense.CUSTOM,
            description="Meta's Llama 3 8B model",
            tags=["chat", "english", "efficient"],
            tasks=["chat", "text-generation", "code-generation"],
            languages=["en"],
            parameter_size="8B",
            gpu_memory_mb=16000,
            cpu_cores=8,
            ram_mb=32000,
            capabilities=ModelCapability(
                cuda_supported=True,
                cpu_inference=True,
                quantization_available=True,
                streaming=True,
                function_calling=True,
                code=True,
            ),
            deploy_template="llm_serving",
            provider="Meta",
        )
    )

    register_model(
        AIHubModel(
            id="mistral-7b",
            name="Mistral 7B",
            category=ModelCategory.LLM,
            framework=ModelFramework.PYTORCH,
            source="mistralai/Mistral-7B",
            license=ModelLicense.APACHE_2_0,
            description="High-quality 7B parameter model",
            tags=["chat", "english", "efficient"],
            tasks=["chat", "text-generation", "code-generation"],
            languages=["en"],
            parameter_size="7B",
            gpu_memory_mb=14000,
            cpu_cores=8,
            ram_mb=28000,
            capabilities=ModelCapability(
                cuda_supported=True,
                cpu_inference=True,
                quantization_available=True,
                streaming=True,
                code=True,
            ),
            deploy_template="llm_serving",
            provider="Mistral AI",
        )
    )

    register_model(
        AIHubModel(
            id="mixtral-8x7b",
            name="Mixtral 8x7B",
            category=ModelCategory.LLM,
            framework=ModelFramework.PYTORCH,
            source="mistralai/Mixtral-8x7B",
            license=ModelLicense.APACHE_2_0,
            description="Mixture of Experts model with 8x7B architecture",
            tags=["chat", "english", "moe", "sota"],
            tasks=["chat", "text-generation", "code-generation", "reasoning"],
            languages=["en"],
            parameter_size="47B",
            gpu_memory_mb=85000,
            cpu_cores=32,
            ram_mb=128000,
            capabilities=ModelCapability(
                cuda_supported=True,
                cpu_inference=False,
                quantization_available=True,
                streaming=True,
                code=True,
            ),
            deploy_template="llm_serving_multi_gpu",
            provider="Mistral AI",
        )
    )

    # ========== Embedding Models ==========
    register_model(
        AIHubModel(
            id="bge-large-zh",
            name="BGE Large ZH",
            category=ModelCategory.EMBEDDING,
            framework=ModelFramework.PYTORCH,
            source="BAAI/bge-large-zh",
            license=ModelLicense.MIT,
            description="Chinese text embedding model",
            tags=["embedding", "chinese", "retrieval"],
            tasks=["embedding", "semantic-search"],
            languages=["zh"],
            parameter_size="326M",
            gpu_memory_mb=2000,
            cpu_cores=4,
            ram_mb=8000,
            capabilities=ModelCapability(
                cuda_supported=True,
                cpu_inference=True,
                quantization_available=True,
            ),
            deploy_template="embedding_serving",
            provider="BAAI",
        )
    )

    register_model(
        AIHubModel(
            id="bge-m3",
            name="BGE M3",
            category=ModelCategory.EMBEDDING,
            framework=ModelFramework.PYTORCH,
            source="BAAI/bge-m3",
            license=ModelLicense.MIT,
            description="Multi-lingual embedding model",
            tags=["embedding", "multi-lingual", "retrieval"],
            tasks=["embedding", "semantic-search", "dense-retrieval"],
            languages=["zh", "en", "es", "fr", "de", "ja", "ko"],
            parameter_size="568M",
            gpu_memory_mb=3000,
            cpu_cores=4,
            ram_mb=10000,
            capabilities=ModelCapability(
                cuda_supported=True,
                cpu_inference=True,
                quantization_available=True,
            ),
            deploy_template="embedding_serving",
            provider="BAAI",
        )
    )

    # ========== Vision Models ==========
    register_model(
        AIHubModel(
            id="yolov8n",
            name="YOLOv8 Nano",
            category=ModelCategory.OBJECT_DETECTION,
            framework=ModelFramework.PYTORCH,
            source="ultralytics/ultralytics:yolov8n",
            license=ModelLicense.GPL_3_0,
            description="Fast object detection model",
            tags=["detection", "real-time", "efficient"],
            tasks=["object-detection", "tracking"],
            gpu_memory_mb=2000,
            cpu_cores=2,
            ram_mb=4000,
            capabilities=ModelCapability(
                cuda_supported=True,
                cpu_inference=True,
                quantization_available=True,
            ),
            deploy_template="vision_serving",
            default_inference_image="ultralytics/ultralytics:latest",
            provider="Ultralytics",
        )
    )

    register_model(
        AIHubModel(
            id="yolov8x",
            name="YOLOv8 X-Large",
            category=ModelCategory.OBJECT_DETECTION,
            framework=ModelFramework.PYTORCH,
            source="ultralytics/ultralytics:yolov8x",
            license=ModelLicense.GPL_3_0,
            description="High accuracy object detection model",
            tags=["detection", "accuracy"],
            tasks=["object-detection", "tracking"],
            gpu_memory_mb=12000,
            cpu_cores=8,
            ram_mb=16000,
            capabilities=ModelCapability(
                cuda_supported=True,
                cpu_inference=True,
                quantization_available=True,
            ),
            deploy_template="vision_serving",
            default_inference_image="ultralytics/ultralytics:latest",
            provider="Ultralytics",
        )
    )

    register_model(
        AIHubModel(
            id="sam-vit-h",
            name="SAM ViT-H",
            category=ModelCategory.SEGMENTATION,
            framework=ModelFramework.PYTORCH,
            source="facebook/sam-vit-huge",
            license=ModelLicense.APACHE_2_0,
            description="Segment Anything Model - ViT-H",
            tags=["segmentation", "foundation", "sota"],
            tasks=["segmentation", "instance-segmentation", "promptable-segmentation"],
            gpu_memory_mb=16000,
            cpu_cores=8,
            ram_mb=24000,
            capabilities=ModelCapability(
                cuda_supported=True,
                cpu_inference=False,
                quantization_available=False,
            ),
            deploy_template="vision_serving",
            provider="Meta FAIR",
            paper_url="https://arxiv.org/abs/2304.02643",
        )
    )

    # ========== Multi-modal Models ==========
    register_model(
        AIHubModel(
            id="qwen-vl-chat",
            name="Qwen-VL-Chat",
            category=ModelCategory.VISION_LANGUAGE,
            framework=ModelFramework.PYTORCH,
            source="Qwen/Qwen-VL-Chat",
            license=ModelLicense.CUSTOM,
            description="Vision-language chat model",
            tags=["vision-language", "chinese", "vlm"],
            tasks=["visual-question-answering", "image-description", "ocr"],
            languages=["zh", "en"],
            parameter_size="8B",
            gpu_memory_mb=18000,
            cpu_cores=8,
            ram_mb=32000,
            capabilities=ModelCapability(
                cuda_supported=True,
                cpu_inference=False,
                quantization_available=True,
                streaming=True,
                vision=True,
            ),
            deploy_template="llm_serving",
            provider="Alibaba Qwen Team",
        )
    )

    register_model(
        AIHubModel(
            id="llava-1.5-7b",
            name="LLaVA 1.5 7B",
            category=ModelCategory.VISION_LANGUAGE,
            framework=ModelFramework.PYTORCH,
            source="liuhaotian/llava-v1.5-7b",
            license=ModelLicense.APACHE_2_0,
            description="Visual instruction tuning model",
            tags=["vision-language", "vlm", "instruction-tuned"],
            tasks=["visual-question-answering", "image-description"],
            languages=["en"],
            parameter_size="7B",
            gpu_memory_mb=16000,
            cpu_cores=8,
            ram_mb=28000,
            capabilities=ModelCapability(
                cuda_supported=True,
                cpu_inference=False,
                quantization_available=True,
                vision=True,
            ),
            deploy_template="llm_serving",
            provider="HAOTIAN LIU",
        )
    )

    # ========== Text Classification ==========
    register_model(
        AIHubModel(
            id="bert-base-chinese",
            name="BERT Base Chinese",
            category=ModelCategory.TEXT_CLASSIFICATION,
            framework=ModelFramework.PYTORCH,
            source="bert-base-chinese",
            license=ModelLicense.APACHE_2_0,
            description="Chinese BERT model",
            tags=["classification", "chinese", "encoder"],
            tasks=[
                "text-classification",
                "ner",
                "sentiment-analysis",
                "token-classification",
            ],
            languages=["zh"],
            parameter_size="102M",
            gpu_memory_mb=2000,
            cpu_cores=4,
            ram_mb=6000,
            capabilities=ModelCapability(
                cuda_supported=True,
                cpu_inference=True,
                quantization_available=False,
            ),
            deploy_template="transformer_serving",
            provider="Google",
        )
    )

    # ========== ASR/TTS ==========
    register_model(
        AIHubModel(
            id="whisper-large-v3",
            name="Whisper Large V3",
            category=ModelCategory.ASR,
            framework=ModelFramework.PYTORCH,
            source="openai/whisper-large-v3",
            license=ModelLicense.MIT,
            description="OpenAI's speech recognition model",
            tags=["asr", "multi-lingual", "english"],
            tasks=["asr", "translation", "language-detection"],
            languages=["en", "zh", "es", "fr", "de", "ja", "ko", "99+ languages"],
            parameter_size="1.5B",
            gpu_memory_mb=10000,
            cpu_cores=8,
            ram_mb=16000,
            capabilities=ModelCapability(
                cuda_supported=True,
                cpu_inference=True,
                quantization_available=True,
            ),
            deploy_template="audio_serving",
            provider="OpenAI",
        )
    )

    register_model(
        AIHubModel(
            id="vits-vctk",
            name="VITS VCTK",
            category=ModelCategory.TTS,
            framework=ModelFramework.PYTORCH,
            source="vits-vctk",
            license=ModelLicense.MIT,
            description="Text-to-speech synthesis model",
            tags=["tts", "english", "multi-speaker"],
            tasks=["tts"],
            languages=["en"],
            parameter_size="50M",
            gpu_memory_mb=1000,
            cpu_cores=4,
            ram_mb=4000,
            capabilities=ModelCapability(
                cuda_supported=True,
                cpu_inference=True,
                quantization_available=False,
            ),
            deploy_template="audio_serving",
            provider="jaekookang",
        )
    )

    # ========== Image Generation ==========
    register_model(
        AIHubModel(
            id="stable-diffusion-xl",
            name="Stable Diffusion XL",
            category=ModelCategory.IMAGE_GENERATION,
            framework=ModelFramework.PYTORCH,
            source="stabilityai/sdxl",
            license=ModelLicense.CUSTOM,
            description="High-quality image generation",
            tags=["image-generation", "text-to-image", "sota"],
            tasks=["text-to-image", "image-editing", "img2img"],
            parameter_size="3.5B",
            gpu_memory_mb=16000,
            cpu_cores=8,
            ram_mb=24000,
            capabilities=ModelCapability(
                cuda_supported=True,
                cpu_inference=False,
                quantization_available=False,
            ),
            deploy_template="diffusion_serving",
            default_inference_image="stabilityai/sdxl:latest",
            provider="Stability AI",
        )
    )


# Initialize registry on module load
_initialize_registry()
