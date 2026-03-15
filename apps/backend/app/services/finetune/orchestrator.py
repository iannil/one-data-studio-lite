"""
Fine-tuning Pipeline Orchestrator

Orchestrates the execution of fine-tuning pipelines across
multiple stages: data preparation, training, evaluation,
registration, and deployment.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finetune import (
    FinetunePipeline,
    FinetuneStage,
    FinetuneCheckpoint,
    FinetuneMetric,
)

logger = logging.getLogger(__name__)


class FinetuneOrchestrator:
    """
    Fine-tuning pipeline orchestrator

    Manages the end-to-end execution of fine-tuning pipelines
    with automatic stage progression and error handling.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize orchestrator

        Args:
            db: Database session
        """
        self.db = db
        self._running_executions: Dict[str, asyncio.Task] = {}

    async def create_pipeline(
        self,
        name: str,
        base_model_id: str,
        base_model_name: str,
        base_model_type: str,
        config: Dict[str, Any],
        owner_id: str,
        dataset_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> FinetunePipeline:
        """
        Create a new fine-tuning pipeline

        Args:
            name: Pipeline name
            base_model_id: Base model ID
            base_model_name: Base model name
            base_model_type: Base model type
            config: Pipeline configuration
            owner_id: Owner user ID
            dataset_id: Training dataset ID
            tenant_id: Tenant ID
            project_id: Project ID

        Returns:
            Created pipeline
        """
        pipeline_id = f"ft-{uuid4().hex[:8]}"

        pipeline = FinetunePipeline(
            pipeline_id=pipeline_id,
            name=name,
            description=config.get("description"),
            base_model_id=base_model_id,
            base_model_name=base_model_name,
            base_model_type=base_model_type,
            finetune_method=config.get("finetune_method", "lora"),
            lora_rank=config.get("lora_rank"),
            lora_alpha=config.get("lora_alpha"),
            lora_dropout=config.get("lora_dropout"),
            dataset_id=dataset_id,
            eval_dataset_id=config.get("eval_dataset_id"),
            test_dataset_id=config.get("test_dataset_id"),
            learning_rate=config.get("learning_rate"),
            batch_size=config.get("batch_size"),
            num_epochs=config.get("num_epochs"),
            max_steps=config.get("max_steps"),
            warmup_steps=config.get("warmup_steps"),
            weight_decay=config.get("weight_decay"),
            gradient_accumulation_steps=config.get("gradient_accumulation_steps"),
            gpu_type=config.get("gpu_type"),
            gpu_count=config.get("gpu_count"),
            distributed_backend=config.get("distributed_backend"),
            output_dir=config.get("output_dir"),
            save_steps=config.get("save_steps"),
            save_total_limit=config.get("save_total_limit"),
            eval_steps=config.get("eval_steps"),
            eval_strategy=config.get("eval_strategy"),
            current_stage="data_prep",
            tags=config.get("tags"),
            labels=config.get("labels"),
            owner_id=owner_id,
            tenant_id=tenant_id,
            project_id=project_id,
        )

        self.db.add(pipeline)
        await self.db.commit()
        await self.db.refresh(pipeline)

        logger.info(f"Created fine-tuning pipeline {pipeline_id}")

        return pipeline

    async def execute_pipeline(
        self,
        pipeline_id: str,
        auto_advance: bool = True,
        start_from: Optional[str] = None,
    ) -> str:
        """
        Execute a fine-tuning pipeline

        Args:
            pipeline_id: Pipeline ID
            auto_advance: Automatically advance through stages
            start_from: Start from specific stage

        Returns:
            Execution ID
        """
        pipeline = await self.get_pipeline(pipeline_id)
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")

        execution_id = f"exec-{uuid4().hex[:8]}"

        # Update pipeline status
        pipeline.current_stage = start_from or "data_prep"
        pipeline.started_at = datetime.utcnow()
        await self.db.commit()

        # Create background task for execution
        task = asyncio.create_task(
            self._execute_pipeline_async(
                pipeline_id, execution_id, auto_advance
            )
        )
        self._running_executions[execution_id] = task

        logger.info(f"Started execution {execution_id} for pipeline {pipeline_id}")

        return execution_id

    async def _execute_pipeline_async(
        self,
        pipeline_id: str,
        execution_id: str,
        auto_advance: bool,
    ) -> None:
        """
        Async pipeline execution

        Args:
            pipeline_id: Pipeline ID
            execution_id: Execution ID
            auto_advance: Auto-advance through stages
        """
        pipeline = await self.get_pipeline(pipeline_id)
        if not pipeline:
            return

        stages = ["data_prep", "training", "evaluation", "registration", "deployment"]

        try:
            for stage in stages:
                # Skip if starting from a later stage
                if pipeline.current_stage != stage:
                    continue

                # Execute stage
                await self._execute_stage(pipeline, stage, execution_id)

                # Check if stage failed
                stage_status = self._get_stage_status(pipeline, stage)
                if stage_status == "failed":
                    pipeline.current_stage = "failed"
                    await self.db.commit()
                    logger.error(f"Pipeline {pipeline_id} failed at stage {stage}")
                    return

                # Advance to next stage
                if auto_advance:
                    next_stage_idx = stages.index(stage) + 1
                    if next_stage_idx < len(stages):
                        pipeline.current_stage = stages[next_stage_idx]
                        await self.db.commit()

            # All stages completed
            pipeline.current_stage = "completed"
            pipeline.completed_at = datetime.utcnow()
            await self.db.commit()

            logger.info(f"Pipeline {pipeline_id} completed successfully")

        except Exception as e:
            logger.error(f"Error executing pipeline {pipeline_id}: {e}")
            pipeline.current_stage = "failed"
            await self.db.commit()

        finally:
            # Clean up execution tracking
            if execution_id in self._running_executions:
                del self._running_executions[execution_id]

    async def _execute_stage(
        self,
        pipeline: FinetunePipeline,
        stage: str,
        execution_id: str,
    ) -> None:
        """
        Execute a single stage

        Args:
            pipeline: Pipeline instance
            stage: Stage to execute
            execution_id: Execution ID
        """
        stage_id = f"stage-{uuid4().hex[:8]}"

        # Create stage record
        stage_record = FinetuneStage(
            stage_id=stage_id,
            pipeline_id=pipeline.pipeline_id,
            stage_type=stage,
            stage_name=f"{stage.replace('_', ' ').title()} Stage",
            status="running",
            started_at=datetime.utcnow(),
        )
        self.db.add(stage_record)
        await self.db.commit()

        try:
            # Update pipeline stage status
            self._set_stage_status(pipeline, stage, "running")
            await self.db.commit()

            # Execute stage-specific logic
            if stage == "data_prep":
                await self._execute_data_prep(pipeline, stage_record)
            elif stage == "training":
                await self._execute_training(pipeline, stage_record)
            elif stage == "evaluation":
                await self._execute_evaluation(pipeline, stage_record)
            elif stage == "registration":
                await self._execute_registration(pipeline, stage_record)
            elif stage == "deployment":
                await self._execute_deployment(pipeline, stage_record)

            # Mark stage as completed
            stage_record.status = "completed"
            stage_record.completed_at = datetime.utcnow()
            if stage_record.started_at:
                stage_record.duration_seconds = int(
                    (stage_record.completed_at - stage_record.started_at).total_seconds()
                )

            self._set_stage_status(pipeline, stage, "completed")
            await self.db.commit()

        except Exception as e:
            logger.error(f"Error in stage {stage}: {e}")
            stage_record.status = "failed"
            stage_record.error_message = str(e)
            stage_record.completed_at = datetime.utcnow()
            self._set_stage_status(pipeline, stage, "failed")
            await self.db.commit()
            raise

    async def _execute_data_prep(
        self,
        pipeline: FinetunePipeline,
        stage_record: FinetuneStage,
    ) -> None:
        """Execute data preparation stage"""
        # TODO: Implement actual data preparation logic
        # - Load dataset
        # - Validate format
        # - Apply preprocessing
        # - Split into train/eval/test
        # - Save processed data

        stage_record.result = {
            "status": "completed",
            "samples_processed": 0,
            "output_path": f"/data/processed/{pipeline.pipeline_id}",
        }
        stage_record.output_path = f"/data/processed/{pipeline.pipeline_id}"

    async def _execute_training(
        self,
        pipeline: FinetunePipeline,
        stage_record: FinetuneStage,
    ) -> None:
        """Execute training stage"""
        # TODO: Implement actual training logic
        # - Configure training environment
        # - Launch training job
        # - Monitor progress
        # - Save checkpoints

        # Create training job
        training_job_id = f"train-{uuid4().hex[:8]}"
        pipeline.training_job_id = training_job_id

        stage_record.result = {
            "status": "completed",
            "training_job_id": training_job_id,
            "final_loss": 0.0,
        }

    async def _execute_evaluation(
        self,
        pipeline: FinetunePipeline,
        stage_record: FinetuneStage,
    ) -> None:
        """Execute evaluation stage"""
        # TODO: Implement actual evaluation logic
        # - Load trained model
        # - Run evaluation on test set
        # - Compute metrics
        # - Generate evaluation report

        stage_record.result = {
            "status": "completed",
            "metrics": {
                "accuracy": 0.0,
                "f1": 0.0,
                "precision": 0.0,
                "recall": 0.0,
            },
        }

        pipeline.eval_metrics = stage_record.result.get("metrics")

    async def _execute_registration(
        self,
        pipeline: FinetunePipeline,
        stage_record: FinetuneStage,
    ) -> None:
        """Execute model registration stage"""
        # TODO: Implement actual model registration logic
        # - Package model artifacts
        # - Register in model registry
        # - Create model version
        # - Link metadata

        model_version = f"v1-{uuid4().hex[:6]}"
        pipeline.model_version = model_version

        stage_record.result = {
            "status": "completed",
            "model_version": model_version,
        }

    async def _execute_deployment(
        self,
        pipeline: FinetunePipeline,
        stage_record: FinetuneStage,
    ) -> None:
        """Execute deployment stage"""
        # TODO: Implement actual deployment logic
        # - Create deployment configuration
        # - Deploy to inference service
        # - Configure scaling
        # - Set up monitoring

        deployment_id = f"deploy-{uuid4().hex[:8]}"
        pipeline.deployment_id = deployment_id

        stage_record.result = {
            "status": "completed",
            "deployment_id": deployment_id,
        }

    def _get_stage_status(self, pipeline: FinetunePipeline, stage: str) -> str:
        """Get status of a stage"""
        status_map = {
            "data_prep": pipeline.data_prep_status,
            "training": pipeline.training_status,
            "evaluation": pipeline.evaluation_status,
            "registration": pipeline.registration_status,
            "deployment": pipeline.deployment_status,
        }
        return status_map.get(stage, "pending")

    def _set_stage_status(self, pipeline: FinetunePipeline, stage: str, status: str) -> None:
        """Set status of a stage"""
        if stage == "data_prep":
            pipeline.data_prep_status = status
        elif stage == "training":
            pipeline.training_status = status
        elif stage == "evaluation":
            pipeline.evaluation_status = status
        elif stage == "registration":
            pipeline.registration_status = status
        elif stage == "deployment":
            pipeline.deployment_status = status

    async def get_pipeline(self, pipeline_id: str) -> Optional[FinetunePipeline]:
        """Get pipeline by ID"""
        result = await self.db.execute(
            select(FinetunePipeline).where(
                FinetunePipeline.pipeline_id == pipeline_id
            )
        )
        return result.scalar_one_or_none()

    async def list_pipelines(
        self,
        owner_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[FinetunePipeline], int]:
        """List pipelines with filtering"""
        conditions = []

        if owner_id:
            conditions.append(FinetunePipeline.owner_id == owner_id)
        if status:
            conditions.append(FinetunePipeline.current_stage == status)

        # Get total count
        from sqlalchemy import func
        count_query = select(func.count(FinetunePipeline.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Get results
        query = select(FinetunePipeline)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(FinetunePipeline.created_at.desc())
        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        pipelines = result.scalars().all()

        return list(pipelines), total

    async def stop_pipeline(self, pipeline_id: str) -> bool:
        """Stop a running pipeline"""
        # TODO: Implement actual stop logic
        # - Cancel training job
        # - Update status
        # - Clean up resources
        pipeline = await self.get_pipeline(pipeline_id)
        if pipeline:
            pipeline.current_stage = "cancelled"
            await self.db.commit()
            return True
        return False

    async def get_pipeline_stages(
        self,
        pipeline_id: str,
    ) -> List[FinetuneStage]:
        """Get all stages for a pipeline"""
        result = await self.db.execute(
            select(FinetuneStage).where(
                FinetuneStage.pipeline_id == pipeline_id
            ).order_by(FinetuneStage.created_at)
        )
        return list(result.scalars().all())

    async def get_pipeline_checkpoints(
        self,
        pipeline_id: str,
    ) -> List[FinetuneCheckpoint]:
        """Get all checkpoints for a pipeline"""
        result = await self.db.execute(
            select(FinetuneCheckpoint).where(
                FinetuneCheckpoint.pipeline_id == pipeline_id
            ).order_by(FinetuneCheckpoint.step)
        )
        return list(result.scalars().all())

    async def get_pipeline_metrics(
        self,
        pipeline_id: str,
    ) -> List[FinetuneMetric]:
        """Get all metrics for a pipeline"""
        result = await self.db.execute(
            select(FinetuneMetric).where(
                FinetuneMetric.pipeline_id == pipeline_id
            ).order_by(FinetuneMetric.step)
        )
        return list(result.scalars().all())
