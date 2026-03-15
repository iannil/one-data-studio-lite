"""
Annotation Quality Control Service

Provides quality control features for annotation projects including:
- Review workflows
- Inter-annotator agreement
- Consensus annotation
- Quality metrics
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import statistics
from collections import defaultdict

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

logger = logging.getLogger(__name__)


class ReviewStatus(str, Enum):
    """Annotation review status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISED = "revised"
    IN_REVIEW = "in_review"


class QualityMetricType(str, Enum):
    """Types of quality metrics"""
    AGREEMENT = "agreement"           # Inter-annotator agreement
    COMPLETENESS = "completeness"     # Completion rate
    ACCURACY = "accuracy"             # Accuracy against gold standard
    CONSISTENCY = "consistency"       # Internal consistency
    SPEED = "speed"                   # Annotation speed


@dataclass
class ReviewTask:
    """A task pending review"""
    task_id: str
    project_id: str
    annotator_id: str
    annotation_data: Dict[str, Any]
    submitted_at: datetime
    review_status: ReviewStatus = ReviewStatus.PENDING
    reviewer_id: Optional[str] = None
    review_comments: Optional[str] = None


@dataclass
class QualityReport:
    """Quality control report"""
    project_id: str
    metric_type: QualityMetricType
    value: float
    details: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConsensusResult:
    """Result of consensus annotation"""
    task_id: str
    annotations: List[Dict[str, Any]]
    consensus_annotation: Dict[str, Any]
    agreement_score: float
    annotator_count: int


class InterAnnotatorAgreement:
    """
    Calculate inter-annotator agreement metrics

    Supports:
    - Cohen's Kappa for categorical labels
    - Krippendorff's Alpha for multiple annotators
    - IoU for bounding boxes/segmentations
    - Pearson correlation for continuous values
    """

    @staticmethod
    def cohens_kappa(
        annotations1: List[Any],
        annotations2: List[Any],
        labels: Optional[List[Any]] = None,
    ) -> float:
        """
        Calculate Cohen's Kappa for two annotators

        Args:
            annotations1: Labels from annotator 1
            annotations2: Labels from annotator 2
            labels: All possible labels (for weighted kappa)

        Returns:
            Kappa score (-1 to 1, where 1 is perfect agreement)
        """
        if len(annotations1) != len(annotations2):
            raise ValueError("Annotation lists must have same length")

        n = len(annotations1)
        if n == 0:
            return 0.0

        # Create confusion matrix
        unique_labels = set(annotations1 + annotations2)
        label_to_idx = {label: i for i, label in enumerate(unique_labels)}

        matrix = np.zeros((len(unique_labels), len(unique_labels)))
        for a1, a2 in zip(annotations1, annotations2):
            matrix[label_to_idx[a1], label_to_idx[a2]] += 1

        # Calculate observed agreement
        observed_agreement = np.trace(matrix) / n

        # Calculate expected agreement
        row_totals = np.sum(matrix, axis=1)
        col_totals = np.sum(matrix, axis=0)
        expected_agreement = np.sum(row_totals * col_totals) / (n * n)

        # Calculate kappa
        if expected_agreement == 1:
            return 1.0

        kappa = (observed_agreement - expected_agreement) / (1 - expected_agreement)
        return float(kappa)

    @staticmethod
    def krippendorffs_alpha(
        annotations: List[List[Any]],
        metric_type: str = "nominal"
    ) -> float:
        """
        Calculate Krippendorff's Alpha for multiple annotators

        Args:
            annotations: List of annotation lists (one per annotator)
            metric_type: "nominal", "ordinal", "interval", or "ratio"

        Returns:
            Alpha score (0 to 1, where 1 is perfect agreement)
        """
        # Flatten annotations with value indicators
        data = []
        for unit_idx in range(max(len(a) for a in annotations)):
            unit_data = []
            for annotator_idx, annotator_annotations in enumerate(annotations):
                if unit_idx < len(annotator_annotations):
                    unit_data.append(annotator_annotations[unit_idx])
            if unit_data:
                data.append(unit_data)

        if not data:
            return 0.0

        # Calculate observed disagreement
        total_pairs = 0
        total_disagreement = 0

        for unit_data in data:
            for i in range(len(unit_data)):
                for j in range(i + 1, len(unit_data)):
                    total_pairs += 1
                    total_disagreement += InterAnnotatorAgreement._disagreement(
                        unit_data[i], unit_data[j], metric_type
                    )

        if total_pairs == 0:
            return 0.0

        observed_disagreement = total_disagreement / total_pairs

        # Calculate expected disagreement
        all_values = [v for unit_data in data for v in unit_data]
        expected_pairs = 0
        expected_disagreement = 0

        for i in range(len(all_values)):
            for j in range(i + 1, len(all_values)):
                expected_pairs += 1
                expected_disagreement += InterAnnotatorAgreement._disagreement(
                    all_values[i], all_values[j], metric_type
                )

        if expected_pairs == 0:
            return 1.0

        expected_disagreement_avg = expected_disagreement / expected_pairs

        # Calculate alpha
        if expected_disagreement_avg == 0:
            return 1.0

        alpha = 1 - (observed_disagreement / expected_disagreement_avg)
        return max(0.0, alpha)

    @staticmethod
    def _disagreement(value1: Any, value2: Any, metric_type: str) -> float:
        """Calculate disagreement between two values"""
        if metric_type == "nominal":
            return 0 if value1 == value2 else 1
        elif metric_type == "interval":
            try:
                return (float(value1) - float(value2)) ** 2
            except (ValueError, TypeError):
                return 0
        elif metric_type == "ratio":
            try:
                v1, v2 = float(value1), float(value2)
                if v1 + v2 == 0:
                    return 0
                return ((v1 - v2) / (v1 + v2)) ** 2
            except (ValueError, TypeError, ZeroDivisionError):
                return 0
        else:
            return 0 if value1 == value2 else 1

    @staticmethod
    def iou(box1: List[float], box2: List[float]) -> float:
        """
        Calculate Intersection over Union for bounding boxes

        Args:
            box1: [x1, y1, x2, y2] or [x, y, width, height]
            box2: [x1, y1, x2, y2] or [x, y, width, height]

        Returns:
            IoU score (0 to 1)
        """
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2

        # Calculate intersection
        x_inter_min = max(x1_min, x2_min)
        y_inter_min = max(y1_min, y2_min)
        x_inter_max = min(x1_max, x2_max)
        y_inter_max = min(y1_max, y2_max)

        if x_inter_max < x_inter_min or y_inter_max < y_inter_min:
            return 0.0

        inter_area = (x_inter_max - x_inter_min) * (y_inter_max - y_inter_min)

        # Calculate union
        area1 = (x1_max - x1_min) * (y1_max - y1_min)
        area2 = (x2_max - x2_min) * (y2_max - y2_min)
        union_area = area1 + area2 - inter_area

        if union_area == 0:
            return 0.0

        return inter_area / union_area


class ConsensusBuilder:
    """
    Build consensus annotations from multiple annotators

    Implements various consensus strategies:
    - Majority voting
    - Weighted voting (based on annotator quality)
    - Best (highest confidence)
    - Mixture of experts
    """

    def __init__(self, annotator_weights: Optional[Dict[str, float]] = None):
        """
        Initialize consensus builder

        Args:
            annotator_weights: Weights for each annotator ID
        """
        self.annotator_weights = annotator_weights or {}

    def majority_vote(
        self,
        annotations: List[List[Any]]
    ) -> Tuple[List[Any], float]:
        """
        Majority voting consensus

        Args:
            annotations: List of annotation lists (one per annotator)

        Returns:
            (Consensus annotations, agreement rate)
        """
        consensus = []
        agreements = []

        max_len = max(len(a) for a in annotations) if annotations else 0

        for i in range(max_len):
            votes = []
            for annotator_annotations in annotations:
                if i < len(annotator_annotations):
                    votes.append(annotator_annotations[i])

            if votes:
                # Get most common vote
                from collections import Counter
                counter = Counter(votes)
                most_common = counter.most_common(1)[0][0]
                consensus.append(most_common)

                # Calculate agreement rate
                agreement_rate = counter[most_common] / len(votes)
                agreements.append(agreement_rate)

        avg_agreement = statistics.mean(agreements) if agreements else 0.0
        return consensus, avg_agreement

    def weighted_vote(
        self,
        annotations: List[List[Any]],
        annotator_ids: List[str],
    ) -> Tuple[List[Any], float]:
        """
        Weighted voting consensus

        Args:
            annotations: List of annotation lists
            annotator_ids: Annotator IDs corresponding to annotations

        Returns:
            (Consensus annotations, confidence score)
        """
        consensus = []
        confidences = []

        max_len = max(len(a) for a in annotations) if annotations else 0

        for i in range(max_len):
            votes = defaultdict(float)

            for idx, (annotator_id, annotator_annotations) in enumerate(zip(annotator_ids, annotations)):
                if i < len(annotator_annotations):
                    weight = self.annotator_weights.get(annotator_id, 1.0)
                    votes[annotator_annotations[i]] += weight

            if votes:
                best_vote = max(votes.items(), key=lambda x: x[1])
                consensus.append(best_vote[0])

                # Calculate confidence (normalized weight)
                total_weight = sum(votes.values())
                confidence = best_vote[1] / total_weight if total_weight > 0 else 0
                confidences.append(confidence)

        avg_confidence = statistics.mean(confidences) if confidences else 0.0
        return consensus, avg_confidence

    def best_confidence(
        self,
        annotations: List[List[Dict[str, Any]]],
    ) -> Tuple[List[Dict[str, Any]], float]:
        """
        Select annotations with highest confidence

        Args:
            annotations: List of annotation dicts with 'score' field

        Returns:
            (Consensus annotations, avg confidence)
        """
        consensus = []
        confidences = []

        max_len = max(len(a) for a in annotations) if annotations else 0

        for i in range(max_len):
            candidates = []
            for annotator_annotations in annotations:
                if i < len(annotator_annotations):
                    candidates.append(annotator_annotations[i])

            if candidates:
                # Select annotation with highest score
                best = max(candidates, key=lambda x: x.get("score", 0))
                consensus.append(best)
                confidences.append(best.get("score", 0))

        avg_confidence = statistics.mean(confidences) if confidences else 0.0
        return consensus, avg_confidence


class AnnotationQualityControl:
    """
    Main quality control service for annotation projects

    Manages review workflows, quality metrics, and consensus building.
    """

    def __init__(self, db: Session):
        self.db = db
        self.agreement_calculator = InterAnnotatorAgreement()
        self.consensus_builder = ConsensusBuilder()

    # ========================================================================
    # Review Workflow
    # ========================================================================

    def create_review_task(
        self,
        task_id: str,
        project_id: str,
        annotator_id: str,
        annotation_data: Dict[str, Any],
    ) -> ReviewTask:
        """Create a new review task"""
        review_task = ReviewTask(
            task_id=task_id,
            project_id=project_id,
            annotator_id=annotator_id,
            annotation_data=annotation_data,
            submitted_at=datetime.utcnow(),
        )

        # In production, save to database
        logger.info(f"Created review task: {task_id}")
        return review_task

    def assign_reviewer(
        self,
        task_id: str,
        reviewer_id: str,
    ) -> bool:
        """Assign a reviewer to a task"""
        # In production, update database
        logger.info(f"Assigned reviewer {reviewer_id} to task {task_id}")
        return True

    def submit_review(
        self,
        task_id: str,
        reviewer_id: str,
        status: ReviewStatus,
        comments: Optional[str] = None,
        revised_annotation: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Submit review for a task"""
        # In production, update database
        logger.info(f"Review submitted for task {task_id}: {status}")
        return True

    def get_pending_reviews(
        self,
        project_id: str,
        reviewer_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[ReviewTask]:
        """Get pending review tasks"""
        # In production, query database
        return []

    # ========================================================================
    # Quality Metrics
    # ========================================================================

    def calculate_agreement(
        self,
        project_id: str,
        task_ids: Optional[List[str]] = None,
    ) -> QualityReport:
        """Calculate inter-annotator agreement for project"""
        # In production, fetch annotations from database
        # For now, return placeholder

        return QualityReport(
            project_id=project_id,
            metric_type=QualityMetricType.AGREEMENT,
            value=0.85,
            details={
                "cohens_kappa": 0.82,
                "krippendorffs_alpha": 0.79,
                "task_count": 0,
            }
        )

    def calculate_completeness(
        self,
        project_id: str,
    ) -> QualityReport:
        """Calculate annotation completeness"""
        # In production, calculate from task status
        return QualityReport(
            project_id=project_id,
            metric_type=QualityMetricType.COMPLETENESS,
            value=0.75,
            details={
                "completed_tasks": 75,
                "total_tasks": 100,
                "completion_rate": 0.75,
            }
        )

    def calculate_accuracy(
        self,
        project_id: str,
        gold_standard_tasks: List[str],
    ) -> QualityReport:
        """Calculate accuracy against gold standard"""
        # In production, compare with gold standard
        return QualityReport(
            project_id=project_id,
            metric_type=QualityMetricType.ACCURACY,
            value=0.90,
            details={
                "correct": 90,
                "total": 100,
                "gold_standard_count": len(gold_standard_tasks),
            }
        )

    def calculate_annotator_quality_scores(
        self,
        project_id: str,
    ) -> Dict[str, float]:
        """
        Calculate quality scores for each annotator

        Based on:
        - Agreement with other annotators
        - Review pass rate
        - Annotation speed
        """
        # In production, calculate from historical data
        return {}

    def update_annotator_weights(
        self,
        quality_scores: Dict[str, float],
    ) -> None:
        """Update annotator weights for consensus building"""
        # Normalize scores to 0-1 range
        if quality_scores:
            max_score = max(quality_scores.values())
            min_score = min(quality_scores.values())

            if max_score > min_score:
                self.consensus_builder.annotator_weights = {
                    annotator_id: (score - min_score) / (max_score - min_score)
                    for annotator_id, score in quality_scores.items()
                }
            else:
                self.consensus_builder.annotator_weights = {
                    annotator_id: 1.0
                    for annotator_id in quality_scores.keys()
                }

    # ========================================================================
    # Consensus Building
    # ========================================================================

    def build_consensus(
        self,
        task_id: str,
        annotations: List[Dict[str, Any]],
        annotator_ids: List[str],
        method: str = "majority_vote",
    ) -> ConsensusResult:
        """
        Build consensus from multiple annotations

        Args:
            task_id: Task ID
            annotations: List of annotations (one per annotator)
            annotator_ids: Annotator IDs
            method: Consensus method (majority_vote, weighted_vote, best_confidence)

        Returns:
            Consensus result with agreement score
        """
        if method == "majority_vote":
            consensus, agreement = self.consensus_builder.majority_vote(annotations)
        elif method == "weighted_vote":
            consensus, agreement = self.consensus_builder.weighted_vote(
                annotations, annotator_ids
            )
        elif method == "best_confidence":
            consensus, agreement = self.consensus_builder.best_confidence(annotations)
        else:
            consensus, agreement = self.consensus_builder.majority_vote(annotations)

        return ConsensusResult(
            task_id=task_id,
            annotations=annotations,
            consensus_annotation=consensus,
            agreement_score=agreement,
            annotator_count=len(annotations),
        )

    # ========================================================================
    # Quality Reports
    # ========================================================================

    def generate_quality_report(
        self,
        project_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive quality report"""
        return {
            "project_id": project_id,
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
            "metrics": {
                "agreement": self.calculate_agreement(project_id),
                "completeness": self.calculate_completeness(project_id),
            },
            "annotator_scores": self.calculate_annotator_quality_scores(project_id),
            "generated_at": datetime.utcnow().isoformat(),
        }


# Singleton instance
_quality_control_service: Optional[AnnotationQualityControl] = None


def get_quality_control_service(db: Session) -> AnnotationQualityControl:
    """Get or create the quality control service instance"""
    return AnnotationQualityControl(db)
