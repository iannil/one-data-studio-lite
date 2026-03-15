"""
EFK Log Aggregator Service

Integrates with Elasticsearch, Fluentd, and Kibana for log aggregation.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class LogAggregator:
    """
    EFK log aggregation manager

    Handles integration with Elasticsearch for log storage,
    Fluentd for log collection, and Kibana for visualization.
    """

    def __init__(
        self,
        elasticsearch_url: str = "http://elasticsearch:9200",
        elasticsearch_user: Optional[str] = None,
        elasticsearch_password: Optional[str] = None,
    ):
        """
        Initialize log aggregator

        Args:
            elasticsearch_url: Elasticsearch endpoint
            elasticsearch_user: Elasticsearch username
            elasticsearch_password: Elasticsearch password
        """
        self.elasticsearch_url = elasticsearch_url
        self.elasticsearch_user = elasticsearch_user
        self.elasticsearch_password = elasticsearch_password
        self._es_client = None

    @property
    def es_client(self):
        """Lazy load Elasticsearch client"""
        if self._es_client is None:
            try:
                from elasticsearch import Elasticsearch

                client_config = {"hosts": [self.elasticsearch_url]}
                if self.elasticsearch_user:
                    client_config["basic_auth"] = (self.elasticsearch_user, self.elasticsearch_password)

                self._es_client = Elasticsearch(**client_config)
            except ImportError:
                logger.warning("elasticsearch-py not installed")
                self._es_client = None

        return self._es_client

    async def create_index(
        self,
        index_name: str,
        index_pattern: Optional[str] = None,
        retention_days: int = 30,
        shard_count: int = 1,
        replica_count: int = 1,
    ) -> Dict[str, Any]:
        """
        Create a log index in Elasticsearch

        Args:
            index_name: Index name
            index_pattern: Index pattern for logs
            retention_days: Data retention period
            shard_count: Number of shards
            replica_count: Number of replicas

        Returns:
            Index creation result
        """
        if not self.es_client:
            raise RuntimeError("Elasticsearch client not available")

        # Index template with proper mappings for logs
        index_template = {
            "index_patterns": [index_pattern or f"{index_name}-*"],
            "template": {
                "settings": {
                    "number_of_shards": shard_count,
                    "number_of_replicas": replica_count,
                    "index.lifecycle.name": f"{index_name}-policy",
                    "index.lifecycle.rollover_alias": f"{index_name}",
                },
                "mappings": {
                    "properties": {
                        "@timestamp": {"type": "date"},
                        "level": {"type": "keyword"},
                        "message": {"type": "text"},
                        "service": {"type": "keyword"},
                        "host": {"type": "keyword"},
                        "tenant_id": {"type": "keyword"},
                        "trace_id": {"type": "keyword"},
                        "span_id": {"type": "keyword"},
                        "user_id": {"type": "keyword"},
                        "job_id": {"type": "keyword"},
                        "tags": {"type": "keyword"},
                    }
                },
            },
        }

        try:
            # Create index template
            self.es_client.indices.put_index_template(
                name=f"{index_name}-template",
                body=index_template,
            )

            # Create index lifecycle policy
            ilm_policy = {
                "policy": {
                    "phases": [
                        {
                            "min_age": "7d",
                            "actions": {"rollover": {"max_size": "50GB", "max_age": "30d"}},
                        }
                    ]
                }
            }

            self.es_client.ilm.put_lifecycle(
                name=f"{index_name}-policy",
                body=ilm_policy,
            )

            return {
                "index_name": index_name,
                "status": "created",
                "retention_days": retention_days,
            }

        except Exception as e:
            logger.error(f"Failed to create Elasticsearch index: {e}")
            raise

    async def ingest_log(
        self,
        index_name: str,
        log_entry: Dict[str, Any],
    ) -> str:
        """
        Ingest a log entry to Elasticsearch

        Args:
            index_name: Target index
            log_entry: Log entry data

        Returns:
            Document ID
        """
        if not self.es_client:
            raise RuntimeError("Elasticsearch client not available")

        # Add timestamp if not present
        if "@timestamp" not in log_entry:
            log_entry["@timestamp"] = datetime.utcnow().isoformat()

        try:
            result = self.es_client.index(
                index=index_name,
                body=log_entry,
            )
            return result["_id"]

        except Exception as e:
            logger.error(f"Failed to ingest log: {e}")
            raise

    async def query_logs(
        self,
        index_pattern: str,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        size: int = 100,
        sort: str = "@timestamp:desc",
    ) -> Dict[str, Any]:
        """
        Query logs from Elasticsearch

        Args:
            index_pattern: Index pattern to query
            query: Full-text query string
            filters: Field filters
            start_time: Start time range
            end_time: End time range
            size: Maximum number of results
            sort: Sort order

        Returns:
            Query results
        """
        if not self.es_client:
            raise RuntimeError("Elasticsearch client not available")

        # Build Elasticsearch query
        es_query = {"bool": {}}

        # Add filters
        filter_clauses = []

        if query:
            es_query["bool"]["must"] = [
                {"query_string": {"query": query}}
            ]

        if filters:
            for field, value in filters.items():
                filter_clauses.append({"term": {field: value}})

        if start_time or end_time:
            range_filter = {"range": {"@timestamp": {}}}
            if start_time:
                range_filter["range"]["@timestamp"]["gte"] = start_time.isoformat()
            if end_time:
                range_filter["range"]["@timestamp"]["lte"] = end_time.isoformat()
            filter_clauses.append(range_filter)

        if filter_clauses:
            if "must" not in es_query["bool"]:
                es_query["bool"]["must"] = []
            es_query["bool"]["must"].extend(filter_clauses)

        try:
            result = self.es_client.search(
                index=index_pattern,
                body={
                    "query": es_query,
                    "size": size,
                    "sort": sort,
                },
            )

            hits = result.get("hits", {}).get("hits", [])

            return {
                "total": result.get("hits", {}).get("total", {}).get("value", 0),
                "logs": [hit.get("_source") for hit in hits],
            }

        except Exception as e:
            logger.error(f"Failed to query logs: {e}")
            raise

    async def aggregate_logs(
        self,
        index_pattern: str,
        aggregation: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Aggregate logs from Elasticsearch

        Args:
            index_pattern: Index pattern to query
            aggregation: Aggregation configuration
            filters: Field filters
            start_time: Start time range
            end_time: End time range

        Returns:
            Aggregation results
        """
        if not self.es_client:
            raise RuntimeError("Elasticsearch client not available")

        # Build query with aggregations
        es_query = {"size": 0, "aggs": aggregation}

        if filters:
            es_query["query"] = {"bool": {"must": []}}
            for field, value in filters.items():
                es_query["query"]["bool"]["must"].append({"term": {field: value}})

        if start_time or end_time:
            if "query" not in es_query:
                es_query["query"] = {"bool": {"must": []}}
            range_filter = {"range": {"@timestamp": {}}}
            if start_time:
                range_filter["range"]["@timestamp"]["gte"] = start_time.isoformat()
            if end_time:
                range_filter["range"]["@timestamp"]["lte"] = end_time.isoformat()
            es_query["query"]["bool"]["must"].append(range_filter)

        try:
            result = self.es_client.search(
                index=index_pattern,
                body=es_query,
            )

            return result.get("aggregations", {})

        except Exception as e:
            logger.error(f"Failed to aggregate logs: {e}")
            raise

    async def delete_index(
        self,
        index_name: str,
    ) -> bool:
        """
        Delete a log index

        Args:
            index_name: Index to delete

        Returns:
            True if successful
        """
        if not self.es_client:
            raise RuntimeError("Elasticsearch client not available")

        try:
            self.es_client.indices.delete(index=index_name)
            return True

        except Exception as e:
            logger.error(f"Failed to delete index: {e}")
            return False

    async def get_index_stats(
        self,
        index_pattern: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get index statistics

        Args:
            index_pattern: Index pattern (or all indices)

        Returns:
            Index statistics
        """
        if not self.es_client:
            raise RuntimeError("Elasticsearch client not available")

        try:
            if index_pattern:
                stats = self.es_client.indices.stats(index=index_pattern)
            else:
                stats = self.es_client.indices.stats()

            return stats

        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {}


def get_log_aggregator(
    elasticsearch_url: str = "http://elasticsearch:9200",
    elasticsearch_user: Optional[str] = None,
    elasticsearch_password: Optional[str] = None,
) -> LogAggregator:
    """Get or create log aggregator instance"""
    return LogAggregator(
        elasticsearch_url=elasticsearch_url,
        elasticsearch_user=elasticsearch_user,
        elasticsearch_password=elasticsearch_password,
    )
