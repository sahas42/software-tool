from src.compliance_checker.analyzer import (_extract_relevance_terms,
    _filter_relevant_txt_files,
    _build_user_prompt,
)
from src.compliance_checker.models import DatasetInfo, UsageRules


def make_rules():
    return UsageRules(
        dataset=DatasetInfo(
            name="Cats Dataset",
            source="local",
            license="CC-BY",
            description="Images of cats for research",
        ),
        allowed_uses=["academic research", "non-commercial use"],
        barred_uses=["commercial resale", "privacy violations"],
    )


def test_extract_relevance_terms_includes_keywords():
    rules = make_rules()
    terms = _extract_relevance_terms(rules)
    assert "cats" in terms
    assert "research" in terms


def test_filter_relevant_txt_files_filters_irrelevant():
    rules = make_rules()
    codebase = {
        "README.txt": "This project includes cat images and labels.",
        "notes.txt": "Shopping list: eggs, milk, flour.",
        "code.py": "print('hello world')",
    }
    filtered = _filter_relevant_txt_files(codebase, rules)
    assert "README.txt" in filtered
    assert "notes.txt" not in filtered


def test_build_user_prompt_skips_irrelevant_txt():
    rules = make_rules()
    codebase = {
        "README.txt": "This dataset contains cat photos for AI training.",
        "random.txt": "Does not match anything relevant.",
        "main.py": "print('cat classification')",
    }
    prompt = _build_user_prompt(rules, codebase)
    assert "README.txt" in prompt
    assert "random.txt" not in prompt
    assert "main.py" in prompt
