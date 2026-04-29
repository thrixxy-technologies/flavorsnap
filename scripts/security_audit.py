#!/usr/bin/env python3
"""
FlavorSnap Security Audit Script  —  Issue #226

Automates the full security audit pipeline:
  1. Bandit   — static analysis for Python source vulnerabilities
  2. Safety   — known CVEs in installed dependencies
  3. pytest   — runs the tests/security/ suite
  4. Headers  — validates HTTP security headers on a live server
  5. CORS     — checks for misconfigured cross-origin policy

Usage:
    python scripts/security_audit.py
    python scripts/security_audit.py --url http://localhost:8000
    python scripts/security_audit.py --url http://localhost:8000 --fail-on-high
    python scripts/security_audit.py --output-dir reports/

Exit codes:
    0  All checks passed
    1  One or more HIGH / CRITICAL findings (when --fail-on-high)
    2  Invocation / configuration error
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("security_audit")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    check: str
    severity: str        # CRITICAL | HIGH | MEDIUM | LOW | INFO
    title: str
    detail: str
    remediation: str = ""


@dataclass
class AuditReport:
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    findings: list[Finding] = field(default_factory=list)
    passed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "CRITICAL")

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "HIGH")

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "MEDIUM")

    @property
    def low_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "LOW")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


# ---------------------------------------------------------------------------
# Check 1 — Bandit static analysis
# ---------------------------------------------------------------------------

def check_bandit(repo_root: Path, report: AuditReport) -> None:
    log.info("Running Bandit static analysis ...")

    src_dirs = [d for d in ["src", "backend", "scripts", "app"] if (repo_root / d).exists()]
    if not src_dirs:
        report.skipped.append("bandit — no Python source directories found")
        return

    result = _run(
        [
            sys.executable, "-m", "bandit",
            "--recursive",
            "--format", "json",
            "--severity-level", "low",
            "--confidence-level", "low",
            *src_dirs,
        ],
        cwd=repo_root,
    )

    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        report.errors.append(f"bandit: failed to parse output\n{result.stderr[:300]}")
        return

    results = data.get("results", [])
    if not results:
        report.passed.append("bandit — no issues found")
        return

    for issue in results:
        sev = issue.get("issue_severity", "LOW")
        report.findings.append(Finding(
            check="bandit",
            severity=sev,
            title=f"[{issue.get('test_id')}] {issue.get('test_name', '')}",
            detail=(
                f"{issue.get('filename')}:{issue.get('line_number')} "
                f"— {issue.get('issue_text', '')}"
            ),
            remediation=(
                f"https://bandit.readthedocs.io/en/latest/plugins/"
                f"{issue.get('test_id', '').lower()}.html"
            ),
        ))

    log.info("Bandit: %d issue(s) found", len(results))


# ---------------------------------------------------------------------------
# Check 2 — Safety dependency CVE scan
# ---------------------------------------------------------------------------

def check_safety(report: AuditReport) -> None:
    log.info("Running Safety dependency vulnerability scan ...")

    result = _run([sys.executable, "-m", "safety", "check", "--json"])

    raw = result.stdout.strip()
    if not raw:
        report.errors.append("safety: no output — is `safety` installed?")
        return

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        report.errors.append(f"safety: failed to parse JSON\n{raw[:300]}")
        return

    vulnerabilities = data if isinstance(data, list) else data.get("vulnerabilities", [])

    if not vulnerabilities:
        report.passed.append("safety — no known CVEs in dependencies")
        return

    for vuln in vulnerabilities:
        if isinstance(vuln, list):
            package, spec, installed, advisory, vuln_id = (vuln + [""] * 5)[:5]
            report.findings.append(Finding(
                check="safety",
                severity="HIGH",
                title=f"CVE in {package} {installed}",
                detail=advisory,
                remediation=f"Upgrade {package} to a version matching {spec}",
            ))
        else:
            package   = vuln.get("package_name", "unknown")
            installed = vuln.get("analyzed_version", "?")
            advisory  = vuln.get("advisory", "")
            vuln_id   = vuln.get("vulnerability_id", "")
            fix       = vuln.get("fixed_versions", [])
            report.findings.append(Finding(
                check="safety",
                severity="HIGH",
                title=f"[{vuln_id}] {package} {installed}",
                detail=advisory,
                remediation=(
                    f"Upgrade {package} to {', '.join(fix)}" if fix
                    else f"Check {vuln_id} for available patches"
                ),
            ))

    log.info("Safety: %d vulnerability(ies) found", len(vulnerabilities))


# ---------------------------------------------------------------------------
# Check 3 — pytest security suite
# ---------------------------------------------------------------------------

def check_security_tests(repo_root: Path, report: AuditReport) -> None:
    log.info("Running pytest security suite ...")

    security_dir = repo_root / "tests" / "security"
    if not security_dir.exists():
        report.skipped.append("pytest-security — tests/security/ not found")
        return

    junit_path = repo_root / "security_junit.xml"
    result = _run(
        [
            sys.executable, "-m", "pytest",
            str(security_dir),
            "-m", "security",
            "--tb=short",
            "--no-header",
            "-q",
            f"--junit-xml={junit_path}",
        ],
        cwd=repo_root,
    )

    if junit_path.exists():
        _parse_junit(junit_path, report)
        junit_path.unlink(missing_ok=True)
    else:
        for line in result.stdout.splitlines():
            if line.startswith("FAILED"):
                report.findings.append(Finding(
                    check="pytest-security",
                    severity="HIGH",
                    title=f"Security test failed: {line}",
                    detail=line,
                    remediation="Fix the underlying vulnerability flagged by this test.",
                ))

    if result.returncode == 0:
        report.passed.append("pytest-security — all tests passed")
    elif result.returncode == 5:
        report.skipped.append("pytest-security — no tests collected (check markers)")
    else:
        log.warning("pytest security suite exited with code %d", result.returncode)


def _parse_junit(junit_path: Path, report: AuditReport) -> None:
    try:
        tree = ET.parse(junit_path)
    except ET.ParseError as exc:
        report.errors.append(f"junit parse error: {exc}")
        return

    for testcase in tree.iter("testcase"):
        failure = testcase.find("failure")
        error   = testcase.find("error")
        node    = failure if failure is not None else error
        if node is not None:
            classname = testcase.get("classname", "")
            name      = testcase.get("name", "")
            message   = node.get("message", node.text or "")
            report.findings.append(Finding(
                check="pytest-security",
                severity="HIGH",
                title=f"{classname}::{name}",
                detail=message[:300],
                remediation="Review the failing assertion and fix the underlying vulnerability.",
            ))


# ---------------------------------------------------------------------------
# Check 4 — HTTP security headers
# ---------------------------------------------------------------------------

def check_http_security_headers(base_url: str, report: AuditReport) -> None:
    log.info("Checking HTTP security headers on %s ...", base_url)

    required: dict[str, tuple[str, str]] = {
        "Strict-Transport-Security": (
            "HIGH",
            "Add: Strict-Transport-Security: max-age=31536000; includeSubDomains",
        ),
        "X-Content-Type-Options": (
            "HIGH",
            "Add: X-Content-Type-Options: nosniff",
        ),
        "X-Frame-Options": (
            "MEDIUM",
            "Add: X-Frame-Options: DENY",
        ),
        "Content-Security-Policy": (
            "HIGH",
            "Define a strict CSP — start with default-src 'self'",
        ),
        "Referrer-Policy": (
            "LOW",
            "Add: Referrer-Policy: strict-origin-when-cross-origin",
        ),
        "Permissions-Policy": (
            "LOW",
            "Add: Permissions-Policy: geolocation=(), microphone=(), camera=()",
        ),
    }

    leaky = ["X-Powered-By", "Server", "X-AspNet-Version"]

    try:
        req = urllib.request.Request(base_url, method="GET")
        req.add_header("User-Agent", "FlavorSnap-SecurityAudit/1.0")
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            headers = {k.lower(): v for k, v in resp.headers.items()}
    except Exception as exc:
        report.skipped.append(f"http-headers — could not reach {base_url}: {exc}")
        return

    for header, (severity, remediation) in required.items():
        if header.lower() not in headers:
            report.findings.append(Finding(
                check="http-headers",
                severity=severity,
                title=f"Missing security header: {header}",
                detail=f"{base_url} did not return {header}",
                remediation=remediation,
            ))
        else:
            report.passed.append(f"http-headers — {header} present")

    for header in leaky:
        if header.lower() in headers:
            report.findings.append(Finding(
                check="http-headers",
                severity="MEDIUM",
                title=f"Information-leaking header: {header}",
                detail=f"{header}: {headers[header.lower()]!r} reveals server details",
                remediation=f"Remove or suppress the {header} header in your server config.",
            ))

    log.info("HTTP header check complete")


# ---------------------------------------------------------------------------
# Check 5 — CORS configuration
# ---------------------------------------------------------------------------

def check_cors(base_url: str, report: AuditReport) -> None:
    log.info("Checking CORS configuration ...")

    try:
        req = urllib.request.Request(f"{base_url}/api/classify", method="OPTIONS")
        req.add_header("Origin", "https://evil.com")
        req.add_header("Access-Control-Request-Method", "POST")
        req.add_header("User-Agent", "FlavorSnap-SecurityAudit/1.0")
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            acao = resp.headers.get("Access-Control-Allow-Origin", "")
            acac = resp.headers.get("Access-Control-Allow-Credentials", "").lower()
    except Exception as exc:
        report.skipped.append(f"cors — preflight probe failed: {exc}")
        return

    if acao == "*" and acac == "true":
        report.findings.append(Finding(
            check="cors",
            severity="CRITICAL",
            title="CORS: wildcard origin + credentials allowed",
            detail=(
                "Access-Control-Allow-Origin: * combined with "
                "Access-Control-Allow-Credentials: true allows any origin "
                "to make credentialed requests."
            ),
            remediation=(
                "Set Access-Control-Allow-Origin to an explicit allowlist. "
                "Never combine * with credentials."
            ),
        ))
    elif acao == "https://evil.com":
        report.findings.append(Finding(
            check="cors",
            severity="HIGH",
            title="CORS: arbitrary origin reflected",
            detail=f"Server reflected attacker-controlled origin {acao!r}",
            remediation="Validate Origin against an explicit allowlist before reflecting it.",
        ))
    else:
        report.passed.append("cors — origin not reflected or wildcard not combined with credentials")

    log.info("CORS check complete")


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
COLOURS = {
    "CRITICAL": "\033[1;31m",
    "HIGH":     "\033[31m",
    "MEDIUM":   "\033[33m",
    "LOW":      "\033[36m",
}
RESET = "\033[0m"


def _col(severity: str, text: str) -> str:
    return f"{COLOURS.get(severity, '')}{text}{RESET}"


def render_console(report: AuditReport) -> None:
    w = 70
    print("\n" + "=" * w)
    print("  FLAVORSNAP SECURITY AUDIT REPORT")
    print(f"  {report.timestamp}")
    print("=" * w)

    if report.passed:
        print(f"\n✅  PASSED ({len(report.passed)})")
        for item in report.passed:
            print(f"     {item}")

    if report.skipped:
        print(f"\n⏭️   SKIPPED ({len(report.skipped)})")
        for item in report.skipped:
            print(f"     {item}")

    if report.errors:
        print(f"\n⚠️   ERRORS ({len(report.errors)})")
        for item in report.errors:
            print(f"     {item}")

    if not report.findings:
        print("\n🎉  No security findings!\n")
    else:
        findings = sorted(
            report.findings, key=lambda f: SEVERITY_ORDER.get(f.severity, 99)
        )
        print(f"\n🔍  FINDINGS ({len(findings)})\n")
        for i, f in enumerate(findings, 1):
            print(f"  {i:>3}. {_col(f.severity, f'[{f.severity}]')}  {f.check} — {f.title}")
            print(f"        {f.detail}")
            if f.remediation:
                print(f"        💡 {f.remediation}")
            print()

    print("-" * w)
    print(
        f"  CRITICAL: {report.critical_count}  "
        f"HIGH: {report.high_count}  "
        f"MEDIUM: {report.medium_count}  "
        f"LOW: {report.low_count}"
    )
    print("=" * w + "\n")


def render_json(report: AuditReport, output_path: Path) -> None:
    data = {
        "timestamp": report.timestamp,
        "summary": {
            "critical": report.critical_count,
            "high":     report.high_count,
            "medium":   report.medium_count,
            "low":      report.low_count,
            "passed":   len(report.passed),
            "skipped":  len(report.skipped),
            "errors":   len(report.errors),
        },
        "findings": [
            {
                "check":       f.check,
                "severity":    f.severity,
                "title":       f.title,
                "detail":      f.detail,
                "remediation": f.remediation,
            }
            for f in sorted(
                report.findings,
                key=lambda f: SEVERITY_ORDER.get(f.severity, 99),
            )
        ],
        "passed":  report.passed,
        "skipped": report.skipped,
        "errors":  report.errors,
    }
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    log.info("JSON report written to %s", output_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="FlavorSnap Security Audit — Issue #226",
    )
    parser.add_argument(
        "--url",
        default=None,
        metavar="URL",
        help="Base URL of a running FlavorSnap instance for live checks "
             "(e.g. http://localhost:8000). Omit to skip header/CORS checks.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        metavar="DIR",
        help="Directory to write the JSON report (default: print to console only).",
    )
    parser.add_argument(
        "--fail-on-high",
        action="store_true",
        help="Exit with code 1 if any HIGH or CRITICAL findings are found.",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip the pytest security suite (useful for CI static-analysis only).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    report = AuditReport()

    # Always run static checks
    check_bandit(repo_root, report)
    check_safety(report)

    # pytest security suite
    if not args.skip_tests:
        check_security_tests(repo_root, report)
    else:
        report.skipped.append("pytest-security — skipped via --skip-tests")

    # Live server checks (optional)
    if args.url:
        check_http_security_headers(args.url, report)
        check_cors(args.url, report)
    else:
        report.skipped.append("http-headers — no --url provided")
        report.skipped.append("cors — no --url provided")

    # Render console report
    render_console(report)

    # Write JSON report if requested
    if args.output_dir:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        render_json(report, out_dir / f"security_audit_{ts}.json")

    # Exit code
    if args.fail_on_high and (report.critical_count + report.high_count) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
