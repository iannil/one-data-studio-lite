# ML utilities for AI Service enhancements

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Any

import numpy as np
import pandas as pd
from openai import AsyncOpenAI
from sklearn.cluster import DBSCAN, KMeans
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


class TimeSeriesForecaster:
    """Time series forecasting using statistical methods."""

    def __init__(self):
        self.scaler = StandardScaler()

    def forecast(
        self,
        data: list[dict],
        date_column: str,
        value_column: str,
        periods: int = 7,
        method: str = "auto",
    ) -> dict[str, Any]:
        """
        Forecast future values using time series analysis.

        Args:
            data: Historical data points
            date_column: Name of date/time column
            value_column: Name of value column to predict
            periods: Number of future periods to predict
            method: Forecasting method (auto, moving_average, exponential_smooth, trend)

        Returns:
            Forecast results with predictions and confidence intervals
        """
        if len(data) < 3:
            return {
                "error": "Insufficient data for forecasting",
                "min_required": 3,
                "provided": len(data),
            }

        # Convert to DataFrame
        df = pd.DataFrame(data)
        df[date_column] = pd.to_datetime(df[date_column])
        df = df.sort_values(date_column)
        df.set_index(date_column, inplace=True)

        # Ensure numeric
        df[value_column] = pd.to_numeric(df[value_column], errors="coerce")
        df = df.dropna()

        if len(df) < 3:
            return {"error": "Insufficient valid data points after cleaning"}

        # Select method
        if method == "auto":
            method = self._select_best_method(df, value_column)

        # Generate forecast
        if method == "moving_average":
            predictions = self._moving_average_forecast(df, value_column, periods)
        elif method == "exponential_smooth":
            predictions = self._exponential_smoothing_forecast(df, value_column, periods)
        elif method == "trend":
            predictions = self._trend_forecast(df, value_column, periods)
        else:
            predictions = self._moving_average_forecast(df, value_column, periods)

        # Calculate trend direction
        recent_values = df[value_column].tail(5).tolist()
        if len(recent_values) >= 2:
            if recent_values[-1] > recent_values[0]:
                trend_direction = "increasing"
            elif recent_values[-1] < recent_values[0]:
                trend_direction = "decreasing"
            else:
                trend_direction = "stable"
        else:
            trend_direction = "unknown"

        # Detect seasonality (simple check)
        seasonality = self._detect_seasonality(df[value_column])

        # Calculate confidence bounds (simplified)
        std = df[value_column].std()
        predictions_with_bounds = []
        for i, pred in enumerate(predictions):
            predictions_with_bounds.append({
                "date": (df.index[-1] + timedelta(days=i+1)).isoformat(),
                "value": round(pred, 2),
                "lower_bound": round(pred - 1.96 * std, 2),
                "upper_bound": round(pred + 1.96 * std, 2),
                "confidence": round(max(0.5, 0.95 - i * 0.05), 2),
            })

        return {
            "predictions": predictions_with_bounds,
            "method": method,
            "trend": trend_direction,
            "seasonality": seasonality,
            "historical_mean": round(df[value_column].mean(), 2),
            "historical_std": round(df[value_column].std(), 2),
            "data_points": len(df),
        }

    def _select_best_method(self, df: pd.DataFrame, value_column: str) -> str:
        """Select the best forecasting method based on data characteristics."""
        values = df[value_column].values

        # Check for trend
        x = np.arange(len(values))
        correlation = np.corrcoef(x, values)[0, 1] if len(values) > 1 else 0

        # Check for seasonality
        diff_variance = np.var(np.diff(values))

        if abs(correlation) > 0.3:
            return "trend"
        elif diff_variance > np.var(values) * 0.5:
            return "exponential_smooth"
        else:
            return "moving_average"

    def _moving_average_forecast(
        self,
        df: pd.DataFrame,
        value_column: str,
        periods: int,
        window: int | None = None,
    ) -> list[float]:
        """Simple moving average forecast."""
        if window is None:
            window = min(7, len(df) // 2)

        forecasts = []
        last_value = df[value_column].iloc[-1]

        for i in range(periods):
            # Use the last 'window' values to predict next
            if i == 0:
                recent_values = df[value_column].tail(window).values
            else:
                # Update with our own forecasts
                recent_values = np.append(recent_values[1:], forecasts[-1])

            forecast = np.mean(recent_values)
            forecasts.append(forecast)

        return forecasts

    def _exponential_smoothing_forecast(
        self,
        df: pd.DataFrame,
        value_column: str,
        periods: int,
        alpha: float = 0.3,
    ) -> list[float]:
        """Exponential smoothing forecast."""
        values = df[value_column].values
        forecasts = []
        level = values[0]

        # Fit to historical data
        for value in values[1:]:
            level = alpha * value + (1 - alpha) * level

        # Generate future forecasts
        for _ in range(periods):
            forecasts.append(level)
            # For exponential smoothing, forecast stays at last level

        return forecasts

    def _trend_forecast(
        self,
        df: pd.DataFrame,
        value_column: str,
        periods: int,
    ) -> list[float]:
        """Linear trend forecast."""
        values = df[value_column].values
        x = np.arange(len(values))

        # Simple linear regression
        coefficients = np.polyfit(x, values, 1)
        polynomial = np.poly1d(coefficients)

        forecasts = []
        for i in range(1, periods + 1):
            forecasts.append(polynomial(len(values) + i - 1))

        return forecasts

    def _detect_seasonality(self, series: pd.Series) -> str:
        """Detect seasonality type."""
        if len(series) < 4:
            return "none"

        # Check weekly pattern (7-day cycle)
        if len(series) >= 14:
            # Simple autocorrelation check
            lag7_corr = series.autocorr(lag=7)
            if lag7_corr and abs(lag7_corr) > 0.3:
                return "weekly"

        return "none"


class AnomalyDetector:
    """Detect anomalies in data using Isolation Forest."""

    def __init__(self, contamination: float = 0.1):
        """
        Initialize the anomaly detector.

        Args:
            contamination: Expected proportion of outliers in the dataset
        """
        self.contamination = contamination
        self.scaler = StandardScaler()

    def detect(
        self,
        data: list[dict],
        features: list[str],
        method: str = "isolation_forest",
    ) -> dict[str, Any]:
        """
        Detect anomalies in the dataset.

        Args:
            data: Data points to analyze
            features: Feature columns to use for detection
            method: Detection method (isolation_forest, statistical)

        Returns:
            Anomaly detection results with flagged anomalies
        """
        df = pd.DataFrame(data)

        # Select and validate features
        valid_features = [f for f in features if f in df.columns]
        if not valid_features:
            return {"error": "No valid features found"}

        # Prepare numeric features
        X = df[valid_features].copy()

        # Convert categorical to numeric
        for col in X.select_dtypes(include=["object"]).columns:
            X[col] = pd.factorize(X[col])[0]

        # Fill missing values
        X = X.fillna(X.mean())

        if method == "isolation_forest":
            return self._isolation_forest_detection(X, df, valid_features)
        else:
            return self._statistical_detection(X, df, valid_features)

    def _isolation_forest_detection(
        self,
        X: pd.DataFrame,
        original_df: pd.DataFrame,
        features: list[str],
    ) -> dict[str, Any]:
        """Detect anomalies using Isolation Forest."""
        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Fit model
        model = IsolationForest(
            contamination=self.contamination,
            random_state=42,
            n_estimators=100,
        )
        predictions = model.fit_predict(X_scaled)

        # Get anomaly scores
        scores = model.score_samples(X_scaled)

        # Create results
        anomalies = []
        anomaly_indices = np.where(predictions == -1)[0]

        for idx in anomaly_indices:
            anomalies.append({
                "index": int(idx),
                "score": round(float(scores[idx]), 4),
                "features": {
                    f: original_df.iloc[idx][f]
                    for f in features
                    if f in original_df.columns
                },
            })

        # Calculate summary
        anomaly_count = len(anomaly_indices)
        anomaly_percentage = (anomaly_count / len(original_df)) * 100

        return {
            "method": "isolation_forest",
            "anomalies": anomalies,
            "anomaly_count": anomaly_count,
            "anomaly_percentage": round(anomaly_percentage, 2),
            "total_records": len(original_df),
            "threshold": round(model.threshold_, 4),
        }

    def _statistical_detection(
        self,
        X: pd.DataFrame,
        original_df: pd.DataFrame,
        features: list[str],
    ) -> dict[str, Any]:
        """Detect anomalies using statistical methods (Z-score)."""
        anomalies = []

        for idx, row in X.iterrows():
            max_z_score = 0
            outlier_features = []

            for col in X.columns:
                mean = X[col].mean()
                std = X[col].std()
                if std > 0:
                    z_score = abs((row[col] - mean) / std)
                    if z_score > 3:  # 3-sigma rule
                        max_z_score = max(max_z_score, z_score)
                        outlier_features.append(col)

            if max_z_score > 3:
                anomalies.append({
                    "index": int(idx),
                    "score": round(max_z_score, 4),
                    "features": {
                        f: original_df.iloc[idx][f]
                        for f in features
                        if f in original_df.columns
                    },
                    "outlier_features": outlier_features,
                })

        return {
            "method": "statistical",
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
            "anomaly_percentage": round((len(anomalies) / len(original_df)) * 100, 2),
            "total_records": len(original_df),
            "threshold": 3.0,
        }


class EnhancedClustering:
    """Enhanced clustering with multiple algorithms."""

    def __init__(self):
        self.scaler = StandardScaler()

    def cluster(
        self,
        data: list[dict],
        features: list[str],
        algorithm: str = "kmeans",
        n_clusters: int = 3,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Perform clustering analysis.

        Args:
            data: Data points to cluster
            features: Feature columns to use
            algorithm: Clustering algorithm (kmeans, dbscan)
            n_clusters: Number of clusters (for KMeans)
            **kwargs: Additional algorithm parameters

        Returns:
            Clustering results with cluster assignments and insights
        """
        df = pd.DataFrame(data)

        # Select and validate features
        valid_features = [f for f in features if f in df.columns]
        if not valid_features:
            return {"error": "No valid features found"}

        # Prepare numeric features
        X = df[valid_features].copy()

        # Convert categorical to numeric
        for col in X.select_dtypes(include=["object"]).columns:
            X[col] = pd.factorize(X[col])[0]

        # Fill missing values
        X = X.fillna(X.mean())

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Apply clustering algorithm
        if algorithm == "kmeans":
            return self._kmeans_clustering(X_scaled, df, valid_features, n_clusters, **kwargs)
        elif algorithm == "dbscan":
            return self._dbscan_clustering(X_scaled, df, valid_features, **kwargs)
        else:
            return {"error": f"Unknown algorithm: {algorithm}"}

    def _kmeans_clustering(
        self,
        X_scaled: np.ndarray,
        original_df: pd.DataFrame,
        features: list[str],
        n_clusters: int,
        **kwargs,
    ) -> dict[str, Any]:
        """K-Means clustering."""
        n_init = kwargs.get("n_init", 10)
        max_iter = kwargs.get("max_iter", 300)

        kmeans = KMeans(
            n_clusters=n_clusters,
            random_state=42,
            n_init=n_init,
            max_iter=max_iter,
        )
        labels = kmeans.fit_predict(X_scaled)

        # Calculate cluster statistics
        original_df = original_df.copy()
        original_df["cluster"] = labels

        cluster_stats = []
        for i in range(n_clusters):
            cluster_data = original_df[original_df["cluster"] == i]
            stats = {
                "cluster_id": i,
                "size": len(cluster_data),
                "percentage": round(len(cluster_data) / len(original_df) * 100, 2),
            }

            # Add feature means for numeric columns
            for feat in features:
                if feat in cluster_data.columns:
                    try:
                        if cluster_data[feat].dtype in ["int64", "float64"]:
                            stats[f"avg_{feat}"] = round(float(cluster_data[feat].mean()), 2)
                    except Exception:
                        pass

            cluster_stats.append(stats)

        return {
            "algorithm": "kmeans",
            "n_clusters": n_clusters,
            "clusters": cluster_stats,
            "total_samples": len(original_df),
            "features_used": features,
            "inertia": round(float(kmeans.inertia_), 2),
        }

    def _dbscan_clustering(
        self,
        X_scaled: np.ndarray,
        original_df: pd.DataFrame,
        features: list[str],
        **kwargs,
    ) -> dict[str, Any]:
        """DBSCAN clustering for density-based grouping."""
        eps = kwargs.get("eps", 0.5)
        min_samples = kwargs.get("min_samples", 5)

        dbscan = DBSCAN(eps=eps, min_samples=min_samples)
        labels = dbscan.fit_predict(X_scaled)

        # Count clusters (excluding noise points labeled -1)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = list(labels).count(-1)

        original_df = original_df.copy()
        original_df["cluster"] = labels

        cluster_stats = []
        for i in range(n_clusters):
            cluster_data = original_df[original_df["cluster"] == i]
            cluster_stats.append({
                "cluster_id": i,
                "size": len(cluster_data),
                "percentage": round(len(cluster_data) / len(original_df) * 100, 2),
            })

        return {
            "algorithm": "dbscan",
            "n_clusters": n_clusters,
            "clusters": cluster_stats,
            "noise_points": n_noise,
            "noise_percentage": round(n_noise / len(original_df) * 100, 2),
            "total_samples": len(original_df),
            "features_used": features,
        }
