"""
Metric Service

Business logic for metrics comparison and analysis.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import statistics

from .mlflow_client import get_mlflow_client
from .run import get_run_service

logger = logging.getLogger(__name__)


class MetricService:
    """
    Service for metrics analysis and comparison
    """

    def __init__(self):
        self._mlflow = get_mlflow_client()
        self._run_service = get_run_service()

    async def compare_metrics(
        self,
        run_ids: List[str],
        metric_keys: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Compare metrics across multiple runs

        Args:
            run_ids: List of run IDs
            metric_keys: Optional list of specific metrics to compare

        Returns:
            Comparison data with statistics
        """
        runs = []
        all_metrics = {}

        for run_id in run_ids:
            run = self._mlflow.get_run(run_id)
            runs.append(run)

            metrics = run.get("metrics", {})
            for key, value in metrics.items():
                if metric_keys and key not in metric_keys:
                    continue

                if key not in all_metrics:
                    all_metrics[key] = []
                all_metrics[key].append({
                    "run_id": run_id,
                    "run_name": run.get("run_name", run_id[:8]),
                    "value": value,
                })

        # Calculate statistics for each metric
        metric_stats = {}
        for key, values in all_metrics.items():
            numeric_values = [v["value"] for v in values]
            metric_stats[key] = {
                "values": values,
                "min": min(numeric_values),
                "max": max(numeric_values),
                "mean": statistics.mean(numeric_values),
                "median": statistics.median(numeric_values),
                "stdev": statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0,
            }

        return {
            "runs": runs,
            "metric_keys": sorted(all_metrics.keys()),
            "metric_stats": metric_stats,
        }

    async def get_metric_history(
        self,
        run_id: str,
        metric_key: str,
    ) -> List[Dict[str, Any]]:
        """
        Get metric history for a run

        Args:
            run_id: Run ID
            metric_key: Metric key

        Returns:
            List of metric values with timestamps and steps
        """
        return self._mlflow.get_metric_history(run_id, metric_key)

    async def get_experiment_metric_summary(
        self,
        experiment_id: str,
        metric_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get metric summary for an experiment

        Args:
            experiment_id: Experiment ID
            metric_key: Specific metric key (uses first available if None)

        Returns:
            Metric summary with best, worst runs and statistics
        """
        runs = self._mlflow.list_runs(experiment_id, max_results=1000)

        if not runs:
            return {"error": "No runs found for experiment"}

        # Determine metric key
        if metric_key is None:
            # Use first available metric from any run
            for run in runs:
                metrics = run.get("metrics", {})
                if metrics:
                    metric_key = list(metrics.keys())[0]
                    break

        if not metric_key:
            return {"error": "No metrics found for experiment"}

        # Collect values
        values = []
        for run in runs:
            value = run.get("metrics", {}).get(metric_key)
            if value is not None:
                values.append({
                    "run_id": run["run_id"],
                    "run_name": run.get("run_name", run["run_id"][:8]),
                    "value": value,
                    "start_time": run.get("start_time"),
                })

        if not values:
            return {"error": f"No values found for metric: {metric_key}"}

        # Sort by value
        sorted_values = sorted(values, key=lambda x: x["value"], reverse=True)

        numeric_values = [v["value"] for v in values]

        return {
            "metric_key": metric_key,
            "count": len(values),
            "best": sorted_values[0],
            "worst": sorted_values[-1],
            "mean": statistics.mean(numeric_values),
            "median": statistics.median(numeric_values),
            "stdev": statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0,
            "min": min(numeric_values),
            "max": max(numeric_values),
            "all_values": sorted_values,
        }

    async def get_parallel_coordinates_data(
        self,
        experiment_id: str,
        run_ids: Optional[List[str]] = None,
        max_runs: int = 50,
    ) -> Dict[str, Any]:
        """
        Get data for parallel coordinates visualization

        Args:
            experiment_id: Experiment ID
            run_ids: Optional list of specific run IDs
            max_runs: Maximum number of runs to include

        Returns:
            Data structured for parallel coordinates plot
        """
        if run_ids is None:
            runs = self._mlflow.list_runs(
                experiment_id=experiment_id,
                max_results=max_runs,
            )
            run_ids = [r["run_id"] for r in runs]

        # Collect all params and metrics
        all_params = set()
        all_metrics = set()
        run_data = []

        for run_id in run_ids:
            run = self._mlflow.get_run(run_id)

            params = run.get("params", {})
            metrics = run.get("metrics", {})

            # Filter to numeric params only
            numeric_params = {}
            for k, v in params.items():
                try:
                    numeric_params[k] = float(v)
                    all_params.add(k)
                except (ValueError, TypeError):
                    pass

            all_metrics.update(metrics.keys())

            run_data.append({
                "run_id": run_id,
                "run_name": run.get("run_name", run_id[:8]),
                "params": numeric_params,
                "metrics": metrics,
            })

        return {
            "dimensions": {
                "params": sorted(list(all_params)),
                "metrics": sorted(list(all_metrics)),
            },
            "runs": run_data,
        }

    async def get_metric_correlation(
        self,
        experiment_id: str,
        metric_key: str,
    ) -> Dict[str, Any]:
        """
        Analyze correlation between a metric and parameters

        Args:
            experiment_id: Experiment ID
            metric_key: Target metric

        Returns:
            Correlation data with most influential params
        """
        runs = self._mlflow.list_runs(experiment_id, max_results=1000)

        # Collect param-value pairs
        param_values = {}
        metric_values = []

        for run in runs:
            metric = run.get("metrics", {}).get(metric_key)
            if metric is None:
                continue

            metric_values.append(metric)

            params = run.get("params", {})
            for key, value in params.items():
                try:
                    num_value = float(value)
                    if key not in param_values:
                        param_values[key] = []
                    param_values[key].append(num_value)
                except (ValueError, TypeError):
                    pass

        # Calculate correlations
        correlations = []
        for param, values in param_values.items():
            if len(values) == len(metric_values):
                try:
                    corr = self._calculate_correlation(values, metric_values)
                    if not (abs(corr) >= 0 and abs(corr) <= 1):  # Check for NaN
                        continue
                    correlations.append({
                        "param": param,
                        "correlation": corr,
                        "abs_correlation": abs(corr),
                    })
                except Exception:
                    pass

        # Sort by absolute correlation
        correlations.sort(key=lambda x: x["abs_correlation"], reverse=True)

        return {
            "metric_key": metric_key,
            "correlations": correlations[:20],  # Top 20
        }

    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient"""
        n = len(x)
        if n < 2:
            return 0

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))

        sum_xx = sum((xi - mean_x) ** 2 for xi in x)
        sum_yy = sum((yi - mean_y) ** 2 for yi in y)

        denominator = (sum_xx * sum_yy) ** 0.5

        if denominator == 0:
            return 0

        return numerator / denominator

    async def get_metric_percentiles(
        self,
        experiment_id: str,
        metric_key: str,
        percentiles: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        Get percentile distribution for a metric

        Args:
            experiment_id: Experiment ID
            metric_key: Metric key
            percentiles: List of percentiles to calculate (default: [25, 50, 75, 90, 95, 99])

        Returns:
            Percentile values
        """
        if percentiles is None:
            percentiles = [25, 50, 75, 90, 95, 99]

        runs = self._mlflow.list_runs(experiment_id, max_results=1000)

        values = []
        for run in runs:
            value = run.get("metrics", {}).get(metric_key)
            if value is not None:
                values.append(value)

        if not values:
            return {"error": f"No values found for metric: {metric_key}"}

        values.sort()

        result = {
            "metric_key": metric_key,
            "count": len(values),
            "min": values[0],
            "max": values[-1],
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0,
        }

        for p in percentiles:
            index = int(len(values) * p / 100)
            index = min(index, len(values) - 1)
            result[f"p{p}"] = values[index]

        return result


# Singleton instance
_metric_service: Optional[MetricService] = None


def get_metric_service() -> MetricService:
    """Get or create metric service singleton"""
    global _metric_service
    if _metric_service is None:
        _metric_service = MetricService()
    return _metric_service
