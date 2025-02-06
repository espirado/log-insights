import datetime

# Set the base time for January 1, 2025 at 10:01:00
base_time = datetime.datetime(2025, 1, 1, 10, 1, 0)

# Define 20 log message templates
log_templates = [
    "[ERROR] [{}] EC2 instance 'i-0123456789abcdef0' terminated unexpectedly: InstanceLimitExceeded.",
    "[DEBUG] [{}] Validating deployment configuration for Kubernetes cluster 'prod-cluster'.",
    "[WARNING] [{}] IAM role 'ReadOnlyAccess' used in high-privilege context.",
    "[INFO]  [{}] Cloud Function 'process-data' executed successfully in 250ms.",
    "[ERROR] [{}] Failed to connect to PostgreSQL database: Connection timeout.",
    "[DEBUG] [{}] Autoscaler evaluated workload distribution for Cloud Run service 'web-service'.",
    "[WARNING] [{}] High memory usage detected in pod 'analytics-worker' (95%).",
    "[INFO]  [{}] Database backup for 'customer-db' completed successfully.",
    "[ERROR] [{}] Cloud Run service 'payment-service' failed to start: HTTP 502.",
    "[DEBUG] [{}] Fetching metrics for EC2 Auto Scaling group 'web-app-asg'.",
    "[WARNING] [{}] Kubernetes node 'kube-node-2' nearing maximum pod capacity.",
    "[INFO]  [{}] IAM policy 'FullAccess' attached to user 'admin-user'.",
    "[ERROR] [{}] Pod 'backend-1' CrashLoopBackOff detected in namespace 'default'.",
    "[DEBUG] [{}] Request latency for Cloud Function 'get-user-data' measured at 120ms.",
    "[WARNING] [{}] PostgreSQL replication lag detected on 'db-replica-1' (10 seconds).",
    "[INFO]  [{}] Deployment 'frontend-app' scaled to 10 replicas in Kubernetes.",
    "[ERROR] [{}] CloudWatch alarm triggered for EC2 instance 'i-0abcdef1234567890'.",
    "[DEBUG] [{}] Investigating Kubernetes pod eviction policies in namespace 'monitoring'.",
    "[WARNING] [{}] Excessive API calls detected to IAM service from IP 192.168.0.1.",
    "[INFO]  [{}] New revision 'rev-002' deployed for Cloud Run service 'data-service'."
]

logs = []

# Generate 100 logs
for i in range(100):
    # Cycle the day offset from 0 to 6 (i.e. January 1 + offset)
    day_offset = i % 7
    # Advance base time by i minutes to ensure unique times
    log_time = base_time + datetime.timedelta(days=day_offset, minutes=i)
    # Format timestamp as ISO 8601 with Zulu time indicator
    timestamp = log_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    # Cycle through the templates using modulo
    template = log_templates[i % len(log_templates)]
    # Insert the timestamp into the template
    log_entry = template.format(timestamp)
    logs.append(log_entry)

# Print the generated logs
for log in logs:
    print(log)
