import os
from dotenv import load_dotenv
from src.compliance_checker.models import UsageRules, DatasetInfo
from src.audit import analyze_advanced

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

rules = UsageRules(
    dataset=DatasetInfo(name="Test Dataset", description="Mock dataset for testing"),
    allowed_uses=["Academic research"],
    barred_uses=["Training models for commercial purposes"]
)

mock_codebase = {
    "train.py": "def train_model():\n    # This model will be sold\n    print('Training for commercial product...')\n    model.fit(dataset='test_dataset')",
    "utils.py": "def hello():\n    return 'world'"
}

print("Running with HyDE enabled:")
analyze_advanced(rules, mock_codebase, api_key, use_hyde=True)

print("\n-----------------------\n")

print("Running with HyDE disabled:")
analyze_advanced(rules, mock_codebase, api_key, use_hyde=False)
