"""
AWS Network Performance Monitor
Main entry point — runs all monitoring components and generates report.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.vpc_flow_analyzer import VPCFlowAnalyzer
from src.bandwidth_monitor import BandwidthMonitor
from src.latency_tracker import LatencyTracker
from src.alert_manager import AlertManager
from src.traffic_report import TrafficReportGenerator
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "network_monitor.db"


def run_monitoring():
    print("=" * 60)
    print("  AWS Network Performance Monitor")
    print("=" * 60)

    # Step 1 — VPC Flow Log Analysis
    print("\n[1/5] Analyzing VPC Flow Logs...")
    analyzer = VPCFlowAnalyzer(db_path=DB_PATH)
    flow_df = analyzer.load_flow_logs("data/sample_flow_logs.csv")
    flow_results = analyzer.analyze_traffic(flow_df)
    flow_bottlenecks = analyzer.get_bottlenecks(flow_df)

    print(f"      Total flows: {flow_results['summary']['total_flows']}")
    print(f"      Rejection rate: {flow_results['summary']['rejection_rate_pct']}%")
    print(f"      Bottlenecks found: {len(flow_bottlenecks)}")

    # Step 2 — Bandwidth Monitoring
    print("\n[2/5] Collecting Bandwidth Metrics...")
    bandwidth = BandwidthMonitor(db_path=DB_PATH)
    bw_df = bandwidth.collect_metrics(hours=1)
    bw_summary = bandwidth.get_summary(bw_df)
    bw_anomalies = bandwidth.detect_anomalies(bw_df)

    print(f"      Instances monitored: {len(bw_summary)}")
    print(f"      Bandwidth anomalies: {len(bw_anomalies)}")

    # Step 3 — Latency Tracking
    print("\n[3/5] Tracking Network Latency...")
    latency = LatencyTracker(db_path=DB_PATH)
    lat_df = latency.collect_latency(hours=1)
    lat_summary = latency.get_summary(lat_df)
    lat_issues = latency.detect_high_latency(lat_df)

    print(f"      Connections monitored: {len(lat_summary)}")
    print(f"      Latency issues: {len(lat_issues)}")

    # Step 4 — Alert Processing
    print("\n[4/5] Processing Alerts...")
    alert_mgr = AlertManager(db_path=DB_PATH)

    all_alerts = []
    all_alerts.extend(alert_mgr.process_alerts(flow_bottlenecks, "VPCFlowAnalyzer"))
    all_alerts.extend(alert_mgr.process_alerts(bw_anomalies, "BandwidthMonitor"))
    all_alerts.extend(alert_mgr.process_alerts(lat_issues, "LatencyTracker"))

    alert_summary = alert_mgr.get_alert_summary()
    print(f"      Total alerts generated: {len(all_alerts)}")
    for sev, count in alert_summary.items():
        print(f"      - {sev}: {count}")

    # Step 5 — Generate Report
    print("\n[5/5] Generating HTML Report...")
    reporter = TrafficReportGenerator(db_path=DB_PATH, output_dir="reports")
    report_path = reporter.generate()

    # Final Summary
    print("\n" + "=" * 60)
    print("  MONITORING COMPLETE")
    print("=" * 60)
    print(f"\n  Report:   {report_path}")
    print(f"  Database: {DB_PATH}")
    print(f"\n  Traffic Summary:")
    for k, v in flow_results["summary"].items():
        print(f"    {k}: {v}")

    if all_alerts:
        print(f"\n  Active Alerts ({len(all_alerts)} total):")
        alert_mgr.print_alert_report(all_alerts[:5])

    print("\n  Open reports/network_report.html in your browser.")
    print("=" * 60)


if __name__ == "__main__":
    run_monitoring()
