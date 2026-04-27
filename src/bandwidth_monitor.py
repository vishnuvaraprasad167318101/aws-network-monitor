"""
Bandwidth Monitor
Tracks network bandwidth usage per EC2 instance using CloudWatch metrics
or sample data when USE_SAMPLE_DATA=true.
"""

import os
import random
import sqlite3
import boto3
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


class BandwidthMonitor:
    def __init__(self, db_path: str = "network_monitor.db"):
        self.db_path = db_path
        self.region = os.getenv("AWS_REGION", "us-west-2")
        self.use_sample = os.getenv("USE_SAMPLE_DATA", "true").lower() == "true"
        self.threshold_mbps = float(os.getenv("BANDWIDTH_THRESHOLD_MBPS", 100))

    def _get_cloudwatch_metrics(self, instance_id: str, hours: int = 1) -> list:
        """Fetch network metrics from CloudWatch for a real EC2 instance."""
        client = boto3.client("cloudwatch", region_name=self.region)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        metrics = []
        for metric_name in ["NetworkIn", "NetworkOut"]:
            response = client.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName=metric_name,
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=["Average", "Maximum"]
            )
            for point in response["Datapoints"]:
                metrics.append({
                    "instance_id": instance_id,
                    "metric": metric_name,
                    "timestamp": point["Timestamp"].isoformat(),
                    "average_bytes": point["Average"],
                    "max_bytes": point["Maximum"],
                    "average_mbps": round(point["Average"] / (1024 * 1024), 3),
                    "max_mbps": round(point["Maximum"] / (1024 * 1024), 3)
                })
        return metrics

    def _generate_sample_metrics(self, hours: int = 1) -> list:
        """Generate realistic sample bandwidth metrics for demo."""
        instances = [
            {"id": "i-0abc12345def67890", "name": "web-server-01", "baseline_mbps": 45},
            {"id": "i-0def67890abc12345", "name": "app-server-01", "baseline_mbps": 80},
            {"id": "i-0ghi11111jkl22222", "name": "db-server-01",  "baseline_mbps": 30},
            {"id": "i-0jkl22222mno33333", "name": "cache-server-01", "baseline_mbps": 120},
        ]

        metrics = []
        now = datetime.utcnow()
        for i in range(hours * 12):
            ts = now - timedelta(minutes=i * 5)
            for inst in instances:
                spike = random.random() < 0.1
                multiplier = random.uniform(1.5, 3.0) if spike else random.uniform(0.8, 1.2)
                avg_mbps = round(inst["baseline_mbps"] * multiplier, 2)
                max_mbps = round(avg_mbps * random.uniform(1.1, 1.5), 2)

                for direction in ["NetworkIn", "NetworkOut"]:
                    factor = 0.6 if direction == "NetworkIn" else 1.0
                    metrics.append({
                        "instance_id": inst["id"],
                        "instance_name": inst["name"],
                        "metric": direction,
                        "timestamp": ts.isoformat(),
                        "average_mbps": round(avg_mbps * factor, 2),
                        "max_mbps": round(max_mbps * factor, 2)
                    })
        return metrics

    def collect_metrics(self, instance_ids: list = None, hours: int = 1) -> pd.DataFrame:
        """Collect bandwidth metrics from CloudWatch or sample data."""
        if self.use_sample:
            print("[BandwidthMonitor] Using sample data mode.")
            metrics = self._generate_sample_metrics(hours)
        else:
            print(f"[BandwidthMonitor] Fetching CloudWatch metrics for {instance_ids}")
            metrics = []
            for inst_id in (instance_ids or []):
                metrics.extend(self._get_cloudwatch_metrics(inst_id, hours))

        df = pd.DataFrame(metrics)
        self._save_to_db(df)
        return df

    def _save_to_db(self, df: pd.DataFrame):
        """Save bandwidth metrics to SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for _, row in df.iterrows():
            cursor.execute("""
                INSERT INTO bandwidth_metrics
                (instance_id, metric_name, timestamp, average_mbps, max_mbps)
                VALUES (?, ?, ?, ?, ?)
            """, (
                row["instance_id"], row["metric"],
                row["timestamp"], row["average_mbps"], row["max_mbps"]
            ))
        conn.commit()
        conn.close()

    def detect_anomalies(self, df: pd.DataFrame) -> list:
        """Detect bandwidth anomalies exceeding threshold."""
        anomalies = []
        high_usage = df[df["max_mbps"] > self.threshold_mbps]
        for _, row in high_usage.iterrows():
            anomalies.append({
                "type": "BANDWIDTH_SPIKE",
                "instance_id": row["instance_id"],
                "metric": row["metric"],
                "max_mbps": row["max_mbps"],
                "threshold_mbps": self.threshold_mbps,
                "timestamp": row["timestamp"],
                "severity": "HIGH" if row["max_mbps"] > self.threshold_mbps * 2 else "MEDIUM"
            })
        return anomalies

    def get_summary(self, df: pd.DataFrame) -> dict:
        """Generate bandwidth usage summary per instance."""
        summary = {}
        for instance_id in df["instance_id"].unique():
            inst_df = df[df["instance_id"] == instance_id]
            summary[instance_id] = {
                "avg_in_mbps": round(inst_df[inst_df["metric"] == "NetworkIn"]["average_mbps"].mean(), 2),
                "avg_out_mbps": round(inst_df[inst_df["metric"] == "NetworkOut"]["average_mbps"].mean(), 2),
                "max_in_mbps": round(inst_df[inst_df["metric"] == "NetworkIn"]["max_mbps"].max(), 2),
                "max_out_mbps": round(inst_df[inst_df["metric"] == "NetworkOut"]["max_mbps"].max(), 2),
            }
        return summary


if __name__ == "__main__":
    monitor = BandwidthMonitor()
    df = monitor.collect_metrics(hours=1)
    summary = monitor.get_summary(df)
    anomalies = monitor.detect_anomalies(df)

    print("\n=== Bandwidth Summary per Instance ===")
    for inst, stats in summary.items():
        print(f"  {inst}: IN={stats['avg_in_mbps']} Mbps avg | OUT={stats['avg_out_mbps']} Mbps avg")

    if anomalies:
        print(f"\n=== {len(anomalies)} Bandwidth Anomalies Detected ===")
        for a in anomalies[:5]:
            print(f"  [{a['severity']}] {a['instance_id']} - {a['metric']}: {a['max_mbps']} Mbps")
