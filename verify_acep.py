import sys
import os
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from compliance_checker.models import UsageRules, DatasetInfo
from audit import analyze_advanced

def mock_progress(progress, message):
    print(f"[PROGRESS] {progress}% - {message}")

def run_verify():
    # 1. Create mock rules
    rules = UsageRules(
        dataset=DatasetInfo(name="TestDataset", description="Test only"),
        allowed_uses=["Education"],
        barred_uses=["Commercial"]
    )
    
    # 2. Create mock codebase
    codebase = {
        "test.py": "print('hello world')\n# This is a commercial product"
    }
    
    # 3. Check imports and logic (will fail without API key, but we check signature)
    print("Verifying analyze_advanced signature and imports...")
    try:
        # We pass a fake API key just to see if the function starts correctly (initialization)
        # It will likely fail at the LLM step, but we check if it reaches that far.
        analyze_advanced(
            rules=rules,
            codebase=codebase,
            api_key="sk-fake-key",
            repo_id="test_repo",
            embed_model="jina",
            use_hyde=False,
            progress_callback=mock_progress
        )
    except Exception as e:
        print(f"Caught expected/unexpected error: {e}")

if __name__ == "__main__":
    run_verify()
