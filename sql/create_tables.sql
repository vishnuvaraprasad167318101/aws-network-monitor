-- Network Monitor Database Schema

CREATE TABLE IF NOT EXISTS flow_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interface_id TEXT,
    src_ip TEXT,
    dst_ip TEXT,
    src_port INTEGER,
    dst_port INTEGER,
    protocol TEXT,
    packets INTEGER,
    bytes INTEGER,
    action TEXT,
    start_time TEXT,
    end_time TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS traffic_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at TEXT,
    total_flows INTEGER,
    total_bytes_mb REAL,
    total_packets INTEGER,
    accepted_flows INTEGER,
    rejected_flows INTEGER,
    rejection_rate_pct REAL
);

CREATE TABLE IF NOT EXISTS bandwidth_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_id TEXT,
    metric_name TEXT,
    timestamp TEXT,
    average_mbps REAL,
    max_mbps REAL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS latency_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    src_subnet TEXT,
    dst_endpoint TEXT,
    connection_type TEXT,
    latency_ms REAL,
    packet_loss_pct REAL,
    timestamp TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT,
    severity TEXT,
    source TEXT,
    message TEXT,
    details TEXT,
    created_at TEXT,
    resolved INTEGER DEFAULT 0
);
