"""Load and validate a YAML rules file into UsageRules."""

from pathlib import Path
import yaml
from .models import UsageRules


def load_rules(path: str) -> UsageRules:
    """Read a YAML file and return a validated UsageRules object."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return UsageRules(**raw)
