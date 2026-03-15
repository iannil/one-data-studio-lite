"""
Data Collection Service Package

Provides online data collection and回流 to data lake:
- Batch, scheduled, streaming, and event-driven collection
- Multiple source connectors (Database, API, Kafka, File)
- Quality validation
- Orchestrator for managing collections
"""

from .orchestrator import (
    DataConnector,
    DatabaseConnector,
    APIConnector,
    KafkaConnector,
    FileConnector,
    QualityValidator,
    DataCollectionOrchestrator,
    CollectionResult,
    get_collection_orchestrator,
)

__all__ = [
    # Connectors
    "DataConnector",
    "DatabaseConnector",
    "APIConnector",
    "KafkaConnector",
    "FileConnector",
    # Quality
    "QualityValidator",
    # Orchestrator
    "DataCollectionOrchestrator",
    "CollectionResult",
    "get_collection_orchestrator",
]
