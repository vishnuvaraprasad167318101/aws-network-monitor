-- Traffic Analysis Queries

-- Top 10 source IPs by total bytes sent
SELECT src_ip, SUM(bytes) / 1024.0 / 1024.0 AS total_mb, COUNT(*) AS flow_count
FROM flow_logs
GROUP BY src_ip
ORDER BY total_mb DESC
LIMIT 10;

-- Rejected traffic by source IP
SELECT src_ip, COUNT(*) AS rejected_attempts, SUM(packets) AS total_packets
FROM flow_logs
WHERE action = 'REJECT'
GROUP BY src_ip
ORDER BY rejected_attempts DESC
LIMIT 10;

-- Traffic breakdown by protocol
SELECT protocol, COUNT(*) AS flows,
       SUM(bytes) / 1024.0 / 1024.0 AS total_mb,
       ROUND(SUM(bytes) * 100.0 / (SELECT SUM(bytes) FROM flow_logs), 2) AS pct_of_total
FROM flow_logs
GROUP BY protocol
ORDER BY total_mb DESC;

-- Hourly traffic trend
SELECT strftime('%Y-%m-%d %H:00', start_time) AS hour,
       COUNT(*) AS flows,
       SUM(bytes) / 1024.0 / 1024.0 AS total_mb,
       SUM(CASE WHEN action = 'REJECT' THEN 1 ELSE 0 END) AS rejected
FROM flow_logs
GROUP BY hour
ORDER BY hour DESC;

-- Average latency by connection type
SELECT connection_type,
       ROUND(AVG(latency_ms), 2) AS avg_latency_ms,
       ROUND(MAX(latency_ms), 2) AS max_latency_ms,
       ROUND(AVG(packet_loss_pct), 2) AS avg_packet_loss_pct,
       COUNT(*) AS samples
FROM latency_metrics
GROUP BY connection_type
ORDER BY avg_latency_ms DESC;

-- Bandwidth usage by instance (last hour)
SELECT instance_id,
       ROUND(AVG(CASE WHEN metric_name = 'NetworkIn' THEN average_mbps END), 2) AS avg_in_mbps,
       ROUND(AVG(CASE WHEN metric_name = 'NetworkOut' THEN average_mbps END), 2) AS avg_out_mbps,
       ROUND(MAX(CASE WHEN metric_name = 'NetworkOut' THEN max_mbps END), 2) AS peak_out_mbps
FROM bandwidth_metrics
WHERE timestamp >= datetime('now', '-1 hour')
GROUP BY instance_id
ORDER BY avg_out_mbps DESC;

-- Active unresolved alerts by severity
SELECT severity, alert_type, COUNT(*) AS count
FROM alerts
WHERE resolved = 0
GROUP BY severity, alert_type
ORDER BY CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 ELSE 3 END;

-- Network bottleneck detection: high rejection rate interfaces
SELECT interface_id,
       COUNT(*) AS total_flows,
       SUM(CASE WHEN action = 'REJECT' THEN 1 ELSE 0 END) AS rejected,
       ROUND(SUM(CASE WHEN action = 'REJECT' THEN 1.0 ELSE 0 END) / COUNT(*) * 100, 2) AS rejection_rate
FROM flow_logs
GROUP BY interface_id
HAVING rejection_rate > 5
ORDER BY rejection_rate DESC;
