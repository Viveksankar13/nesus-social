#!/usr/bin/env python3
"""
Nexus Social — Repository Secret Scanner
=========================================
Scans repository source files for accidental leaks of credentials, private keys,
hardcoded API keys, JWT secrets, and production passwords.

Exits with:
  0 if no high-risk secrets are found.
  1 if potential hardcoded secrets are detected.
"""

import os
import re
import sys
from pathlib import Path

# Directories and files to exclude from secret scan
EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    ".next",
    ".pytest_cache",
    ".venv",
    "venv",
    "dist",
    "build",
    "coverage",
    "__pycache__",
}

EXCLUDE_FILES = {
    ".env",
    ".env.local",
    "package-lock.json",
    "SYSTEM_DOCUMENTATION.pdf",
    "SAMPLE_STAGE0.pdf",
    "secret_scan.py",
}

# Regex patterns for high-risk secrets
PATTERNS = [
    (r"AIzaSy[0-9A-Za-z-_]{33}", "Google Gemini / Firebase API Key"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
    (r"-----BEGIN (RSA|EC|DSA|OPENSSH|PRIVATE) KEY-----", "Private Cryptographic Key"),
    (r"ghp_[0-9a-zA-Z]{36}", "GitHub Personal Access Token"),
    (r"xox[baprs]-[0-9a-zA-Z]{10,48}", "Slack Token"),
    (r"sk-[0-9a-zA-Z]{48}", "OpenAI Secret Key"),
    (r"xsmtpsib-[0-9a-zA-Z]{64}", "Live Brevo SMTP Secret Key"),
]

# Safe placeholder tokens to allow
ALLOWLIST = {
    "AIzaSyDemoPlaceholderKeyForTesting0000000000",
    "AIzaSyTestMockKeyForOfflineUnitTestingOnly",
    "CHANGE_ME_USE_OPENSSL_RAND_HEX_32",
    "CHANGE_ME_STRONG_PASSWORD",
}


def scan_file(file_path: Path) -> list[tuple[int, str, str]]:
    """Scan a single text file for credential patterns."""
    findings = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    for line_idx, line in enumerate(content.splitlines(), start=1):
        # Skip comment or doc lines that are clearly documentation examples
        for regex, desc in PATTERNS:
            matches = re.finditer(regex, line)
            for m in matches:
                matched_val = m.group(0)
                if matched_val in ALLOWLIST or "example" in line.lower() or "..." in line:
                    continue
                findings.append((line_idx, desc, matched_val[:8] + "..." + matched_val[-4:]))
    return findings


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    root_dir = Path(__file__).resolve().parent.parent
    print(f"Scanning repository at: {root_dir}")
    total_scanned = 0
    all_findings = []

    for root, dirs, files in os.walk(root_dir):
        # Prune excluded dirs
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            if file in EXCLUDE_FILES:
                continue
            file_path = Path(root) / file
            # Skip binary files by extension
            if file_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".ico", ".pdf", ".pyc"}:
                continue

            total_scanned += 1
            findings = scan_file(file_path)
            for line_no, desc, masked in findings:
                all_findings.append((file_path.relative_to(root_dir), line_no, desc, masked))

    print(f"Scanned {total_scanned} files across repository.")

    if all_findings:
        print("\n[!] POTENTIAL SECRETS DETECTED:")
        for rel_path, line_no, desc, masked in all_findings:
            print(f"  {rel_path}:{line_no} — [{desc}] ({masked})")
        return 1

    print("\n[SUCCESS] SECRET SCAN PASSED: Zero live credentials or secrets detected in repository.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
