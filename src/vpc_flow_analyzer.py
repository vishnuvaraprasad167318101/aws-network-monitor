"""
VPC Flow Log Analyzer
Parses VPC flow logs and provides traffic analysis by protocol,
source/destination, port, and action (ACCEPT/REJECT).
"""

import os
import csv
import sqlite3
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

PROTOCOL_MAP = {
    "1": "ICMP",
    "6": "TCP",
    "17": "UDP",
    "58": "IPv6-ICMP"
}


class VPCFlowAnalyzer:
    def __init__(self, db_path: str = "network_monitor.db"):
        self.db_path = db_path
        self.use_sample = os.getenv("USE_SAMPLE_DATA", "true").lower() == "true"
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.executescript(open("sql/create_tables.sql").read())
        conn.commit()
        conn.close()

    def load_flow_logs(self, filepath: str = "data/sample_flow_logs.csv") -> pd.DataFrame:
        """Load VPC flow logs from CSV file (sample or exported from AWS)."""
        print(f"[VPCFlowAnalyzer] Loading flow logs from {filepath}")
        df = pd.read_csv(filepath)
        df["protocol_name"] = df["protocol"].astype(str).map(PROTOCOL_MAP).fillna("OTHER")
        df["bytes_mb"] = df["bytes"] / (1024 * 1024)
        df["start_dt"] = pd.to_datetime(df["start"], unit="s")
        df["end_dt"] = pd.to_datetime(df["end"], unit="s")
        df["duration_sec"] = df["end"] - df["start"]
        return df

    def analyze_traffic(self, df: pd.DataFrame) -> dict:
        """Analyze traffic patterns from flow log data."""
        total_bytes = df["bytes"].sum()
        total_packets = df["packets"].sum()
        total_flows = len(df)

        accepted = df[df["action"] == "ACCEPT"]
        rejected = df[df["action"] == "REJECT"]

        protocol_breakdown = (
            df.groupby("protocol_name")["bytes"]
            .sum()
            .sort_values(ascending=False)
            .to_dict()
        )

        top_talkers = (
            df.groupby("srcaddr")["bytes"]
            .sum()
            .sort_values(ascending=False)
            .head(5)
            .to_dict()
        )

        top_destinations = (
            df.groupby("dstaddr")["bytes"]
            .sum()
            .sort_values(ascending=False)
            .head(5)
            .to_dict()
        )

        top_ports = (
            df.groupby("dstport")["packets"]
            .sum()
            .sort_values(ascending=False)
            .head(5)
            .to_dict()
        )

        rejected_sources = (
            rejected.groupby("srcaddr")["packets"]
            .sum()
            .sort_values(ascending=False)
            .head(5)
            .to_dict()
        )

        results = {
            "summary": {
                "total_flows": total_flows,
                "total_bytes_mb": round(total_bytes / (1024 * 1024), 2),
                "total_packets": total_packets,
                "accepted_flows": len(accepted),
                "rejected_flows": len(rejected),
                "rejection_rate_pct": round(len(rejected) / total_flows * 100, 2) if total_flows > 0 else 0
            },
            "protocol_breakdown": protocol_breakdown,
            "top_talkers": top_talkers,
            "top_destinations": top_destinations,
            "top_ports": top_ports,
            "rejected_sources": rejected_sources
        }

        self._save_to_db(df, results)
        return results

    def _save_to_db(self, df: pd.DataFrame, results: dict):
        """Save flow log data and analysis results to SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for _, row in df.iterrows():
            cursor.execute("""
                INSERT OR IGNORE INTO flow_logs
                (interface_id, src_ip, dst_ip, src_port, dst_port,
                 protocol, packets, bytes, action, start_time, end_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["interface_id"], row["srcaddr"], row["dstaddr"],
                row["srcport"], row["dstport"], row["protocol_name"],
                row["packets"], row["bytes"], row["action"],
                row["start_dt"].isoformat(), row["end_dt"].isoformat()
            ))

        summary = results["summary"]
        cursor.execute("""
            INSERT INTO traffic_summary
            (recorded_at, total_flows, total_bytes_mb, total_packets,
             accepted_flows, rejected_flows, rejection_rate_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            summary["total_flows"], summary["total_bytes_mb"],
            summary["total_packets"], summary["accepted_flows"],
            summary["rejected_flows"], summary["rejection_rate_pct"]
        ))

        conn.commit()
        conn.close()
        print("[VPCFlowAnalyzer] Data saved to database.")

    def get_bottlenecks(self, df: pd.DataFrame) -> list:
        """Identify potential network bottlenecks."""
        bottlenecks = []
        threshold_bytes = float(os.getenv("BANDWIDTH_THRESHOLD_MBPS", 100)) * 1024 * 1024

        high_traffic = df[df["bytes"] > threshold_bytes]
        if not high_traffic.empty:
            for _, row in high_traffic.iterrows():
                bottlenecks.append({
                    "type": "HIGH_BANDWIDTH",
                    "src": row["srcaddr"],
                    "dst": row["dstaddr"],
                    "bytes_mb": round(row["bytes_mb"], 2),
                    "interface": row["interface_id"]
                })

        rejection_rate = len(df[df["action"] == "REJECT"]) / len(df) * 100
        if rejection_rate > float(os.getenv("PACKET_LOSS_THRESHOLD_PCT", 5)):
            bottlenecks.append({
                "type": "HIGH_REJECTION_RATE",
                "rejection_rate_pct": round(rejection_rate, 2),
                "message": f"Rejection rate {rejection_rate:.1f}% exceeds threshold"
            })

        return bottlenecks


if __name__ == "__main__":
    analyzer = VPCFlowAnalyzer()
    df = analyzer.load_flow_logs()
    results = analyzer.analyze_traffic(df)
    bottlenecks = analyzer.get_bottlenecks(df)

    print("\n=== VPC Flow Analysis Summary ===")
    for k, v in results["summary"].items():
        print(f"  {k}: {v}")

    print("\n=== Protocol Breakdown ===")
    for proto, bytes_val in results["protocol_breakdown"].items():
        print(f"  {proto}: {round(bytes_val / 1024, 1)} KB")

    print("\n=== Top Talkers (by bytes) ===")
    for ip, bytes_val in results["top_talkers"].items():
        print(f"  {ip}: {round(bytes_val / 1024, 1)} KB")

    if bottlenecks:
        print("\n=== Bottlenecks Detected ===")
        for b in bottlenecks:
            print(f"  {b}")
