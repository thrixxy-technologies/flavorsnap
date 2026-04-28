#!/usr/bin/env python3
"""
Check for critical vulnerabilities and fail if threshold exceeded
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any

class CriticalVulnerabilityChecker:
    """Check for critical vulnerabilities and determine if build should fail"""
    
    def __init__(self):
        self.severity_weights = {
            'CRITICAL': 100,
            'HIGH': 50,
            'MEDIUM': 20,
            'LOW': 10,
            'INFO': 5
        }
    
    def check_vulnerabilities(self, fail_threshold: str = 'high') -> Dict[str, Any]:
        """Check vulnerabilities against threshold"""
        results = {
            'total_vulnerabilities': 0,
            'severity_counts': {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'INFO': 0},
            'risk_score': 0,
            'should_fail': False,
            'threshold': fail_threshold,
            'findings': []
        }
        
        # Collect all security reports
        report_files = [
            'dependency-security-reports/python-dependencies.json',
            'code-security-reports/bandit-report.json',
            'container-security-reports/trivy-report.json',
            'compliance-security-reports/compliance-analysis.json'
        ]
        
        for report_file in report_files:
            if Path(report_file).exists():
                try:
                    with open(report_file) as f:
                        data = json.load(f)
                    
                    vulnerabilities = self._extract_vulnerabilities(data)
                    results['findings'].extend(vulnerabilities)
                    
                except Exception as e:
                    print(f"Error reading {report_file}: {e}")
        
        # Count by severity
        for vuln in results['findings']:
            severity = vuln.get('severity', 'INFO').upper()
            if severity in results['severity_counts']:
                results['severity_counts'][severity] += 1
            else:
                results['severity_counts']['INFO'] += 1
            
            # Calculate risk score
            results['risk_score'] += self.severity_weights.get(severity, 0)
        
        results['total_vulnerabilities'] = len(results['findings'])
        
        # Determine if should fail based on threshold
        if fail_threshold.lower() == 'critical':
            results['should_fail'] = results['severity_counts']['CRITICAL'] > 0
        elif fail_threshold.lower() == 'high':
            results['should_fail'] = results['severity_counts']['CRITICAL'] > 0 or results['severity_counts']['HIGH'] > 0
        elif fail_threshold.lower() == 'medium':
            results['should_fail'] = results['severity_counts']['CRITICAL'] > 0 or results['severity_counts']['HIGH'] > 0 or results['severity_counts']['MEDIUM'] > 0
        elif fail_threshold.lower() == 'score':
            results['should_fail'] = results['risk_score'] > 200  # Arbitrary threshold
        
        return results
    
    def _extract_vulnerabilities(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract vulnerabilities from different report formats"""
        vulnerabilities = []
        
        if isinstance(data, dict):
            # Handle different report formats
            if 'findings' in data:
                findings = data['findings']
                if isinstance(findings, dict):
                    # Consolidate all finding categories
                    for category in ['dependencies', 'code_analysis', 'container_scan', 'compliance']:
                        if category in findings:
                            vulnerabilities.extend(findings[category])
                else:
                    vulnerabilities.extend(findings)
            elif 'results' in data:  # Bandit format
                vulnerabilities.extend(data['results'])
            elif 'vulnerabilities' in data:  # Trivy format
                vulnerabilities.extend(data['vulnerabilities'])
            elif isinstance(data, list):  # Direct list of vulnerabilities
                vulnerabilities.extend(data)
        
        return vulnerabilities
    
    def print_summary(self, results: Dict[str, Any]):
        """Print vulnerability summary"""
        print(f"\nVulnerability Check Summary")
        print(f"==========================")
        print(f"Total vulnerabilities: {results['total_vulnerabilities']}")
        print(f"Risk score: {results['risk_score']}")
        print(f"Fail threshold: {results['threshold']}")
        print(f"Should fail: {results['should_fail']}")
        print()
        
        print("Severity breakdown:")
        for severity, count in results['severity_counts'].items():
            if count > 0:
                print(f"  {severity}: {count}")
        
        if results['should_fail']:
            print(f"\n❌ BUILD SHOULD FAIL - Threshold '{results['threshold']}' exceeded")
            
            # Show critical and high severity findings
            critical_high = [v for v in results['findings'] if v.get('severity', '').upper() in ['CRITICAL', 'HIGH']]
            if critical_high:
                print(f"\nCritical/High severity findings:")
                for i, vuln in enumerate(critical_high[:10], 1):
                    print(f"  {i}. {vuln.get('severity', 'UNKNOWN')} - {vuln.get('issue_text', vuln.get('title', 'No description'))}")
                    if vuln.get('file'):
                        print(f"     File: {vuln['file']}")
                
                if len(critical_high) > 10:
                    print(f"  ... and {len(critical_high) - 10} more")
        else:
            print(f"\n✅ BUILD PASSES - Within threshold '{results['threshold']}'")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Check for critical vulnerabilities")
    parser.add_argument("--fail-threshold", choices=["critical", "high", "medium", "score"], default="high", help="Failure threshold")
    
    args = parser.parse_args()
    
    checker = CriticalVulnerabilityChecker()
    results = checker.check_vulnerabilities(args.fail_threshold)
    
    checker.print_summary(results)
    
    # Exit with error code if should fail
    if results['should_fail']:
        sys.exit(1)

if __name__ == "__main__":
    main()
