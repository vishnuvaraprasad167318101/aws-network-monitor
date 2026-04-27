"""
Traffic Report Generator
Generates HTML report with charts summarizing network performance,
traffic patterns, and alerts.
"""

import os
import sqlite3
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime
from jinja2 import Template
from dotenv import load_dotenv

load_dotenv()


REPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AWS Network Performance Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; color: #333; }
        h1 { color: #232f3e; border-bottom: 3px solid #ff9900; padding-bottom: 10px; }
        h2 { color: #232f3e; margin-top: 30px; }
        .card { background: white; border-radius: 8px; padding: 20px; margin: 15px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; }
        .metric-box { background: #232f3e; color: white; padding: 20px; border-radius: 8px; text-align: center; }
        .metric-box .value { font-size: 2em; font-weight: bold; color: #ff9900; }
        .metric-box .label { font-size: 0.9em; margin-top: 5px; }
        table { width: 100%; border-collapse: collapse; }
        th { background: #232f3e; color: white; padding: 10px; text-align: left; }
        td { padding: 8px 10px; border-bottom: 1px solid #eee; }
        tr:hover { background: #f9f9f9; }
        .alert-critical { color: #d32f2f; font-weight: bold; }
        .alert-high { color: #f57c00; font-weight: bold; }
        .alert-medium { color: #f9a825; }
        .badge { padding: 3px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold; }
        .badge-critical { background: #ffebee; color: #d32f2f; }
        .badge-high { background: #fff3e0; color: #f57c00; }
        .badge-medium { background: #fffde7; color: #f9a825; }
        img { max-width: 100%; border-radius: 8px; }
        .footer { text-align: center; color: #888; margin-top: 40px; font-size: 0.85em; }
    </style>
</head>
<body>
    <h1>AWS Network Performance Report</h1>
    <p>Generated: <strong>{{ generated_at }}</strong> | Region: <strong>{{ region }}</strong></p>

    <h2>Traffic Summary</h2>
    <div class="metric-grid">
        <div class="metric-box">
            <div class="value">{{ summary.total_flows }}</div>
            <div class="label">Total Flows</div>
        </div>
        <div class="metric-box">
            <div class="value">{{ summary.total_bytes_mb }} MB</div>
            <div class="label">Total Traffic</div>
        </div>
        <div class="metric-box">
            <div class="value">{{ summary.rejection_rate_pct }}%</div>
            <div class="label">Rejection Rate</div>
        </div>
        <div class="metric-box">
            <div class="value">{{ summary.accepted_flows }}</div>
            <div class="label">Accepted Flows</div>
        </div>
        <div class="metric-box">
            <div class="value">{{ summary.rejected_flows }}</div>
            <div class="label">Rejected Flows</div>
        </div>
        <div class="metric-box">
            <div class="value">{{ alert_count }}</div>
            <div class="label">Active Alerts</div>
        </div>
    </div>

    {% if chart_path %}
    <div class="card">
        <h2>Traffic Charts</h2>
        <img src="{{ chart_path }}" alt="Network Traffic Charts">
    </div>
    {% endif %}

    <div class="card">
        <h2>Active Alerts</h2>
        {% if alerts %}
        <table>
            <tr><th>Severity</th><th>Type</th><th>Message</th><th>Time</th></tr>
            {% for alert in alerts %}
            <tr>
                <td><span class="badge badge-{{ alert.severity|lower }}">{{ alert.severity }}</span></td>
                <td>{{ alert.type }}</td>
                <td>{{ alert.message }}</td>
                <td>{{ alert.created_at }}</td>
            </tr>
            {% endfor %}
        </table>
        {% else %}
        <p>No active alerts.</p>
        {% endif %}
    </div>

    <div class="card">
        <h2>Latency by Connection</h2>
        <table>
            <tr><th>Source</th><th>Destination</th><th>Avg Latency (ms)</th><th>Max Latency (ms)</th><th>Packet Loss %</th></tr>
            {% for conn in latency_data %}
            <tr>
                <td>{{ conn.src_subnet }}</td>
                <td>{{ conn.dst_endpoint }}</td>
                <td>{{ conn.avg_latency }}</td>
                <td>{{ conn.max_latency }}</td>
                <td>{{ conn.avg_loss }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <div class="card">
        <h2>Top Bandwidth Consumers</h2>
        <table>
            <tr><th>Instance ID</th><th>Avg In (Mbps)</th><th>Avg Out (Mbps)</th><th>Max In (Mbps)</th><th>Max Out (Mbps)</th></tr>
            {% for inst in bandwidth_data %}
            <tr>
                <td>{{ inst.instance_id }}</td>
                <td>{{ inst.avg_in }}</td>
                <td>{{ inst.avg_out }}</td>
                <td>{{ inst.max_in }}</td>
                <td>{{ inst.max_out }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <div class="footer">
        AWS Network Performance Monitor | Auto-generated report
    </div>
</body>
</html>
"""


class TrafficReportGenerator:
    def __init__(self, db_path: str = "network_monitor.db", output_dir: str = "reports"):
        self.db_path = db_path
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def _load_data(self) -> dict:
        """Load all data from SQLite for the report."""
        conn = sqlite3.connect(self.db_path)

        summary_df = pd.read_sql("SELECT * FROM traffic_summary ORDER BY recorded_at DESC LIMIT 1", conn)
        alerts_df = pd.read_sql("SELECT * FROM alerts WHERE resolved = 0 ORDER BY created_at DESC LIMIT 20", conn)
        latency_df = pd.read_sql("""
            SELECT src_subnet, dst_endpoint,
                   ROUND(AVG(latency_ms), 2) as avg_latency,
                   ROUND(MAX(latency_ms), 2) as max_latency,
                   ROUND(AVG(packet_loss_pct), 2) as avg_loss
            FROM latency_metrics
            GROUP BY src_subnet, dst_endpoint
            ORDER BY avg_latency DESC
        """, conn)
        bandwidth_df = pd.read_sql("""
            SELECT instance_id,
                   ROUND(AVG(CASE WHEN metric_name='NetworkIn' THEN average_mbps END), 2) as avg_in,
                   ROUND(AVG(CASE WHEN metric_name='NetworkOut' THEN average_mbps END), 2) as avg_out,
                   ROUND(MAX(CASE WHEN metric_name='NetworkIn' THEN max_mbps END), 2) as max_in,
                   ROUND(MAX(CASE WHEN metric_name='NetworkOut' THEN max_mbps END), 2) as max_out
            FROM bandwidth_metrics
            GROUP BY instance_id
            ORDER BY avg_out DESC
        """, conn)
        flow_df = pd.read_sql("SELECT * FROM flow_logs ORDER BY start_time DESC LIMIT 500", conn)
        conn.close()

        return {
            "summary": summary_df,
            "alerts": alerts_df,
            "latency": latency_df,
            "bandwidth": bandwidth_df,
            "flows": flow_df
        }

    def _generate_charts(self, data: dict) -> str:
        """Generate traffic analysis charts and save as PNG."""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle("AWS Network Performance Dashboard", fontsize=14, fontweight="bold", color="#232f3e")

        # Protocol breakdown
        if not data["flows"].empty:
            proto_counts = data["flows"].groupby("protocol")["bytes"].sum()
            axes[0, 0].pie(proto_counts.values, labels=proto_counts.index,
                           autopct="%1.1f%%", colors=["#ff9900", "#232f3e", "#666", "#999"])
            axes[0, 0].set_title("Traffic by Protocol")

        # Accepted vs Rejected
        if not data["flows"].empty:
            action_counts = data["flows"]["action"].value_counts()
            colors = ["#4caf50" if x == "ACCEPT" else "#f44336" for x in action_counts.index]
            axes[0, 1].bar(action_counts.index, action_counts.values, color=colors)
            axes[0, 1].set_title("Accepted vs Rejected Flows")
            axes[0, 1].set_ylabel("Flow Count")

        # Latency by connection
        if not data["latency"].empty:
            df = data["latency"].head(5)
            labels = [f"{r['src_subnet']}\n->{r['dst_endpoint'][:12]}" for _, r in df.iterrows()]
            axes[1, 0].barh(labels, df["avg_latency"], color="#ff9900")
            axes[1, 0].set_title("Avg Latency by Connection (ms)")
            axes[1, 0].set_xlabel("Latency (ms)")

        # Bandwidth by instance
        if not data["bandwidth"].empty:
            df = data["bandwidth"].head(5).fillna(0)
            x = range(len(df))
            axes[1, 1].bar([i - 0.2 for i in x], df["avg_in"], width=0.4,
                           label="Avg In", color="#232f3e")
            axes[1, 1].bar([i + 0.2 for i in x], df["avg_out"], width=0.4,
                           label="Avg Out", color="#ff9900")
            axes[1, 1].set_xticks(list(x))
            axes[1, 1].set_xticklabels(
                [inst[-12:] for inst in df["instance_id"]], rotation=15, fontsize=8
            )
            axes[1, 1].set_title("Bandwidth per Instance (Mbps)")
            axes[1, 1].legend()

        plt.tight_layout()
        chart_path = os.path.join(self.output_dir, "network_charts.png")
        plt.savefig(chart_path, dpi=120, bbox_inches="tight")
        plt.close()
        print(f"[TrafficReport] Charts saved to {chart_path}")
        return chart_path

    def generate(self) -> str:
        """Generate the full HTML report."""
        print("[TrafficReport] Generating report...")
        data = self._load_data()
        chart_path = self._generate_charts(data)

        summary = {}
        if not data["summary"].empty:
            row = data["summary"].iloc[0]
            summary = {
                "total_flows": int.from_bytes(row.get("total_flows", 0), "little") if isinstance(row.get("total_flows"), bytes) else int(row.get("total_flows", 0)),
                "total_bytes_mb": round(float(row.get("total_bytes_mb", 0)), 2),
                "total_packets": int.from_bytes(row.get("total_packets", 0), "little") if isinstance(row.get("total_packets"), bytes) else int(row.get("total_packets", 0)),
                "accepted_flows": int.from_bytes(row.get("accepted_flows", 0), "little") if isinstance(row.get("accepted_flows"), bytes) else int(row.get("accepted_flows", 0)),
                "rejected_flows": int.from_bytes(row.get("rejected_flows", 0), "little") if isinstance(row.get("rejected_flows"), bytes) else int(row.get("rejected_flows", 0)),
                "rejection_rate_pct": round(float(row.get("rejection_rate_pct", 0)), 2)
            }

        alerts = data["alerts"].to_dict("records") if not data["alerts"].empty else []
        latency_data = data["latency"].to_dict("records") if not data["latency"].empty else []
        bandwidth_data = data["bandwidth"].fillna(0).to_dict("records") if not data["bandwidth"].empty else []

        template = Template(REPORT_TEMPLATE)
        html = template.render(
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            region=os.getenv("AWS_REGION", "us-west-2"),
            summary=summary,
            alert_count=len(alerts),
            alerts=alerts,
            latency_data=latency_data,
            bandwidth_data=bandwidth_data,
            chart_path=os.path.basename(chart_path)
        )

        report_path = os.path.join(self.output_dir, "network_report.html")
        with open(report_path, "w") as f:
            f.write(html)

        print(f"[TrafficReport] Report saved to {report_path}")
        return report_path


if __name__ == "__main__":
    generator = TrafficReportGenerator()
    report = generator.generate()
    print(f"\nReport generated: {report}")
    print("Open reports/network_report.html in your browser to view.")
