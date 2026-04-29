#!/usr/bin/env python3
"""
Automated security remediation execution
"""

import json
import os
import subprocess
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any

class AutomatedRemediation:
    """Execute automated security remediation"""
    
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.remediation_log = []
        
    def analyze_remediation_opportunities(self) -> Dict[str, Any]:
        """Analyze what can be automatically remediated"""
        analysis = {
            'automatable_fixes': [],
            'manual_review_required': [],
            'total_vulnerabilities': 0,
            'automatable_count': 0
        }
        
        # Look for security reports
        report_files = [
            'dependency-security-reports/python-dependencies.json',
            'code-security-reports/code-analysis.json',
            'container-security-reports/container-analysis.json',
            'compliance-security-reports/compliance-analysis.json'
        ]
        
        for report_file in report_files:
            if Path(report_file).exists():
                try:
                    with open(report_file) as f:
                        data = json.load(f)
                    
                    vulnerabilities = data.get('findings', {}).get('dependencies', []) + \
                                   data.get('findings', {}).get('code_analysis', []) + \
                                   data.get('findings', {}).get('container_scan', []) + \
                                   data.get('findings', {}).get('compliance', [])
                    
                    analysis['total_vulnerabilities'] += len(vulnerabilities)
                    
                    for vuln in vulnerabilities:
                        if self._can_automate(vuln):
                            analysis['automatable_fixes'].append(vuln)
                            analysis['automatable_count'] += 1
                        else:
                            analysis['manual_review_required'].append(vuln)
                            
                except Exception as e:
                    print(f"Error analyzing {report_file}: {e}")
        
        return analysis
    
    def _can_automate(self, vulnerability: Dict) -> bool:
        """Determine if a vulnerability can be automatically fixed"""
        vuln_type = vulnerability.get('type', '')
        severity = vulnerability.get('severity', '')
        
        # Only automate low and medium severity issues
        if severity in ['CRITICAL', 'HIGH']:
            return False
        
        # Automatable types
        automatable_types = [
            'python_dependency',
            'rust_dependency', 
            'node_dependency',
            'dockerfile',
            'compliance'
        ]
        
        return vuln_type in automatable_types
    
    def execute_remediation(self, dry_run: bool = True) -> Dict[str, Any]:
        """Execute automated remediation"""
        print(f"Running {'dry run' if dry_run else 'actual'} remediation...")
        
        analysis = self.analyze_remediation_opportunities()
        
        results = {
            'dry_run': dry_run,
            'analysis': analysis,
            'executed_fixes': [],
            'failed_fixes': [],
            'success_rate': 0
        }
        
        if not dry_run:
            # Execute dependency fixes
            if Path('remediation-scripts/dependencies.sh').exists():
                result = self._execute_script('remediation-scripts/dependencies.sh')
                results['executed_fixes'].append(result)
            
            # Execute code fixes
            if Path('remediation-scripts/code-fixes.sh').exists():
                result = self._execute_script('remediation-scripts/code-fixes.sh')
                results['executed_fixes'].append(result)
            
            # Execute container fixes
            if Path('remediation-scripts/container-fixes.sh').exists():
                result = self._execute_script('remediation-scripts/container-fixes.sh')
                results['executed_fixes'].append(result)
            
            # Execute compliance fixes
            if Path('remediation-scripts/compliance-fixes.sh').exists():
                result = self._execute_python_script('remediation-scripts/compliance-fixes.sh')
                results['executed_fixes'].append(result)
        else:
            # Dry run - just report what would be done
            for fix in analysis['automatable_fixes']:
                results['executed_fixes'].append({
                    'type': fix.get('type', 'unknown'),
                    'description': fix.get('remediation', 'No remediation available'),
                    'dry_run': True
                })
        
        # Calculate success rate
        if results['executed_fixes']:
            successful = len([f for f in results['executed_fixes'] if f.get('success', True)])
            results['success_rate'] = (successful / len(results['executed_fixes'])) * 100
        
        return results
    
    def _execute_script(self, script_path: str) -> Dict[str, Any]:
        """Execute a shell script"""
        try:
            result = subprocess.run(
                ['bash', script_path],
                capture_output=True,
                text=True,
                cwd=self.repo_root
            )
            
            return {
                'script': script_path,
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode
            }
        except Exception as e:
            return {
                'script': script_path,
                'success': False,
                'error': str(e)
            }
    
    def _execute_python_script(self, script_path: str) -> Dict[str, Any]:
        """Execute a Python script"""
        try:
            result = subprocess.run(
                ['python3', script_path],
                capture_output=True,
                text=True,
                cwd=self.repo_root
            )
            
            return {
                'script': script_path,
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode
            }
        except Exception as e:
            return {
                'script': script_path,
                'success': False,
                'error': str(e)
            }
    
    def generate_summary(self, results: Dict[str, Any]) -> str:
        """Generate remediation summary"""
        summary = []
        summary.append("# Automated Security Remediation Summary")
        summary.append("")
        
        if results['dry_run']:
            summary.append("## Dry Run Results")
        else:
            summary.append("## Remediation Results")
        
        summary.append("")
        summary.append(f"Total vulnerabilities analyzed: {results['analysis']['total_vulnerabilities']}")
        summary.append(f"Automatable fixes: {results['analysis']['automatable_count']}")
        summary.append(f"Manual review required: {len(results['analysis']['manual_review_required'])}")
        summary.append("")
        
        if results['executed_fixes']:
            summary.append("### Executed Fixes")
            for fix in results['executed_fixes']:
                status = "✅ Success" if fix.get('success', True) else "❌ Failed"
                summary.append(f"- {fix.get('script', 'Unknown script')}: {status}")
                if not fix.get('success', True) and fix.get('error'):
                    summary.append(f"  Error: {fix['error']}")
            summary.append("")
        
        if results['analysis']['manual_review_required']:
            summary.append("### Manual Review Required")
            for vuln in results['analysis']['manual_review_required'][:10]:  # Limit to 10
                summary.append(f"- {vuln.get('type', 'unknown')}: {vuln.get('issue_text', 'No description')}")
            
            if len(results['analysis']['manual_review_required']) > 10:
                remaining = len(results['analysis']['manual_review_required']) - 10
                summary.append(f"- ... and {remaining} more items")
            summary.append("")
        
        summary.append("### Recommendations")
        summary.append("- Review all automated fixes before deploying")
        summary.append("- Address manual review items promptly")
        summary.append("- Run security scan again after fixes")
        summary.append("- Update documentation and security policies")
        
        return "\n".join(summary)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Automated security remediation")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run only")
    parser.add_argument("--apply-fixes", action="store_true", help="Apply automated fixes")
    parser.add_argument("--output", type=Path, help="Output results to file")
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Repository root")
    
    args = parser.parse_args()
    
    remediation = AutomatedRemediation(args.repo)
    
    if args.apply_fixes:
        results = remediation.execute_remediation(dry_run=False)
    else:
        results = remediation.execute_remediation(dry_run=True)
    
    # Generate summary
    summary = remediation.generate_summary(results)
    print(summary)
    
    # Output results if requested
    if args.output:
        output_data = {
            'timestamp': str(Path().cwd()),
            'results': results,
            'summary': summary
        }
        
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\nResults saved to: {args.output}")
    
    # Exit with error if fixes failed and not dry run
    if not args.dry_run and not results['executed_fixes']:
        sys.exit(1)

if __name__ == "__main__":
    main()
