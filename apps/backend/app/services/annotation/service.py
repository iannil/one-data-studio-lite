"""
Label Studio Annotation Service

Manages annotation projects, tasks, and integrates with MLflow for model-assisted annotation.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.annotation.auth import LabelStudioAuthConfig, LabelStudioTokenGenerator
from app.services.ai_service import AIService
from app.core.config import settings


class LabelStudioProjectConfig:
    """Label Studio project configuration templates"""

    # Computer vision labeling configs
    IMAGE_CLASSIFICATION_CONFIG = """
    <View>
      <Image name="image" value="$image"/>
      <Choices name="choice" toName="image">
        <Choice value="Cat"/>
        <Choice value="Dog"/>
        <Choice value="Bird"/>
        <Choice value="Other"/>
      </Choices>
    </View>
    """

    OBJECT_DETECTION_CONFIG = """
    <View>
      <Image name="image" value="$image"/>
      <RectangleLabels name="label" toName="image">
        <Label value="Person" background="blue"/>
        <Label value="Vehicle" background="red"/>
        <Label value="Animal" background="green"/>
        <Label value="Object" background="yellow"/>
      </RectangleLabels>
    </View>
    """

    SEGMENTATION_CONFIG = """
    <View>
      <Image name="image" value="$image"/>
      <PolygonLabels name="label" toName="image"
                     strokeColor="#00FF00" pointSize="small" opacity="0.9">
        <Label value="Background" background="#000000"/>
        <Label value="Foreground" background="#FF0000"/>
      </PolygonLabels>
    </View>
    """

    # NLP labeling configs
    TEXT_CLASSIFICATION_CONFIG = """
    <View>
      <Text name="text" value="$text"/>
      <Choices name="choice" toName="text">
        <Choice value="Positive"/>
        <Choice value="Negative"/>
        <Choice value="Neutral"/>
      </Choices>
    </View>
    """

    NER_CONFIG = """
    <View>
      <Text name="text" value="$text"/>
      <Labels name="label" toName="text">
        <Label value="Person" background="blue"/>
        <Label value="Organization" background="red"/>
        <Label value="Location" background="green"/>
        <Label value="Date" background="yellow"/>
      </Labels>
    </View>
    """

    # Multi-modal config
    MULTIMODAL_CONFIG = """
    <View>
      <Image name="image" value="$image"/>
      <Text name="text" value="$text"/>
      <TextArea name="comment" toName="image"/>
    </View>
    """


class AutoAnnotationService:
    """
    Automated annotation using AI models.

    Integrates with AIHub models for pre-annotation and active learning.
    """

    def __init__(self, ai_service: AIService = None):
        self.ai_service = ai_service  # Optional: may be injected
        self.config = LabelStudioAuthConfig()

    async def pre_annotate_image(
        self,
        image_url: str,
        task_type: str,
        model: str = "gpt-4-vision-preview"
    ) -> Dict[str, Any]:
        """
        Pre-annotate image using vision models.

        Args:
            image_url: URL to image
            task_type: Type of annotation (classification, detection, etc.)
            model: Model to use for prediction

        Returns:
            Label Studio compatible predictions
        """
        try:
            if task_type == "classification":
                return await self._classify_image(image_url, model)
            elif task_type == "detection":
                return await self._detect_objects(image_url, model)
            elif task_type == "captioning":
                return await self._generate_caption(image_url, model)
            else:
                return {"result": [], "score": 0}
        except Exception as e:
            return {
                "result": [],
                "score": 0,
                "error": str(e)
            }

    async def _classify_image(
        self,
        image_url: str,
        model: str
    ) -> Dict[str, Any]:
        """Classify image using vision model"""
        prompt = """Classify this image into one of these categories:
        - Cat
        - Dog
        - Bird
        - Other

        Return only the category name."""

        response = await self.ai_service.complete(
            model=model,
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]}
            ],
            max_tokens=50
        )

        category = response.get("content", "Other").strip()

        return {
            "result": [{
                "from_name": "choice",
                "to_name": "image",
                "type": "choices",
                "value": {"choices": [category]}
            }],
            "score": 0.85,
            "model": model
        }

    async def _detect_objects(
        self,
        image_url: str,
        model: str
    ) -> Dict[str, Any]:
        """Detect objects in image"""
        # In production, use dedicated object detection models
        # For now, return placeholder
        return {
            "result": [],
            "score": 0,
            "model": model,
            "message": "Object detection requires specialized model"
        }

    async def _generate_caption(
        self,
        image_url: str,
        model: str
    ) -> Dict[str, Any]:
        """Generate image caption"""
        prompt = "Describe this image in one sentence."

        response = await self.ai_service.complete(
            model=model,
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]}
            ],
            max_tokens=200
        )

        caption = response.get("content", "")

        return {
            "result": [{
                "from_name": "comment",
                "to_name": "image",
                "type": "textarea",
                "value": {"text": [caption]}
            }],
            "score": 0.8,
            "model": model
        }

    async def pre_annotate_text(
        self,
        text: str,
        task_type: str,
        labels: List[str],
        model: str = "gpt-4"
    ) -> Dict[str, Any]:
        """
        Pre-annotate text using LLM.

        Args:
            text: Text to annotate
            task_type: Type of annotation (classification, ner, etc.)
            labels: Available labels
            model: Model to use

        Returns:
            Label Studio compatible predictions
        """
        if task_type == "classification":
            return await self._classify_text(text, labels, model)
        elif task_type == "ner":
            return await self._extract_entities(text, labels, model)
        else:
            return {"result": [], "score": 0}

    async def _classify_text(
        self,
        text: str,
        labels: List[str],
        model: str
    ) -> Dict[str, Any]:
        """Classify text"""
        labels_str = ", ".join(labels)
        prompt = f"""Classify the following text into one of these categories: {labels_str}

Text: {text}

Return only the category name."""

        response = await self.ai_service.complete(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50
        )

        category = response.get("content", labels[0]).strip()

        return {
            "result": [{
                "from_name": "choice",
                "to_name": "text",
                "type": "choices",
                "value": {"choices": [category]}
            }],
            "score": 0.85,
            "model": model
        }

    async def _extract_entities(
        self,
        text: str,
        labels: List[str],
        model: str
    ) -> Dict[str, Any]:
        """Extract named entities from text"""
        labels_str = ", ".join(labels)
        prompt = f"""Extract entities from the following text. Entity types: {labels_str}

Text: {text}

Return as JSON: {{"entities": [{{"text": "...", "label": "...", "start": 0, "end": 10}}]}}"""

        response = await self.ai_service.complete(
            model=model,
            messages=[
                {"role": "system", "content": "You are a named entity recognition expert. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0
        )

        try:
            data = json.loads(response.get("content", "{}"))
            entities = data.get("entities", [])

            results = []
            for entity in entities:
                results.append({
                    "from_name": "label",
                    "to_name": "text",
                    "type": "labels",
                    "value": {
                        "start": entity.get("start", 0),
                        "end": entity.get("end", 0),
                        "labels": [entity.get("label", "Unknown")]
                    }
                })

            return {
                "result": results,
                "score": 0.8,
                "model": model
            }
        except json.JSONDecodeError:
            return {"result": [], "score": 0}

    async def active_learning_sample(
        self,
        project_id: int,
        n_samples: int = 10
    ) -> List[int]:
        """
        Select samples for active learning based on uncertainty.

        Args:
            project_id: Label Studio project ID
            n_samples: Number of samples to select

        Returns:
            List of task IDs to annotate
        """
        # In production, use uncertainty sampling, entropy, etc.
        # For now, return placeholder
        return []


class AnnotationService:
    """
    Main annotation service managing Label Studio projects.

    Provides API proxy and integration with platform features.
    """

    def __init__(self):
        self.config = LabelStudioAuthConfig()
        self.auto_annotation = AutoAnnotationService()
        self.token_generator = LabelStudioTokenGenerator()

    async def create_project(
        self,
        name: str,
        description: str,
        labeling_config: str,
        task_type: str = "image_classification",
        auto_annotation: bool = False,
        mlflow_run_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new Label Studio project.

        Args:
            name: Project name
            description: Project description
            labeling_config: Labeling configuration XML
            task_type: Type of annotation task
            auto_annotation: Enable model-assisted annotation
            mlflow_run_id: MLflow run for model-assisted annotation

        Returns:
            Created project details
        """
        # In production, call Label Studio API
        project = {
            "id": f"proj_{datetime.utcnow().timestamp()}",
            "name": name,
            "description": description,
            "labeling_config": labeling_config,
            "task_type": task_type,
            "auto_annotation": auto_annotation,
            "mlflow_run_id": mlflow_run_id,
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
            "stats": {
                "total_tasks": 0,
                "completed_tasks": 0,
                "skipped_tasks": 0,
                "completion_rate": 0.0
            }
        }

        return project

    async def get_projects(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all projects accessible to user"""
        # In production, call Label Studio API
        return []

    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project details"""
        # In production, call Label Studio API
        return None

    async def import_tasks(
        self,
        project_id: str,
        tasks: List[Dict[str, Any]],
        preannotate: bool = False,
        model: str = "gpt-4-vision-preview"
    ) -> Dict[str, Any]:
        """
        Import tasks to project.

        Args:
            project_id: Target project
            tasks: List of tasks to import
            preannotate: Generate pre-annotations
            model: Model for pre-annotation

        Returns:
            Import result
        """
        results = {
            "project_id": project_id,
            "imported": len(tasks),
            "preannotated": 0,
            "failed": 0,
            "tasks": []
        }

        if preannotate:
            for task in tasks:
                try:
                    prediction = await self._generate_prediction(task, model)
                    if prediction.get("result"):
                        task["predictions"] = [prediction]
                        results["preannotated"] += 1
                except Exception:
                    results["failed"] += 1

                results["tasks"].append({
                    "id": f"task_{len(results['tasks'])}",
                    "data": task.get("data", {}),
                    "has_prediction": "predictions" in task
                })

        return results

    async def _generate_prediction(
        self,
        task: Dict[str, Any],
        model: str
    ) -> Dict[str, Any]:
        """Generate prediction for a task"""
        data = task.get("data", {})

        # Check for image
        if "image" in data:
            return await self.auto_annotation.pre_annotate_image(
                data["image"],
                "classification",
                model
            )

        # Check for text
        if "text" in data:
            labels = data.get("labels", ["Positive", "Negative", "Neutral"])
            return await self.auto_annotation.pre_annotate_text(
                data["text"],
                "classification",
                labels,
                model
            )

        return {"result": []}

    async def export_annotations(
        self,
        project_id: str,
        export_format: str = "JSON",
        only_finished: bool = True
    ) -> Dict[str, Any]:
        """
        Export annotations from project.

        Args:
            project_id: Source project
            export_format: Output format (JSON, CSV, COCO, VOC, etc.)
            only_finished: Export only completed annotations

        Returns:
            Export result
        """
        # In production, call Label Studio export API
        return {
            "project_id": project_id,
            "format": export_format,
            "annotations": [],
            "exported_at": datetime.utcnow().isoformat()
        }

    async def get_project_stats(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """Get project statistics"""
        return {
            "project_id": project_id,
            "total_tasks": 0,
            "completed_tasks": 0,
            "in_progress_tasks": 0,
            "skipped_tasks": 0,
            "total_annotations": 0,
            "completion_rate": 0.0,
            "annotators": [],
            "average_time_per_task": 0
        }

    async def delete_project(self, project_id: str) -> bool:
        """Delete a project"""
        # In production, call Label Studio API
        return True


class AnnotationMetricsService:
    """Metrics and analytics for annotation projects"""

    async def get_annotator_performance(
        self,
        project_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get annotator performance metrics"""
        return []

    async def get_annotation_quality(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """Get annotation quality metrics"""
        return {
            "project_id": project_id,
            "agreement_score": 0.0,
            "quality_score": 0.0,
            "review_rate": 0.0
        }

    async def get_label_distribution(
        self,
        project_id: str
    ) -> Dict[str, int]:
        """Get label distribution"""
        return {}
