"""
Latency Tracker
Simulates and tracks network latency between subnets and to external endpoints.
Uses ICMP-style ping simulation or real CloudWatch metrics.
"""

import os
import random
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


class LatencyTracker:
    def __init__(self, db_path: str = "network_monitor.db"):
        self.db_path = db_path
        self.threshold_ms = float(os.getenv("LATENCY_THRESHOLD_MS", 100))
        self.use_sample = os.getenv("USE_SAMPLE_DATA", "true").lower() == "true"

    def _generate_sample_latency(self, hours: int = 1) -> list:
        """Generate sample latency data between subnets and external endpoints."""
        endpoints = [
            {"src": "10.0.1.0/24", "dst": "10.0.2.0/24", "type": "subnet-to-subnet", "base_ms": 2},
            {"src": "10.0.1.0/24", "dst": "10.0.3.0/24", "type": "subnet-to-subnet", "base_ms": 3},
            {"src": "10.0.2.0/24", "dst": "10.0.3.0/24", "type": "subnet-to-subnet", "base_ms": 2},
            {"src": "10.0.1.0/24", "dst": "8.8.8.8",     "type": "internet",          "base_ms": 15},
            {"src": "10.0.1.0/24", "dst": "172.16.0.0/16","type": "vpc-peering",       "base_ms": 5},
        ]

        records = []
        now = datetime.utcnow()
        for i in range(hours * 12):
            ts = now - timedelta(minutes=i * 5)
            for ep in endpoints:
                spike = random.random() < 0.08
                multiplier = random.uniform(5, 20) if spike else random.uniform(0.8, 1.3)
                latency = round(ep["base_ms"] * multiplier, 2)
                packet_loss = round(random.uniform(0, 2) if not spike else random.uniform(5, 15), 2)
                records.append({
                    "src_subnet": ep["src"],
                    "dst_endpoint": ep["dst"],
                    "connection_type": ep["type"],
                    "latency_ms": latency,
                    "packet_loss_pct": packet_loss,
                    "timestamp": ts.isoformat()
                })
        return records

    def collect_latency(self, hours: int = 1) -> pd.DataFrame:
        """Collect latency data."""
        if self.use_sample:
            print("[LatencyTracker] Using sample latency data.")
            records = self._generate_sample_latency(hours)
        else:
            print("[LatencyTracker] Real AWS latency monitoring not configured.")
            records = self._generate_sample_latency(hours)

        df = pd.DataFrame(records)
        self._save_to_db(df)
        return df

    def _save_to_db(self, df: pd.DataFrame):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for _, row in df.iterrows():
            cursor.execute("""
                INSERT INTO latency_metrics
                (src_subnet, dst_endpoint, connection_type, latency_ms, packet_loss_pct, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                row["src_subnet"], row["dst_endpoint"], row["connection_type"],
                row["latency_ms"], row["packet_loss_pct"], row["timestamp"]
            ))
        conn.commit()
        conn.close()

    def detect_high_latency(self, df: pd.DataFrame) -> list:
        """Detect connections exceeding latency threshold."""
        issues = []
        high_latency = df[df["latency_ms"] > self.threshold_ms]
        for _, row in high_latency.iterrows():
            issues.append({
                "type": "HIGH_LATENCY",
                "src": row["src_subnet"],
                "dst": row["dst_endpoint"],
                "latency_ms": row["latency_ms"],
                "threshold_ms": self.threshold_ms,
                "timestamp": row["timestamp"],
                "severity": "CRITICAL" if row["latency_ms"] > self.threshold_ms * 3 else "HIGH"
            })

        high_loss = df[df["packet_loss_pct"] > float(os.getenv("PACKET_LOSS_THRESHOLD_PCT", 5))]
        for _, row in high_loss.iterrows():
            issues.append({
                "type": "PACKET_LOSS",
                "src": row["src_subnet"],
                "dst": row["dst_endpoint"],
                "packet_loss_pct": row["packet_loss_pct"],
                "timestamp": row["timestamp"],
                "severity": "HIGH"
            })
        return issues

    def get_summary(self, df: pd.DataFrame) -> dict:
        """Summarize latency stats per connection pair."""
        summary = {}
        for (src, dst), group in df.groupby(["src_subnet", "dst_endpoint"]):
            key = f"{src} -> {dst}"
            summary[key] = {
                "avg_latency_ms": round(group["latency_ms"].mean(), 2),
                "max_latency_ms": round(group["latency_ms"].max(), 2),
                "min_latency_ms": round(group["latency_ms"].min(), 2),
                "avg_packet_loss_pct": round(group["packet_loss_pct"].mean(), 2),
                "connection_type": group["connection_type"].iloc[0]
            }
        return summary


if __name__ == "__main__":
    tracker = LatencyTracker()
    df = tracker.collect_latency(hours=1)
    summary = tracker.get_summary(df)
    issues = tracker.detect_high_latency(df)

    print("\n=== Latency Summary ===")
    for conn, stats in summary.items():
        print(f"  {conn}: avg={stats['avg_latency_ms']}ms | max={stats['max_latency_ms']}ms | loss={stats['avg_packet_loss_pct']}%")

    if issues:
        print(f"\n=== {len(issues)} Latency Issues Detected ===")
        for issue in issues[:5]:
            print(f"  [{issue['severity']}] {issue['type']}: {issue.get('latency_ms', issue.get('packet_loss_pct'))} - {issue['src']} -> {issue['dst']}")
