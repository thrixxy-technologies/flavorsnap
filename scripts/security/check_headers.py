#!/usr/bin/env python3
"""
Check security headers configuration
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any

class SecurityHeaderChecker:
    """Check security headers in configuration files"""
    
    def __init__(self):
        self.required_headers = {
            'X-Content-Type-Options': {
                'expected': 'nosniff',
                'severity': 'HIGH',
                'description': 'Prevents MIME-type sniffing'
            },
            'X-Frame-Options': {
                'expected': 'DENY',
                'severity': 'MEDIUM',
                'description': 'Prevents clickjacking attacks'
            },
            'X-XSS-Protection': {
                'expected': '1; mode=block',
                'severity': 'MEDIUM',
                'description': 'Enables XSS protection in browsers'
            },
            'Strict-Transport-Security': {
                'expected': 'max-age=31536000; includeSubDomains',
                'severity': 'HIGH',
                'description': 'Enforces HTTPS connections'
            },
            'Content-Security-Policy': {
                'expected': 'default-src \'self\'',
                'severity': 'HIGH',
                'description': 'Prevents XSS and data injection attacks'
            },
            'Referrer-Policy': {
                'expected': 'strict-origin-when-cross-origin',
                'severity': 'LOW',
                'description': 'Controls referrer information leakage'
            },
            'Permissions-Policy': {
                'expected': 'geolocation=(), microphone=(), camera=()',
                'severity': 'LOW',
                'description': 'Controls browser feature access'
            }
        }
    
    def check_headers(self) -> Dict[str, Any]:
        """Check security headers in configuration files"""
        results = {
            'timestamp': str(Path().cwd()),
            'findings': [],
            'missing_headers': [],
            'misconfigured_headers': [],
            'compliance_score': 0
        }
        
        # Look for configuration files
        config_files = self._find_config_files()
        
        for config_file in config_files:
            file_results = self._check_file_headers(config_file)
            results['findings'].extend(file_results['findings'])
            results['missing_headers'].extend(file_results['missing_headers'])
            results['misconfigured_headers'].extend(file_results['misconfigured_headers'])
        
        # Calculate compliance score
        total_headers = len(self.required_headers)
        found_headers = total_headers - len(set(results['missing_headers']))
        results['compliance_score'] = (found_headers / total_headers) * 100
        
        return results
    
    def _find_config_files(self) -> List[Path]:
        """Find configuration files that might contain security headers"""
        config_patterns = [
            '**/*.py',
            '**/*.js',
            '**/*.ts',
            '**/*.yml',
            '**/*.yaml',
            '**/*.json',
            '**/*.env*',
            '**/config*',
            '**/security*',
            '**/*security*'
        ]
        
        config_files = []
        for pattern in config_patterns:
            config_files.extend(Path('.').glob(pattern))
        
        # Filter out common non-config files
        exclude_patterns = [
            '__pycache__',
            'node_modules',
            '.git',
            'test',
            'tests',
            'venv',
            'env'
        ]
        
        filtered_files = []
        for file_path in config_files:
            if not any(pattern in str(file_path) for pattern in exclude_patterns):
                filtered_files.append(file_path)
        
        return filtered_files
    
    def _check_file_headers(self, file_path: Path) -> Dict[str, Any]:
        """Check security headers in a specific file"""
        results = {
            'findings': [],
            'missing_headers': [],
            'misconfigured_headers': []
        }
        
        try:
            content = file_path.read_text()
            
            # Check for security headers configuration
            found_headers = set()
            
            for header_name, header_info in self.required_headers.items():
                if header_name.lower() in content.lower():
                    found_headers.add(header_name)
                    
                    # Check if properly configured
                    expected_value = header_info['expected']
                    if expected_value.lower() not in content.lower():
                        results['misconfigured_headers'].append({
                            'file': str(file_path),
                            'header': header_name,
                            'issue': 'Header found but may be misconfigured',
                            'severity': header_info['severity'],
                            'description': header_info['description'],
                            'expected': expected_value,
                            'remediation': f'Ensure {header_name} is set to "{expected_value}"'
                        })
                else:
                    results['missing_headers'].append({
                        'file': str(file_path),
                        'header': header_name,
                        'severity': header_info['severity'],
                        'description': header_info['description'],
                        'remediation': f'Add {header_name}: "{header_info["expected"]}" to security configuration'
                    })
            
            # Add findings for files with security configurations
            if found_headers:
                results['findings'].append({
                    'file': str(file_path),
                    'type': 'security_headers',
                    'headers_found': list(found_headers),
                    'headers_count': len(found_headers),
                    'total_required': len(self.required_headers),
                    'compliance_percentage': (len(found_headers) / len(self.required_headers)) * 100
                })
            
        except Exception as e:
            results['findings'].append({
                'file': str(file_path),
                'type': 'error',
                'error': str(e),
                'message': f'Could not read file: {e}'
            })
        
        return results
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate header check report"""
        report = []
        report.append("# Security Headers Report")
        report.append(f"Generated: {results['timestamp']}")
        report.append("")
        
        report.append("## Summary")
        report.append(f"Compliance Score: {results['compliance_score']:.1f}%")
        report.append(f"Missing Headers: {len(results['missing_headers'])}")
        report.append(f"Misconfigured Headers: {len(results['misconfigured_headers'])}")
        report.append("")
        
        if results['missing_headers']:
            report.append("## Missing Security Headers")
            for missing in sorted(results['missing_headers'], key=lambda x: x['severity']):
                report.append(f"- **{missing['header']}** ({missing['severity']})")
                report.append(f"  - File: {missing['file']}")
                report.append(f"  - Description: {missing['description']}")
                report.append(f"  - Remediation: {missing['remediation']}")
                report.append("")
        
        if results['misconfigured_headers']:
            report.append("## Misconfigured Security Headers")
            for misconfig in sorted(results['misconfigured_headers'], key=lambda x: x['severity']):
                report.append(f"- **{misconfig['header']}** ({misconfig['severity']})")
                report.append(f"  - File: {misconfig['file']}")
                report.append(f"  - Issue: {misconfig['issue']}")
                report.append(f"  - Expected: {misconfig['expected']}")
                report.append(f"  - Remediation: {misconfig['remediation']}")
                report.append("")
        
        if results['findings']:
            report.append("## Files with Security Configuration")
            for finding in results['findings']:
                if finding['type'] == 'security_headers':
                    report.append(f"- **{finding['file']}**")
                    report.append(f"  - Headers found: {finding['headers_count']}/{finding['total_required']}")
                    report.append(f"  - Compliance: {finding['compliance_percentage']:.1f}%")
                    if finding['headers_found']:
                        report.append(f"  - Headers: {', '.join(finding['headers_found'])}")
                    report.append("")
        
        return "\n".join(report)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Check security headers configuration")
    parser.add_argument("--output", type=Path, help="Output report file")
    
    args = parser.parse_args()
    
    checker = SecurityHeaderChecker()
    results = checker.check_headers()
    
    # Generate report
    report = checker.generate_report(results)
    print(report)
    
    # Save results if output path provided
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {args.output}")

if __name__ == "__main__":
    main()
