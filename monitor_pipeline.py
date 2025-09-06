#!/usr/bin/env python3
"""
Pipeline Monitoring Script
Monitors the health and performance of the news processing pipeline.
"""

import os
import json
import yaml
import shutil
from datetime import datetime, timedelta
import requests

# Configuration
MONITORING_CONFIG = "monitoring_config.yaml"
LOGS_DIR = "logs"
STATUS_FILES = [
    "content_fetcher_status.json",
    "text_extractor_status.json", 
    "ai_analyzer_status.json",
    "archive_manager_status.json",
    "rss_generator_status.json"
]

class PipelineMonitor:
    def __init__(self):
        self.config = self.load_config()
        self.alerts = []

    def load_config(self):
        """Load monitoring configuration"""
        try:
            with open(MONITORING_CONFIG, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Warning: Could not load monitoring config: {e}")
            return {}

    def check_disk_usage(self):
        """Check disk usage and alert if thresholds exceeded"""
        try:
            total, used, free = shutil.disk_usage('.')
            usage_percent = (used / total) * 100
            
            warning_threshold = self.config.get('monitoring', {}).get('disk_usage_warning', 80)
            critical_threshold = self.config.get('monitoring', {}).get('disk_usage_critical', 90)
            
            if usage_percent >= critical_threshold:
                self.alerts.append(f"CRITICAL: Disk usage at {usage_percent:.1f}%")
            elif usage_percent >= warning_threshold:
                self.alerts.append(f"WARNING: Disk usage at {usage_percent:.1f}%")
            
            return {
                'total_gb': total / (1024**3),
                'used_gb': used / (1024**3),
                'free_gb': free / (1024**3),
                'usage_percent': usage_percent
            }
        except Exception as e:
            self.alerts.append(f"ERROR: Could not check disk usage: {e}")
            return None

    def check_recent_errors(self):
        """Check for recent errors in log files"""
        error_counts = {}
        
        if not os.path.exists(LOGS_DIR):
            return error_counts
        
        # Check the most recent month's logs
        now = datetime.now()
        current_month = now.strftime("%Y-%m")
        month_path = os.path.join(LOGS_DIR, current_month)
        
        if not os.path.exists(month_path):
            return error_counts
        
        # Check error log files
        error_files = [f for f in os.listdir(month_path) if 'error' in f.lower()]
        
        for error_file in error_files:
            error_path = os.path.join(month_path, error_file)
            try:
                with open(error_path, 'r') as f:
                    lines = f.readlines()
                    
                # Count errors in the last 24 hours
                cutoff_time = now - timedelta(hours=24)
                recent_errors = 0
                
                for line in lines:
                    if line.strip():  # Non-empty line
                        recent_errors += 1
                
                if recent_errors > 0:
                    component = error_file.replace('_errors.log', '')
                    error_counts[component] = recent_errors
                    
            except Exception as e:
                self.alerts.append(f"WARNING: Could not read error file {error_file}: {e}")
        
        # Check against thresholds
        thresholds = self.config.get('error_thresholds', {})
        for component, count in error_counts.items():
            threshold_key = f"{component}_failures"
            if threshold_key in thresholds and count >= thresholds[threshold_key]:
                self.alerts.append(f"ALERT: {component} has {count} recent errors")
        
        return error_counts

    def check_pipeline_status(self):
        """Check the status of each pipeline component"""
        status_summary = {}
        
        for status_file in STATUS_FILES:
            if os.path.exists(status_file):
                try:
                    with open(status_file, 'r') as f:
                        status_data = json.load(f)
                    
                    component = status_file.replace('_status.json', '')
                    
                    # Count successful vs failed operations
                    success_count = sum(1 for item in status_data.values() 
                                      if isinstance(item, dict) and item.get('status') == 'success')
                    error_count = sum(1 for item in status_data.values() 
                                    if isinstance(item, dict) and item.get('status') == 'error')
                    
                    status_summary[component] = {
                        'success': success_count,
                        'errors': error_count,
                        'total': success_count + error_count,
                        'success_rate': success_count / (success_count + error_count) * 100 if (success_count + error_count) > 0 else 0
                    }
                    
                    # Alert if success rate is low
                    if status_summary[component]['success_rate'] < 80 and status_summary[component]['total'] > 10:
                        self.alerts.append(f"WARNING: {component} success rate is {status_summary[component]['success_rate']:.1f}%")
                        
                except Exception as e:
                    self.alerts.append(f"ERROR: Could not read {status_file}: {e}")
        
        return status_summary

    def send_email_alert(self, subject, body):
        """Send email alert using SendGrid (if configured)"""
        email_config = self.config.get('email', {})
        if not email_config.get('enabled', False):
            return False
        
        api_key = email_config.get('sendgrid_api_key')
        if not api_key or api_key == "YOUR_SENDGRID_API_KEY_HERE":
            print("WARNING: SendGrid API key not configured")
            return False
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'personalizations': [
                {
                    'to': [{'email': email} for email in email_config.get('to_emails', [])],
                    'subject': subject
                }
            ],
            'from': {'email': email_config.get('from_email', 'alerts@localhost')},
            'content': [
                {
                    'type': 'text/plain',
                    'value': body
                }
            ]
        }
        
        try:
            response = requests.post('https://api.sendgrid.com/v3/mail/send', 
                                   headers=headers, json=data, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Failed to send email alert: {e}")
            return False

    def ping_health_checks(self):
        """Ping external monitoring services"""
        health_config = self.config.get('health_checks', {})
        if not health_config.get('enabled', False):
            return
        
        webhook_urls = health_config.get('webhook_urls', [])
        for url in webhook_urls:
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                print(f"✓ Pinged health check: {url}")
            except Exception as e:
                self.alerts.append(f"WARNING: Health check failed for {url}: {e}")

    def generate_report(self):
        """Generate monitoring report"""
        print(f"=== Pipeline Monitoring Report ===")
        print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Disk usage
        disk_info = self.check_disk_usage()
        if disk_info:
            print(f"Disk Usage: {disk_info['usage_percent']:.1f}% ({disk_info['used_gb']:.1f}GB / {disk_info['total_gb']:.1f}GB)")
        
        # Pipeline status
        print("\nPipeline Component Status:")
        status_summary = self.check_pipeline_status()
        for component, stats in status_summary.items():
            print(f"  {component}: {stats['success']} success, {stats['errors']} errors ({stats['success_rate']:.1f}% success rate)")
        
        # Recent errors
        print("\nRecent Errors (24h):")
        error_counts = self.check_recent_errors()
        if error_counts:
            for component, count in error_counts.items():
                print(f"  {component}: {count} errors")
        else:
            print("  No recent errors found")
        
        # Alerts
        if self.alerts:
            print(f"\n=== ALERTS ({len(self.alerts)}) ===")
            for alert in self.alerts:
                print(f"  ! {alert}")
            
            # Send email if alerts exist
            if self.config.get('email', {}).get('enabled', False):
                subject = f"News Pipeline Alert - {len(self.alerts)} issues detected"
                body = "Alerts detected in news processing pipeline:\n\n" + "\n".join(f"- {alert}" for alert in self.alerts)
                if self.send_email_alert(subject, body):
                    print("  Email alert sent")
        else:
            print("\n✓ No alerts - system healthy")
        
        # Health checks
        self.ping_health_checks()
        
        print()

    def run(self):
        """Run monitoring checks"""
        self.generate_report()

if __name__ == "__main__":
    monitor = PipelineMonitor()
    monitor.run()