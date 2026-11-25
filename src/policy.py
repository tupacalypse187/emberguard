"""Policy pack loading and severity rules.

A policy pack is a single markdown file. A repo can carry its own pack at
`.emberguard/policy.md`; when it does not, EmberGuard falls back to the
bundled default security pack in `policies/default-security.md`.

Pack format (one section per rule):

    ## Rule: hardcoded-secrets
    - Severity: blocking
    - Category: Hardcoded secrets
    - Patterns: api_key, secret, token
    - Guidance: free text explaining the rule for the model

Severity is either "blocking" (fails the commit status) or "advisory"
(comment only). Only blocking findings can fail a review.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

SEVERITY_BLOCKING = "blocking"
SEVERITY_ADVISORY = "advisory"

_REPO_POLICY_PATH = os.path.join(".emberguard", "policy.md")


@dataclass
class Rule:
    rule_id: str
    category: str
    severity: str
    patterns: list = field(default_factory=list)
    guidance: str = ""

    @property
    def is_blocking(self) -> bool:
        return self.severity == SEVERITY_BLOCKING


@dataclass
class PolicyPack:
    rules: list
    source: str

    def rule(self, rule_id: str):
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        return None

    def blocking_rules(self) -> list:
        return [r for r in self.rules if r.is_blocking]

    def advisory_rules(self) -> list:
        return [r for r in self.rules if not r.is_blocking]

    def prompt_text(self) -> str:
        """Render the pack as instructions for the review prompt."""
        lines = []
        for rule in self.rules:
            lines.append(
                "- [%s] %s (%s): %s"
                % (rule.severity.upper(), rule.category, rule.rule_id, rule.guidance)
            )
        return "\n".join(lines)


def parse_policy_markdown(text: str, source: str) -> PolicyPack:
    """Parse a policy pack markdown file into a PolicyPack."""
    rules = []
    current = None
    guidance_lines = []

    def flush():
        if current is not None:
            current.guidance = " ".join(guidance_lines).strip()
            rules.append(current)

    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("## Rule:"):
            flush()
            rule_id = line[len("## Rule:"):].strip()
            current = Rule(rule_id=rule_id, category=rule_id, severity=SEVERITY_ADVISORY)
            guidance_lines = []
            continue
        if current is None:
            continue
        if line.startswith("- Severity:"):
            value = line.split(":", 1)[1].strip().lower()
            current.severity = (
                SEVERITY_BLOCKING if value == SEVERITY_BLOCKING else SEVERITY_ADVISORY
            )
        elif line.startswith("- Category:"):
            current.category = line.split(":", 1)[1].strip()
        elif line.startswith("- Patterns:"):
            current.patterns = [
                p.strip() for p in line.split(":", 1)[1].split(",") if p.strip()
            ]
        elif line.startswith("- Guidance:"):
            guidance_lines.append(line.split(":", 1)[1].strip())
        elif line and not line.startswith("#"):
            guidance_lines.append(line)
    flush()
    return PolicyPack(rules=rules, source=source)


def bundled_default_path() -> str:
    """Absolute path to the bundled default security pack."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(repo_root, "policies", "default-security.md")


def load_policy(repo_root: str = None, policy_path: str = None) -> PolicyPack:
    """Load the effective policy pack.

    Precedence: explicit policy_path, then <repo_root>/.emberguard/policy.md
    (or ./.emberguard/policy.md), then the bundled default pack.
    """
    candidates = []
    if policy_path:
        candidates.append(policy_path)
    if repo_root:
        candidates.append(os.path.join(repo_root, _REPO_POLICY_PATH))
    candidates.append(_REPO_POLICY_PATH)
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            with open(candidate, "r", encoding="utf-8") as fh:
                return parse_policy_markdown(fh.read(), source=candidate)
    default = bundled_default_path()
    with open(default, "r", encoding="utf-8") as fh:
        return parse_policy_markdown(
            fh.read(), source="policies/default-security.md (bundled default)"
        )
