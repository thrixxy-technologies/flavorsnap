#!/usr/bin/env python3
"""
Generate security scan summary for GitHub Actions
"""

import json
import sys
from pathlib import Path

def generate_summary():
    """Generate security scan summary"""
    summary_lines = [
        "# Security Scan Summary",
        "",
        "## Scan Results",
        ""
    ]
    
    # Check dependencies
    deps_file = Path("dependency-security-reports/python-dependencies.json")
    if deps_file.exists():
        summary_lines.append("### Dependencies")
        try:
            with open(deps_file) as f:
                data = json.load(f)
            total = len(data.get('findings', {}).get('dependencies', []))
            summary_lines.append(f"- Python dependencies: {total} vulnerabilities")
        except:
            summary_lines.append("- Python dependencies: Scan completed")
    
    # Check code analysis
    code_file = Path("code-security-reports/bandit-report.json")
    if code_file.exists():
        summary_lines.append("### Code Analysis")
        try:
            with open(code_file) as f:
                data = json.load(f)
            total = len(data.get('results', []))
            summary_lines.append(f"- Bandit analysis: {total} issues")
        except:
            summary_lines.append("- Bandit analysis: Scan completed")
    
    # Check container security
    container_file = Path("container-security-reports/trivy-report.json")
    if container_file.exists():
        summary_lines.append("### Container Security")
        summary_lines.append("- Container scan completed")
    
    # Check compliance
    compliance_file = Path("compliance-security-reports/trufflehog-report.json")
    if compliance_file.exists():
        summary_lines.append("### Compliance")
        summary_lines.append("- Secret scanning completed")
    
    # Add recommendations
    summary_lines.extend([
        "",
        "### Recommendations",
        "- Review detailed reports in the artifacts section",
        "- Address high-severity findings promptly",
        "- Consider implementing automated remediation where safe",
        "- Schedule regular security training for the team"
    ])
    
    # Print to GitHub Actions summary
    for line in summary_lines:
        print(line)

if __name__ == "__main__":
    generate_summary()
