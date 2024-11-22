# src/data/log_generator.py
import random
from datetime import datetime, timedelta
import ipaddress
import json
from typing import List, Optional
import uuid

class LogGenerator:
    def __init__(self):
        self.templates = {
            'database': [
                "ERROR [Database] Connection timeout after {retries} retries to {db_name}",
                "ERROR [Database] Query execution failed: {error_msg}",
                "WARNING [Database] Slow query detected. Execution time: {exec_time}ms",
                "ERROR [Database] Max connections reached on {db_name}"
            ],
            'memory': [
                "WARNING [Memory] High memory usage: {mem_pct}% on {host}",
                "CRITICAL [Memory] Out of memory error on {host}",
                "WARNING [Memory] Memory threshold ({threshold}%) exceeded: current usage {mem_pct}%",
                "ERROR [Memory] Memory leak detected in {service}"
            ],
            'security': [
                "CRITICAL [Security] Multiple failed login attempts from IP: {ip_addr}",
                "WARNING [Security] Unusual traffic pattern detected from {ip_addr}",
                "CRITICAL [Security] Unauthorized access attempt to {resource}",
                "ERROR [Security] SSL certificate validation failed for {domain}"
            ],
            'application': [
                "ERROR [App] Request timeout for {endpoint}",
                "WARNING [App] High latency detected: {latency}ms",
                "ERROR [App] Service {service} not responding",
                "CRITICAL [App] Unhandled exception in {service}: {error_msg}"
            ]
        }
        
        self.error_messages = [
            "Connection refused",
            "Timeout waiting for response",
            "Invalid credentials",
            "Resource not found",
            "Internal server error"
        ]
        
        self.services = [
            "user-service", "auth-service", "payment-service",
            "inventory-service", "notification-service"
        ]
        
        self.hosts = [
            "prod-app-01", "prod-app-02", "prod-db-01",
            "prod-cache-01", "prod-worker-01"
        ]

    def generate_logs(self, 
                     num_entries: int = 100, 
                     start_time: Optional[datetime] = None,
                     time_interval: int = 60,
                     include_errors: bool = True) -> List[str]:
        """
        Generate a list of realistic log entries
        
        Args:
            num_entries: Number of log entries to generate
            start_time: Starting timestamp (defaults to now)
            time_interval: Seconds between log entries
            include_errors: Whether to include error conditions
        
        Returns:
            List of log entries
        """
        logs = []
        current_time = start_time or datetime.now()
        
        for i in range(num_entries):
            # Select random category and template
            category = random.choice(list(self.templates.keys()))
            template = random.choice(self.templates[category])
            
            # Generate context data
            context = self._generate_context(category, include_errors)
            
            # Format the log message
            log_message = template.format(**context)
            
            # Add timestamp
            timestamp = current_time + timedelta(seconds=i * time_interval)
            log_entry = f"{timestamp.isoformat()} {log_message}"
            
            logs.append(log_entry)
            
            # Simulate related errors if include_errors is True
            if include_errors and random.random() < 0.3:  # 30% chance of related error
                related_log = self._generate_related_error(category, context, timestamp)
                if related_log:
                    logs.append(related_log)
        
        return logs

    def _generate_context(self, category: str, include_errors: bool) -> dict:
        """Generate context data for log templates"""
        context = {
            'host': random.choice(self.hosts),
            'service': random.choice(self.services),
            'error_msg': random.choice(self.error_messages),
            'request_id': str(uuid.uuid4())
        }
        
        # Add category-specific context
        if category == 'database':
            context.update({
                'db_name': random.choice(['users_db', 'orders_db', 'products_db']),
                'retries': random.randint(1, 5),
                'exec_time': random.randint(1000, 5000)
            })
        elif category == 'memory':
            context.update({
                'mem_pct': random.randint(80, 99),
                'threshold': 80
            })
        elif category == 'security':
            context.update({
                'ip_addr': str(ipaddress.IPv4Address(random.randint(0, 2**32-1))),
                'resource': random.choice(['/api/admin', '/api/users', '/api/payments']),
                'domain': random.choice(['api.example.com', 'admin.example.com'])
            })
        elif category == 'application':
            context.update({
                'endpoint': random.choice(['/api/v1/users', '/api/v1/orders', '/api/v1/products']),
                'latency': random.randint(500, 3000)
            })
            
        return context

    def _generate_related_error(self, category: str, context: dict, timestamp: datetime) -> Optional[str]:
        """Generate a related error log entry"""
        related_templates = {
            'database': [
                "ERROR [Database] Failed to reconnect to {db_name} after connection timeout",
                "ERROR [Database] Failover attempted for {db_name} but failed"
            ],
            'memory': [
                "ERROR [Memory] Service {service} crashed due to memory exhaustion on {host}",
                "CRITICAL [Memory] System performance degraded due to memory pressure on {host}"
            ],
            'security': [
                "ERROR [Security] Account locked after multiple failures from {ip_addr}",
                "CRITICAL [Security] Blocking traffic from {ip_addr} due to suspicious activity"
            ],
            'application': [
                "ERROR [App] Circuit breaker triggered for {service}",
                "CRITICAL [App] Service {service} entering degraded state"
            ]
        }
        
        if category in related_templates:
            template = random.choice(related_templates[category])
            log_message = template.format(**context)
            timestamp_related = timestamp + timedelta(seconds=random.randint(1, 5))
            return f"{timestamp_related.isoformat()} {log_message}"
        
        return None

    def save_logs(self, logs: List[str], filename: str):
        """Save generated logs to a file"""
        with open(filename, 'w') as f:
            for log in logs:
                f.write(f"{log}\n")