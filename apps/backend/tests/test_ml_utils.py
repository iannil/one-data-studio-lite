from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

import pandas as pd
import numpy as np

from app.services.ml_utils import (
    TimeSeriesForecaster,
    AnomalyDetector,
    EnhancedClustering,
)


class TestTimeSeriesForecaster:
    """Test TimeSeriesForecaster functionality."""

    @pytest.fixture
    def sample_time_series_data(self):
        """Generate sample time series data for testing."""
        base_date = datetime.now(timezone.utc)
        data = []
        for i in range(30):
            date = base_date - timedelta(days=30 - i)
            value = 100 + i * 2 + np.random.randn() * 5  # Upward trend with noise
            data.append({
                "date": date.isoformat(),
                "value": round(value, 2),
            })
        return data

    def test_forecast_insufficient_data(self):
        """Test forecast with insufficient data."""
        forecaster = TimeSeriesForecaster()
        result = forecaster.forecast(
            data=[{"date": "2026-01-01", "value": 10}],
            date_column="date",
            value_column="value",
            periods=7,
        )

        assert "error" in result
        assert result["error"] == "Insufficient data for forecasting"
        assert result["min_required"] == 3

    def test_forecast_moving_average(self, sample_time_series_data):
        """Test moving average forecast."""
        forecaster = TimeSeriesForecaster()
        result = forecaster.forecast(
            data=sample_time_series_data,
            date_column="date",
            value_column="value",
            periods=5,
            method="moving_average",
        )

        assert "predictions" in result
        assert len(result["predictions"]) == 5
        assert result["method"] == "moving_average"
        assert "trend" in result
        assert "historical_mean" in result

    def test_forecast_exponential_smoothing(self, sample_time_series_data):
        """Test exponential smoothing forecast."""
        forecaster = TimeSeriesForecaster()
        result = forecaster.forecast(
            data=sample_time_series_data,
            date_column="date",
            value_column="value",
            periods=5,
            method="exponential_smooth",
        )

        assert "predictions" in result
        assert len(result["predictions"]) == 5
        assert result["method"] == "exponential_smooth"

    def test_forecast_trend(self, sample_time_series_data):
        """Test linear trend forecast."""
        forecaster = TimeSeriesForecaster()
        result = forecaster.forecast(
            data=sample_time_series_data,
            date_column="date",
            value_column="value",
            periods=5,
            method="trend",
        )

        assert "predictions" in result
        assert len(result["predictions"]) == 5
        assert result["method"] == "trend"

    def test_forecast_auto_method_selection(self, sample_time_series_data):
        """Test automatic method selection."""
        forecaster = TimeSeriesForecaster()
        result = forecaster.forecast(
            data=sample_time_series_data,
            date_column="date",
            value_column="value",
            periods=5,
            method="auto",
        )

        assert "predictions" in result
        assert len(result["predictions"]) == 5
        assert result["method"] in ["moving_average", "exponential_smooth", "trend"]

    def test_prediction_structure(self, sample_time_series_data):
        """Test prediction structure includes required fields."""
        forecaster = TimeSeriesForecaster()
        result = forecaster.forecast(
            data=sample_time_series_data,
            date_column="date",
            value_column="value",
            periods=3,
        )

        prediction = result["predictions"][0]
        assert "date" in prediction
        assert "value" in prediction
        assert "lower_bound" in prediction
        assert "upper_bound" in prediction
        assert "confidence" in prediction


class TestAnomalyDetector:
    """Test AnomalyDetector functionality."""

    @pytest.fixture
    def sample_normal_data(self):
        """Generate sample data with some anomalies."""
        data = []
        for i in range(100):
            data.append({
                "id": i,
                "value1": np.random.normal(50, 10),
                "value2": np.random.normal(100, 20),
                "category": "A" if i % 2 == 0 else "B",
            })
        # Add some anomalies
        data.append({"id": 100, "value1": 200, "value2": 500, "category": "A"})
        data.append({"id": 101, "value1": -50, "value2": -100, "category": "B"})
        return data

    def test_anomaly_detection_no_features(self):
        """Test with no valid features."""
        detector = AnomalyDetector()
        result = detector.detect(
            data=[{"id": 1, "name": "test"}],
            features=["nonexistent"],
        )

        assert "error" in result

    def test_isolation_forest_detection(self, sample_normal_data):
        """Test Isolation Forest anomaly detection."""
        detector = AnomalyDetector(contamination=0.05)
        result = detector.detect(
            data=sample_normal_data,
            features=["value1", "value2"],
            method="isolation_forest",
        )

        assert "method" in result
        assert result["method"] == "isolation_forest"
        assert "anomalies" in result
        assert "anomaly_count" in result
        assert "total_records" in result
        assert result["total_records"] == len(sample_normal_data)

    def test_statistical_detection(self, sample_normal_data):
        """Test statistical Z-score anomaly detection."""
        detector = AnomalyDetector()
        result = detector.detect(
            data=sample_normal_data,
            features=["value1", "value2"],
            method="statistical",
        )

        assert "method" in result
        assert result["method"] == "statistical"
        assert "anomalies" in result
        assert "anomaly_count" in result

    def test_anomaly_structure(self, sample_normal_data):
        """Test anomaly result structure."""
        detector = AnomalyDetector(contamination=0.05)
        result = detector.detect(
            data=sample_normal_data,
            features=["value1"],
            method="isolation_forest",
        )

        if result.get("anomalies"):
            anomaly = result["anomalies"][0]
            assert "index" in anomaly
            assert "score" in anomaly
            assert "features" in anomaly


class TestEnhancedClustering:
    """Test EnhancedClustering functionality."""

    @pytest.fixture
    def sample_clustering_data(self):
        """Generate sample data for clustering."""
        data = []
        # Cluster 1
        for i in range(30):
            data.append({
                "id": i,
                "feature1": np.random.normal(10, 2),
                "feature2": np.random.normal(10, 2),
            })
        # Cluster 2
        for i in range(30, 60):
            data.append({
                "id": i,
                "feature1": np.random.normal(50, 2),
                "feature2": np.random.normal(50, 2),
            })
        # Cluster 3
        for i in range(60, 90):
            data.append({
                "id": i,
                "feature1": np.random.normal(90, 2),
                "feature2": np.random.normal(90, 2),
            })
        return data

    def test_clustering_no_features(self):
        """Test with no valid features."""
        clusterer = EnhancedClustering()
        result = clusterer.cluster(
            data=[{"id": 1, "name": "test"}],
            features=["nonexistent"],
        )

        assert "error" in result

    def test_kmeans_clustering(self, sample_clustering_data):
        """Test K-Means clustering."""
        clusterer = EnhancedClustering()
        result = clusterer.cluster(
            data=sample_clustering_data,
            features=["feature1", "feature2"],
            algorithm="kmeans",
            n_clusters=3,
        )

        assert "algorithm" in result
        assert result["algorithm"] == "kmeans"
        assert "n_clusters" in result
        assert result["n_clusters"] == 3
        assert "clusters" in result
        assert len(result["clusters"]) == 3
        assert "total_samples" in result

    def test_dbscan_clustering(self, sample_clustering_data):
        """Test DBSCAN clustering."""
        clusterer = EnhancedClustering()
        result = clusterer.cluster(
            data=sample_clustering_data,
            features=["feature1", "feature2"],
            algorithm="dbscan",
            eps=5.0,
            min_samples=5,
        )

        assert "algorithm" in result
        assert result["algorithm"] == "dbscan"
        assert "clusters" in result
        assert "total_samples" in result

    def test_cluster_structure(self, sample_clustering_data):
        """Test cluster result structure."""
        clusterer = EnhancedClustering()
        result = clusterer.cluster(
            data=sample_clustering_data,
            features=["feature1", "feature2"],
            algorithm="kmeans",
            n_clusters=3,
        )

        cluster = result["clusters"][0]
        assert "cluster_id" in cluster
        assert "size" in cluster
        assert "percentage" in cluster

    def test_unknown_algorithm(self, sample_clustering_data):
        """Test with unknown algorithm."""
        clusterer = EnhancedClustering()
        result = clusterer.cluster(
            data=sample_clustering_data,
            features=["feature1", "feature2"],
            algorithm="unknown_algorithm",
        )

        assert "error" in result
