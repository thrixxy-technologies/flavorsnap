#!/usr/bin/env python3
"""
Generate comprehensive security report
"""

import json
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

class SecurityReportGenerator:
    """Generate comprehensive security reports"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        print("Generating comprehensive security report...")
        
        # Collect all security reports
        reports = self._collect_reports()
        
        # Generate summary
        summary = self._generate_summary(reports)
        
        # Generate HTML report
        html_report = self._generate_html_report(reports, summary)
        
        # Generate remediation priority
        remediation_priority = self._generate_remediation_priority(reports)
        
        # Save reports
        comprehensive_report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'summary': summary,
            'detailed_findings': reports,
            'remediation_priority': remediation_priority,
            'recommendations': self._generate_recommendations(summary)
        }
        
        # Save JSON report
        json_file = self.output_dir / "security-summary.json"
        with open(json_file, 'w') as f:
            json.dump(comprehensive_report, f, indent=2)
        
        # Save HTML report
        html_file = self.output_dir / "security-report.html"
        with open(html_file, 'w') as f:
            f.write(html_report)
        
        # Save remediation priority
        priority_file = self.output_dir / "remediation-priority.json"
        with open(priority_file, 'w') as f:
            json.dump(remediation_priority, f, indent=2)
        
        print(f"Reports generated in {self.output_dir}")
        return comprehensive_report
    
    def _collect_reports(self) -> Dict[str, Any]:
        """Collect all security scan reports"""
        reports = {
            'dependencies': {},
            'code_analysis': {},
            'container_scan': {},
            'compliance': {}
        }
        
        # Dependency reports
        dependency_files = [
            'dependency-security-reports/python-dependencies.json',
            'dependency-security-reports/rust-dependencies.json',
            'dependency-security-reports/node-dependencies.json'
        ]
        
        for file_path in dependency_files:
            if Path(file_path).exists():
                try:
                    with open(file_path) as f:
                        data = json.load(f)
                    reports['dependencies'][Path(file_path).stem] = data
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
        
        # Code analysis reports
        code_files = [
            'code-security-reports/bandit-report.json',
            'code-security-reports/semgrep-report.json',
            'code-security-reports/code-analysis.json'
        ]
        
        for file_path in code_files:
            if Path(file_path).exists():
                try:
                    with open(file_path) as f:
                        data = json.load(f)
                    reports['code_analysis'][Path(file_path).stem] = data
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
        
        # Container scan reports
        container_files = [
            'container-security-reports/hadolint-report.json',
            'container-security-reports/trivy-report.json',
            'container-security-reports/container-analysis.json'
        ]
        
        for file_path in container_files:
            if Path(file_path).exists():
                try:
                    with open(file_path) as f:
                        data = json.load(f)
                    reports['container_scan'][Path(file_path).stem] = data
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
        
        # Compliance reports
        compliance_files = [
            'compliance-security-reports/trufflehog-report.json',
            'compliance-security-reports/compliance-analysis.json',
            'compliance-security-reports/headers-report.json'
        ]
        
        for file_path in compliance_files:
            if Path(file_path).exists():
                try:
                    with open(file_path) as f:
                        data = json.load(f)
                    reports['compliance'][Path(file_path).stem] = data
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
        
        return reports
    
    def _generate_summary(self, reports: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary"""
        summary = {
            'total_vulnerabilities': 0,
            'severity_breakdown': {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'INFO': 0},
            'category_breakdown': {},
            'trend_analysis': 'N/A',
            'compliance_status': 'PASS',
            'security_score': 0
        }
        
        all_vulnerabilities = []
        
        # Collect all vulnerabilities
        for category, category_reports in reports.items():
            category_vulns = []
            
            for report_name, report_data in category_reports.items():
                if isinstance(report_data, dict):
                    # Handle different report formats
                    if 'findings' in report_data:
                        vulns = report_data['findings'].get('dependencies', []) + \
                               report_data['findings'].get('code_analysis', []) + \
                               report_data['findings'].get('container_scan', []) + \
                               report_data['findings'].get('compliance', [])
                    elif 'results' in report_data:  # Bandit format
                        vulns = report_data['results']
                    elif 'vulnerabilities' in report_data:  # Trivy format
                        vulns = report_data['vulnerabilities']
                    else:
                        vulns = []
                    
                    category_vulns.extend(vulns)
            
            summary['category_breakdown'][category] = len(category_vulns)
            all_vulnerabilities.extend(category_vulns)
        
        # Count by severity
        for vuln in all_vulnerabilities:
            severity = vuln.get('severity', 'INFO').upper()
            if severity in summary['severity_breakdown']:
                summary['severity_breakdown'][severity] += 1
            else:
                summary['severity_breakdown']['INFO'] += 1
        
        summary['total_vulnerabilities'] = len(all_vulnerabilities)
        
        # Calculate security score (0-100)
        critical_weight = 40
        high_weight = 20
        medium_weight = 10
        low_weight = 5
        info_weight = 1
        
        total_score = 100
        total_score -= summary['severity_breakdown']['CRITICAL'] * critical_weight
        total_score -= summary['severity_breakdown']['HIGH'] * high_weight
        total_score -= summary['severity_breakdown']['MEDIUM'] * medium_weight
        total_score -= summary['severity_breakdown']['LOW'] * low_weight
        total_score -= summary['severity_breakdown']['INFO'] * info_weight
        
        summary['security_score'] = max(0, total_score)
        
        # Determine compliance status
        if summary['severity_breakdown']['CRITICAL'] > 0:
            summary['compliance_status'] = 'FAIL'
        elif summary['severity_breakdown']['HIGH'] > 5:
            summary['compliance_status'] = 'WARNING'
        else:
            summary['compliance_status'] = 'PASS'
        
        return summary
    
    def _generate_html_report(self, reports: Dict[str, Any], summary: Dict[str, Any]) -> str:
        """Generate HTML security report"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>FlavorSnap Security Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
        .summary {{ background-color: #ecf0f1; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .severity-critical {{ color: #e74c3c; font-weight: bold; }}
        .severity-high {{ color: #e67e22; font-weight: bold; }}
        .severity-medium {{ color: #f39c12; font-weight: bold; }}
        .severity-low {{ color: #27ae60; }}
        .severity-info {{ color: #3498db; }}
        .score {{ font-size: 24px; font-weight: bold; }}
        .status-pass {{ color: #27ae60; }}
        .status-warning {{ color: #f39c12; }}
        .status-fail {{ color: #e74c3c; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .category {{ background-color: #3498db; color: white; padding: 10px; margin: 20px 0 10px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>FlavorSnap Security Report</h1>
        <p>Generated: {summary.get('timestamp', datetime.now().isoformat())}</p>
    </div>
    
    <div class="summary">
        <h2>Executive Summary</h2>
        <p><strong>Total Vulnerabilities:</strong> {summary['total_vulnerabilities']}</p>
        <p><strong>Security Score:</strong> <span class="score">{summary['security_score']}/100</span></p>
        <p><strong>Compliance Status:</strong> <span class="status-{summary['compliance_status'].lower()}">{summary['compliance_status']}</span></p>
        
        <h3>Severity Breakdown</h3>
        <ul>
            <li class="severity-critical">Critical: {summary['severity_breakdown']['CRITICAL']}</li>
            <li class="severity-high">High: {summary['severity_breakdown']['HIGH']}</li>
            <li class="severity-medium">Medium: {summary['severity_breakdown']['MEDIUM']}</li>
            <li class="severity-low">Low: {summary['severity_breakdown']['LOW']}</li>
            <li class="severity-info">Info: {summary['severity_breakdown']['INFO']}</li>
        </ul>
        
        <h3>Category Breakdown</h3>
        <ul>
"""
        
        for category, count in summary['category_breakdown'].items():
            html += f"            <li>{category.replace('_', ' ').title()}: {count}</li>\n"
        
        html += """
        </ul>
    </div>
    
    <div class="category">
        <h2>Detailed Findings</h2>
    </div>
"""
        
        # Add detailed findings for each category
        for category, category_reports in reports.items():
            if category_reports:
                html += f'    <h3>{category.replace("_", " ").title()}</h3>\n'
                
                for report_name, report_data in category_reports.items():
                    html += f'    <h4>{report_name}</h4>\n'
                    
                    # Extract vulnerabilities based on report format
                    vulnerabilities = []
                    if isinstance(report_data, dict):
                        if 'findings' in report_data:
                            vulnerabilities = report_data['findings'].get('dependencies', []) + \
                                           report_data['findings'].get('code_analysis', []) + \
                                           report_data['findings'].get('container_scan', []) + \
                                           report_data['findings'].get('compliance', [])
                        elif 'results' in report_data:
                            vulnerabilities = report_data['results']
                        elif 'vulnerabilities' in report_data:
                            vulnerabilities = report_data['vulnerabilities']
                    
                    if vulnerabilities:
                        html += '    <table>\n'
                        html += '        <tr><th>Severity</th><th>Issue</th><th>File</th><th>Remediation</th></tr>\n'
                        
                        for vuln in vulnerabilities[:20]:  # Limit to 20 for readability
                            severity = vuln.get('severity', 'INFO')
                            severity_class = f"severity-{severity.lower()}"
                            
                            issue = vuln.get('issue_text', vuln.get('title', 'N/A'))
                            file_path = vuln.get('file', vuln.get('filename', 'N/A'))
                            remediation = vuln.get('remediation', 'Manual review required')
                            
                            html += f'        <tr><td class="{severity_class}">{severity}</td><td>{issue}</td><td>{file_path}</td><td>{remediation}</td></tr>\n'
                        
                        html += '    </table>\n'
                    else:
                        html += '    <p>No vulnerabilities found.</p>\n'
        
        html += """
</body>
</html>
"""
        
        return html
    
    def _generate_remediation_priority(self, reports: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate prioritized remediation list"""
        all_items = []
        
        # Collect all remediation items
        for category, category_reports in reports.items():
            for report_name, report_data in category_reports.items():
                if isinstance(report_data, dict):
                    # Extract vulnerabilities
                    vulnerabilities = []
                    if 'findings' in report_data:
                        vulnerabilities = report_data['findings'].get('dependencies', []) + \
                                       report_data['findings'].get('code_analysis', []) + \
                                       report_data['findings'].get('container_scan', []) + \
                                       report_data['findings'].get('compliance', [])
                    elif 'results' in report_data:
                        vulnerabilities = report_data['results']
                    elif 'vulnerabilities' in report_data:
                        vulnerabilities = report_data['vulnerabilities']
                    
                    for vuln in vulnerabilities:
                        priority = self._calculate_priority(vuln)
                        all_items.append({
                            'priority': priority,
                            'severity': vuln.get('severity', 'INFO'),
                            'category': category,
                            'tool': report_name,
                            'issue': vuln.get('issue_text', vuln.get('title', 'N/A')),
                            'file': vuln.get('file', vuln.get('filename', 'N/A')),
                            'remediation': vuln.get('remediation', 'Manual review required'),
                            'automatable': self._is_automatable(vuln)
                        })
        
        # Sort by priority
        priority_order = {'IMMEDIATE': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'INFO': 4}
        all_items.sort(key=lambda x: priority_order.get(x['priority'], 4))
        
        return all_items
    
    def _calculate_priority(self, vulnerability: Dict[str, Any]) -> str:
        """Calculate remediation priority"""
        severity = vulnerability.get('severity', 'INFO').upper()
        vuln_type = vulnerability.get('type', '')
        
        if severity == 'CRITICAL':
            return 'IMMEDIATE'
        elif severity == 'HIGH':
            if vuln_type in ['python_dependency', 'rust_dependency', 'node_dependency']:
                return 'IMMEDIATE'
            return 'HIGH'
        elif severity == 'MEDIUM':
            if vuln_type in ['python_dependency', 'rust_dependency', 'node_dependency']:
                return 'HIGH'
            return 'MEDIUM'
        elif severity == 'LOW':
            return 'LOW'
        else:
            return 'INFO'
    
    def _is_automatable(self, vulnerability: Dict[str, Any]) -> bool:
        """Check if vulnerability is automatable"""
        vuln_type = vulnerability.get('type', '')
        severity = vulnerability.get('severity', '')
        
        if severity in ['CRITICAL', 'HIGH']:
            return False
        
        automatable_types = [
            'python_dependency',
            'rust_dependency',
            'node_dependency',
            'dockerfile',
            'compliance'
        ]
        
        return vuln_type in automatable_types
    
    def _generate_recommendations(self, summary: Dict[str, Any]) -> List[str]:
        """Generate security recommendations"""
        recommendations = []
        
        if summary['severity_breakdown']['CRITICAL'] > 0:
            recommendations.append(f"URGENT: Address {summary['severity_breakdown']['CRITICAL']} critical vulnerabilities immediately")
        
        if summary['severity_breakdown']['HIGH'] > 0:
            recommendations.append(f"HIGH: Address {summary['severity_breakdown']['HIGH']} high-severity vulnerabilities within 7 days")
        
        if summary['security_score'] < 70:
            recommendations.append("Security score is below acceptable threshold. Implement comprehensive security improvements.")
        
        if summary['category_breakdown'].get('dependencies', 0) > 10:
            recommendations.append("Consider implementing automated dependency updates and monitoring.")
        
        if summary['category_breakdown'].get('code_analysis', 0) > 5:
            recommendations.append("Implement secure coding practices and regular code reviews.")
        
        if summary['category_breakdown'].get('compliance', 0) > 0:
            recommendations.append("Establish security compliance checklist for deployments.")
        
        # General recommendations
        recommendations.extend([
            "Implement automated security scanning in CI/CD pipeline",
            "Regular security training for development team",
            "Establish incident response procedures",
            "Monitor security advisories for dependencies",
            "Conduct regular penetration testing",
            "Implement security metrics and KPIs",
            "Regular security audits and assessments"
        ])
        
        return recommendations

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Generate comprehensive security report")
    parser.add_argument("--output-dir", type=Path, default=Path("security-reports"), help="Output directory")
    
    args = parser.parse_args()
    
    generator = SecurityReportGenerator(args.output_dir)
    generator.generate_comprehensive_report()

if __name__ == "__main__":
    main()
