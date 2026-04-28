import os
import subprocess
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContainerSecurity:
    def __init__(self, image_name):
        self.image_name = image_name

    def run_vulnerability_scan(self):
        """Runs Trivy scan and returns the results."""
        logger.info(f"Scanning image {self.image_name} for vulnerabilities...")
        try:
            result = subprocess.run(
                ["trivy", "image", "-f", "json", self.image_name],
                capture_output=True,
                text=True,
                check=True
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            logger.error(f"Scan failed: {e}")
            return None
        except FileNotFoundError:
            logger.error("Trivy not found in path.")
            return None

    def check_runtime_compliance(self):
        """Checks if the current process is running as root."""
        is_root = os.getuid() == 0
        return {
            "is_root": is_root,
            "compliant": not is_root,
            "message": "Process is running as root!" if is_root else "Process is running as non-root."
        }

    def get_security_report(self):
        """Generates a comprehensive security report."""
        scan_results = self.run_vulnerability_scan()
        runtime_status = self.check_runtime_compliance()
        
        report = {
            "image": self.image_name,
            "runtime_compliance": runtime_status,
            "vulnerabilities": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            }
        }

        if scan_results and "Results" in scan_results:
            for result in scan_results["Results"]:
                if "Vulnerabilities" in result:
                    for vuln in result["Vulnerabilities"]:
                        severity = vuln["Severity"].lower()
                        if severity in report["vulnerabilities"]:
                            report["vulnerabilities"][severity] += 1

        return report

if __name__ == "__main__":
    security = ContainerSecurity("flavorsnap-api:latest")
    print(json.dumps(security.get_security_report(), indent=2))
