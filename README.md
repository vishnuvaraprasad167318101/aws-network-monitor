# AWS Network Performance Monitor

A Python-based network monitoring tool that analyzes VPC flow logs, tracks bandwidth usage, monitors latency between subnets, detects anomalies, and generates an HTML performance report.

Built to demonstrate AWS networking skills including EC2, VPC, Subnets, CloudWatch, and SQL-based traffic analysis.

---

## Features

- **VPC Flow Log Analysis** — parses flow logs, identifies top talkers, protocol breakdown, rejected traffic
- **Bandwidth Monitoring** — tracks NetworkIn/NetworkOut per EC2 instance via CloudWatch
- **Latency Tracking** — monitors latency and packet loss between subnets and external endpoints
- **Anomaly Detection** — alerts on bandwidth spikes, high latency, packet loss, high rejection rates
- **SQL Traffic Analysis** — stores all data in SQLite with pre-built analysis queries
- **HTML Report** — auto-generated dashboard with charts and alert tables

---

## Project Structure

```
aws-network-monitor/
├── main.py                    # Entry point — runs full monitoring pipeline
├── requirements.txt
├── .env.example               # Configuration template
├── data/
│   └── sample_flow_logs.csv   # Sample VPC flow log data
├── src/
│   ├── vpc_flow_analyzer.py   # VPC flow log parser and traffic analyzer
│   ├── bandwidth_monitor.py   # EC2 bandwidth metrics via CloudWatch
│   ├── latency_tracker.py     # Subnet-to-subnet latency monitoring
│   ├── alert_manager.py       # Alert consolidation and storage
│   └── traffic_report.py      # HTML report and chart generation
├── sql/
│   ├── create_tables.sql      # SQLite schema
│   └── traffic_queries.sql    # Pre-built analysis queries
└── reports/                   # Generated reports (auto-created)
```

---

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/aws-network-monitor.git
cd aws-network-monitor
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env — set USE_SAMPLE_DATA=true to run without AWS credentials
```

### 4. Run the monitor
```bash
python main.py
```

### 5. View the report
Open `reports/network_report.html` in your browser.

---

## Sample Output

```
============================================================
  AWS Network Performance Monitor
============================================================

[1/5] Analyzing VPC Flow Logs...
      Total flows: 15
      Rejection rate: 26.67%
      Bottlenecks found: 1

[2/5] Collecting Bandwidth Metrics...
      Instances monitored: 4
      Bandwidth anomalies: 3

[3/5] Tracking Network Latency...
      Connections monitored: 5
      Latency issues: 2

[4/5] Processing Alerts...
      Total alerts generated: 6
      - HIGH: 4
      - MEDIUM: 2

[5/5] Generating HTML Report...
      Report saved to reports/network_report.html
```

---

## Running with Real AWS

To use real AWS data instead of sample data:

1. Set `USE_SAMPLE_DATA=false` in `.env`
2. Add your AWS credentials to `.env`
3. Enable VPC Flow Logs in your AWS Console:
   - VPC Console → Your VPC → Flow Logs → Create
   - Destination: S3 bucket or CloudWatch Logs
4. Export flow logs to CSV and place in `data/` folder
5. Update `bandwidth_monitor.py` with your EC2 instance IDs

---

## AWS Services Used

| Service | Purpose |
|---|---|
| **VPC Flow Logs** | Network traffic capture per ENI |
| **EC2** | Compute instances being monitored |
| **CloudWatch** | NetworkIn/NetworkOut metrics |
| **VPC/Subnets** | Network topology for latency tracking |
| **SQLite** | Local storage for metrics and alerts |

---

## Technologies

- Python 3.9+
- boto3 (AWS SDK)
- pandas (data analysis)
- matplotlib (charts)
- Jinja2 (HTML report templating)
- SQLite (metrics storage)

---

## Alerts Detected

| Alert Type | Trigger Condition |
|---|---|
| BANDWIDTH_SPIKE | Instance exceeds threshold Mbps |
| HIGH_LATENCY | Latency exceeds threshold ms |
| PACKET_LOSS | Packet loss exceeds threshold % |
| HIGH_REJECTION_RATE | >5% of flows rejected |
| HIGH_BANDWIDTH | Single flow exceeds threshold |

---

## License

MIT
