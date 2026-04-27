"""
Alert Manager
Consolidates all network alerts from bandwidth, latency, and flow log analysis.
Logs alerts to database and prints to console (can be extended to email/SNS).
"""

import os
import sqlite3
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class AlertManager:
    def __init__(self, db_path: str = "network_monitor.db"):
        self.db_path = db_path

    def process_alerts(self, alerts: list, source: str) -> list:
        """Process and store alerts from any source."""
        if not alerts:
            print(f"[AlertManager] No alerts from {source}.")
            return []

        print(f"[AlertManager] Processing {len(alerts)} alerts from {source}.")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stored = []
        for alert in alerts:
            severity = alert.get("severity", "MEDIUM")
            alert_type = alert.get("type", "UNKNOWN")
            message = self._format_message(alert)

            cursor.execute("""
                INSERT INTO alerts
                (alert_type, severity, source, message, details, created_at, resolved)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                alert_type, severity, source, message,
                json.dumps(alert), datetime.now().isoformat(), 0
            ))
            stored.append({
                "type": alert_type,
                "severity": severity,
                "source": source,
                "message": message
            })

        conn.commit()
        conn.close()
        return stored

    def _format_message(self, alert: dict) -> str:
        """Format alert into a human-readable message."""
        atype = alert.get("type", "")
        if atype == "BANDWIDTH_SPIKE":
            return (f"Bandwidth spike on {alert.get('instance_id')} "
                    f"[{alert.get('metric')}]: {alert.get('max_mbps')} Mbps "
                    f"(threshold: {alert.get('threshold_mbps')} Mbps)")
        elif atype == "HIGH_LATENCY":
            return (f"High latency detected: {alert.get('src')} -> {alert.get('dst')} "
                    f"= {alert.get('latency_ms')} ms "
                    f"(threshold: {alert.get('threshold_ms')} ms)")
        elif atype == "PACKET_LOSS":
            return (f"Packet loss detected: {alert.get('src')} -> {alert.get('dst')} "
                    f"= {alert.get('packet_loss_pct')}%")
        elif atype == "HIGH_REJECTION_RATE":
            return f"High traffic rejection rate: {alert.get('rejection_rate_pct')}%"
        elif atype == "HIGH_BANDWIDTH":
            return (f"High bandwidth flow: {alert.get('src')} -> {alert.get('dst')} "
                    f"= {alert.get('bytes_mb')} MB on {alert.get('interface')}")
        return json.dumps(alert)

    def get_active_alerts(self, severity: str = None) -> list:
        """Retrieve unresolved alerts from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if severity:
            cursor.execute("""
                SELECT alert_type, severity, source, message, created_at
                FROM alerts WHERE resolved = 0 AND severity = ?
                ORDER BY created_at DESC
            """, (severity,))
        else:
            cursor.execute("""
                SELECT alert_type, severity, source, message, created_at
                FROM alerts WHERE resolved = 0
                ORDER BY created_at DESC
            """)
        rows = cursor.fetchall()
        conn.close()
        return [
            {"type": r[0], "severity": r[1], "source": r[2],
             "message": r[3], "created_at": r[4]}
            for r in rows
        ]

    def get_alert_summary(self) -> dict:
        """Get count of active alerts by severity."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT severity, COUNT(*) FROM alerts
            WHERE resolved = 0
            GROUP BY severity
        """)
        rows = cursor.fetchall()
        conn.close()
        return {row[0]: row[1] for row in rows}

    def print_alert_report(self, alerts: list):
        """Print formatted alert report to console."""
        if not alerts:
            print("  No active alerts.")
            return
        for alert in alerts:
            icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡"}.get(alert["severity"], "⚪")
            print(f"  {icon} [{alert['severity']}] {alert['type']} | {alert['message']}")


if __name__ == "__main__":
    manager = AlertManager()
    active = manager.get_active_alerts()
    summary = manager.get_alert_summary()

    print("\n=== Active Alert Summary ===")
    for severity, count in summary.items():
        print(f"  {severity}: {count} alerts")

    print("\n=== Active Alerts ===")
    manager.print_alert_report(active[:10])
