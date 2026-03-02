"""CLI entry point for the compliance checker."""

import argparse
import sys
import os

from .rules_loader import load_rules
from .codebase_loader import load_codebase
from .analyzer import analyze


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check a codebase for dataset usage policy violations."
    )
    parser.add_argument("--rules", required=True, help="Path to the YAML rules file.")
    parser.add_argument("--codebase", required=True, help="Path to the codebase directory.")
    parser.add_argument(
        "--extensions",
        nargs="*",
        default=[".py"],
        help="File extensions to scan (default: .py).",
    )
    parser.add_argument("--api-key", default=None, help="Gemini API key (or set GEMINI_API_KEY env var).")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: Provide a Gemini API key via --api-key or GEMINI_API_KEY env var.")
        sys.exit(2)

    # 1. Load rules
    print(f"Loading rules from {args.rules} ...")
    rules = load_rules(args.rules)

    # 2. Load codebase
    print(f"Scanning codebase at {args.codebase} ...")
    codebase = load_codebase(args.codebase, args.extensions)
    print(f"  Found {len(codebase)} file(s).")

    if not codebase:
        print("No files found. Check the path and extensions.")
        sys.exit(2)

    # 3. Analyze
    print("Sending to Gemini for analysis ...")
    report = analyze(rules, codebase, api_key)

    # 4. Print report
    print("\n" + "=" * 60)
    if report.is_compliant:
        print("✅  COMPLIANT — No violations found.")
    else:
        print(f"❌  NON-COMPLIANT — {len(report.violations)} violation(s) found.\n")
        for i, v in enumerate(report.violations, 1):
            print(f"  [{i}] {v.severity.upper()} — {v.violated_rule}")
            print(f"      File: {v.file}  (lines {v.line_range})")
            print(f"      Snippet: {v.code_snippet}")
            print(f"      Explanation: {v.explanation}")
            print()

    print(f"Summary: {report.summary}")
    print("=" * 60)

    sys.exit(0 if report.is_compliant else 1)


if __name__ == "__main__":
    main()
