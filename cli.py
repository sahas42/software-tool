#!/usr/bin/env python3
import os
import argparse
import time
import requests
import json

API_URL = os.environ.get("ACEP_API_URL", "http://localhost:5001")

def main():
    parser = argparse.ArgumentParser(description="ACEP Compliance CLI")
    parser.add_argument("--repo-url", type=str, help="GitHub repository URL")
    parser.add_argument("--rules-file", type=str, required=True, help="Path to rules file (.yaml or .pdf)")
    parser.add_argument("--pipeline", choices=["vanilla", "advanced"], default="advanced", help="Pipeline type")
    parser.add_argument("--embed-model", choices=["jina", "bge"], default="bge", help="Embedding model (for advanced)")
    parser.add_argument("--api-key", type=str, help="Gemini API Key (or set GEMINI_API_KEY env var)")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: Gemini API Key is required. Pass --api-key or set GEMINI_API_KEY environment variable.")
        return

    # Prepare files and data
    files = {}
    data = {
        "api_key": api_key,
        "pipeline_type": args.pipeline,
        "embed_model": args.embed_model,
        "extensions": ".py,.js,.ts,.java,.cpp,.c,.go,.rb,.rs"
    }

    if args.repo_url:
        data["codebase_type"] = "github"
        data["codebase_url"] = args.repo_url
    else:
        print("Error: --repo-url must be provided for CLI scanning at this time.")
        return

    try:
        with open(args.rules_file, "rb") as f:
            files["rules_file"] = (os.path.basename(args.rules_file), f.read())
    except FileNotFoundError:
        print(f"Error: Rules file not found at '{args.rules_file}'")
        return

    print(f"Submitting audit for {args.repo_url}...")
    
    try:
        res = requests.post(f"{API_URL}/api/analyze", data=data, files=files)
        res.raise_for_status()
        response_data = res.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to submit task: {e}")
        if e.response is not None:
            print(e.response.text)
        return

    task_id = response_data.get("task_id")
    if not task_id:
        print("Audit completed synchronously:")
        print(json.dumps(response_data, indent=2))
        return

    print(f"Task submitted successfully! Task ID: {task_id}")
    print("Polling for progress...")

    while True:
        try:
            status_res = requests.get(f"{API_URL}/api/tasks/{task_id}")
            status_res.raise_for_status()
            status_data = status_res.json()
            
            state = status_data.get("status")
            if state == "SUCCESS":
                print("\n=== Audit Completed ===")
                result = status_data.get("result", {})
                is_compliant = result.get("is_compliant", False)
                print(f"Status: {'COMPLIANT' if is_compliant else 'VIOLATIONS FOUND'}")
                print(f"Summary: {result.get('summary', '')}")
                violations = result.get("violations", [])
                print(f"Total Violations: {len(violations)}")
                for v in violations:
                    print(f"- [{v.get('severity', 'high').upper()}] {v.get('file', '')}: {v.get('violated_rule', '')}")
                break
            elif state in ["FAILURE", "REVOKED"]:
                print(f"\nTask ended with state: {state}")
                break
            else:
                print(".", end="", flush=True)
                time.sleep(2)
        except Exception as e:
            print(f"\nError polling status: {e}")
            break

if __name__ == "__main__":
    main()
