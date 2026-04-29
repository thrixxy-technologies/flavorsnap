#!/usr/bin/env python3
"""
Send security notifications via various platforms
"""

import json
import smtplib
import sys
import argparse
from datetime import datetime
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from pathlib import Path
from typing import Dict, List, Any
import requests

class SecurityNotifier:
    """Send security notifications"""
    
    def __init__(self):
        self.platform_handlers = {
            'slack': self._send_slack_notification,
            'email': self._send_email_notification
        }
    
    def send_notification(self, platform: str, **kwargs) -> bool:
        """Send notification via specified platform"""
        if platform not in self.platform_handlers:
            print(f"Unsupported platform: {platform}")
            return False
        
        try:
            # Generate notification content
            content = self._generate_notification_content()
            return self.platform_handlers[platform](content, **kwargs)
        except Exception as e:
            print(f"Error sending {platform} notification: {e}")
            return False
    
    def _generate_notification_content(self) -> Dict[str, Any]:
        """Generate notification content from security reports"""
        content = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_vulnerabilities': 0,
                'critical_count': 0,
                'high_count': 0,
                'medium_count': 0,
                'low_count': 0
            },
            'findings': [],
            'recommendations': []
        }
        
        # Collect data from security reports
        report_files = [
            'security-reports/security-summary.json',
            'dependency-security-reports/python-dependencies.json',
            'code-security-reports/bandit-report.json',
            'container-security-reports/trivy-report.json',
            'compliance-security-reports/compliance-analysis.json'
        ]
        
        # Try to get comprehensive summary first
        if Path('security-reports/security-summary.json').exists():
            try:
                with open('security-reports/security-summary.json') as f:
                    data = json.load(f)
                
                if 'summary' in data:
                    content['summary'] = data['summary']
                    content['findings'] = data.get('detailed_findings', {})
                    content['recommendations'] = data.get('recommendations', [])
            except Exception as e:
                print(f"Error reading comprehensive report: {e}")
        
        # If no comprehensive report, collect individual reports
        if content['summary']['total_vulnerabilities'] == 0:
            for report_file in report_files:
                if Path(report_file).exists():
                    try:
                        with open(report_file) as f:
                            data = json.load(f)
                        
                        vulnerabilities = self._extract_vulnerabilities(data)
                        content['findings'].extend(vulnerabilities)
                        
                        # Update counts
                        for vuln in vulnerabilities:
                            severity = vuln.get('severity', 'INFO').upper()
                            content['summary']['total_vulnerabilities'] += 1
                            
                            if severity == 'CRITICAL':
                                content['summary']['critical_count'] += 1
                            elif severity == 'HIGH':
                                content['summary']['high_count'] += 1
                            elif severity == 'MEDIUM':
                                content['summary']['medium_count'] += 1
                            elif severity == 'LOW':
                                content['summary']['low_count'] += 1
                    
                    except Exception as e:
                        print(f"Error reading {report_file}: {e}")
        
        # Generate recommendations if not present
        if not content['recommendations']:
            content['recommendations'] = self._generate_recommendations(content['summary'])
        
        return content
    
    def _extract_vulnerabilities(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract vulnerabilities from different report formats"""
        vulnerabilities = []
        
        if isinstance(data, dict):
            if 'findings' in data:
                findings = data['findings']
                if isinstance(findings, dict):
                    for category in ['dependencies', 'code_analysis', 'container_scan', 'compliance']:
                        if category in findings:
                            vulnerabilities.extend(findings[category])
                else:
                    vulnerabilities.extend(findings)
            elif 'results' in data:
                vulnerabilities.extend(data['results'])
            elif 'vulnerabilities' in data:
                vulnerabilities.extend(data['vulnerabilities'])
        
        return vulnerabilities
    
    def _generate_recommendations(self, summary: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on summary"""
        recommendations = []
        
        if summary['critical_count'] > 0:
            recommendations.append(f"URGENT: Address {summary['critical_count']} critical vulnerabilities immediately")
        
        if summary['high_count'] > 0:
            recommendations.append(f"HIGH: Address {summary['high_count']} high-severity vulnerabilities within 7 days")
        
        if summary['total_vulnerabilities'] > 20:
            recommendations.append("Large number of vulnerabilities detected. Consider implementing automated security improvements.")
        
        recommendations.extend([
            "Review detailed security reports in the artifacts section",
            "Schedule regular security training for the development team",
            "Consider implementing automated security scanning in CI/CD pipeline"
        ])
        
        return recommendations
    
    def _send_slack_notification(self, content: Dict[str, Any], webhook: str = None) -> bool:
        """Send Slack notification"""
        if not webhook:
            print("Slack webhook URL not provided")
            return False
        
        # Determine message color based on severity
        color = "good"  # green
        if content['summary']['critical_count'] > 0:
            color = "danger"  # red
        elif content['summary']['high_count'] > 0:
            color = "warning"  # yellow
        elif content['summary']['total_vulnerabilities'] > 10:
            color = "warning"
        
        # Create Slack message
        message = {
            "attachments": [
                {
                    "color": color,
                    "title": "🔒 FlavorSnap Security Scan Results",
                    "fields": [
                        {
                            "title": "Total Vulnerabilities",
                            "value": str(content['summary']['total_vulnerabilities']),
                            "short": True
                        },
                        {
                            "title": "Critical",
                            "value": str(content['summary']['critical_count']),
                            "short": True
                        },
                        {
                            "title": "High",
                            "value": str(content['summary']['high_count']),
                            "short": True
                        },
                        {
                            "title": "Medium",
                            "value": str(content['summary']['medium_count']),
                            "short": True
                        },
                        {
                            "title": "Low",
                            "value": str(content['summary']['low_count']),
                            "short": True
                        }
                    ],
                    "footer": "FlavorSnap Security Scanner",
                    "ts": datetime.now().timestamp()
                }
            ]
        }
        
        # Add recommendations if critical or high vulnerabilities found
        if content['summary']['critical_count'] > 0 or content['summary']['high_count'] > 0:
            if content['recommendations']:
                message["attachments"][0]["fields"].append({
                    "title": "📋 Recommendations",
                    "value": "\n".join(f"• {rec}" for rec in content['recommendations'][:3]),
                    "short": False
                })
        
        try:
            response = requests.post(webhook, json=message, timeout=30)
            response.raise_for_status()
            print("Slack notification sent successfully")
            return True
        except Exception as e:
            print(f"Error sending Slack notification: {e}")
            return False
    
    def _send_email_notification(self, content: Dict[str, Any], to: str = None, 
                               smtp_host: str = None, smtp_user: str = None, 
                               smtp_pass: str = None) -> bool:
        """Send email notification"""
        if not all([to, smtp_host, smtp_user, smtp_pass]):
            print("Email configuration incomplete")
            return False
        
        # Create email message
        msg = MimeMultipart()
        msg['From'] = smtp_user
        msg['To'] = to
        msg['Subject'] = f"FlavorSnap Security Scan Results - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Determine urgency based on severity
        urgency = "LOW"
        if content['summary']['critical_count'] > 0:
            urgency = "CRITICAL"
        elif content['summary']['high_count'] > 0:
            urgency = "HIGH"
        elif content['summary']['total_vulnerabilities'] > 10:
            urgency = "MEDIUM"
        
        # Create email body
        body = f"""
Security Scan Report
==================

Scan Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Urgency Level: {urgency}

SUMMARY
--------
Total Vulnerabilities Found: {content['summary']['total_vulnerabilities']}
- Critical: {content['summary']['critical_count']}
- High: {content['summary']['high_count']}
- Medium: {content['summary']['medium_count']}
- Low: {content['summary']['low_count']}

"""
        
        if content['summary']['critical_count'] > 0 or content['summary']['high_count'] > 0:
            body += "IMMEDIATE ACTION REQUIRED\n"
            body += "========================\n\n"
            
            # Show top critical/high findings
            critical_high = [v for v in content['findings'] if v.get('severity', '').upper() in ['CRITICAL', 'HIGH']]
            for i, vuln in enumerate(critical_high[:5], 1):
                body += f"{i}. {vuln.get('severity', 'UNKNOWN')} - {vuln.get('issue_text', vuln.get('title', 'No description'))}\n"
                if vuln.get('file'):
                    body += f"   File: {vuln['file']}\n"
                if vuln.get('remediation'):
                    body += f"   Fix: {vuln['remediation']}\n"
                body += "\n"
        
        body += "RECOMMENDATIONS\n"
        body += "==============\n\n"
        for i, rec in enumerate(content['recommendations'], 1):
            body += f"{i}. {rec}\n"
        
        body += f"\n\nFor detailed information, please check the security reports in the CI/CD system.\n"
        body += f"This is an automated message from the FlavorSnap Security Scanner.\n"
        
        msg.attach(MimeText(body, 'plain'))
        
        try:
            server = smtplib.SMTP(smtp_host, 587)
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            server.quit()
            print("Email notification sent successfully")
            return True
        except Exception as e:
            print(f"Error sending email notification: {e}")
            return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Send security notifications")
    parser.add_argument("--platform", required=True, choices=["slack", "email"], help="Notification platform")
    parser.add_argument("--webhook", help="Slack webhook URL")
    parser.add_argument("--to", help="Email recipient")
    parser.add_argument("--smtp-host", help="SMTP server host")
    parser.add_argument("--smtp-user", help="SMTP username")
    parser.add_argument("--smtp-pass", help="SMTP password")
    
    args = parser.parse_args()
    
    notifier = SecurityNotifier()
    
    kwargs = {}
    if args.platform == "slack":
        kwargs['webhook'] = args.webhook
    elif args.platform == "email":
        kwargs['to'] = args.to
        kwargs['smtp_host'] = args.smtp_host
        kwargs['smtp_user'] = args.smtp_user
        kwargs['smtp_pass'] = args.smtp_pass
    
    success = notifier.send_notification(args.platform, **kwargs)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
