"""The Ember review loop.

One interface, two clients:

- MockEmberClient returns recorded (canned) responses keyed to the
  bundled sample diffs, so the full pipeline runs end to end with $0
  spend. This is the default path for development and tests.
- LiveEmberClient is the seam for the real Muse Ember client (Meta Model
  API). It is deliberately not wired to the network yet: no API key
  exists until calibration day, and live calls must never happen by
  accident. It lands behind this same interface on day 3 of the plan.

A client returns (findings, usage) where usage is a dict with
input_tokens and output_tokens, which the caller records in the ledger.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from . import ledger as ledger_mod

MODEL_NAME = "muse-ember"


@dataclass
class Finding:
    rule_id: str
    category: str
    severity: str          # "blocking" or "advisory"
    file: str
    title: str
    explanation: str       # plain English, written for the PR author
    evidence: str = ""     # the diff line(s) that triggered the finding
    verified: bool = False
    verify_note: str = ""

    @property
    def is_blocking(self) -> bool:
        return self.severity == "blocking"


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


# ---------------------------------------------------------------------------
# Mock client: canned responses keyed to the bundled sample diffs.
#
# Each scenario is keyed by a marker that appears in its sample diff. The
# findings below are the recorded responses for demo/sample-diffs/; they
# are what a calibrated live run is expected to reproduce.
# ---------------------------------------------------------------------------

_MOCK_SCENARIOS = [
    {
        # demo/sample-diffs/02-hardcoded-secret.diff
        "marker": "sk_live_",
        "finding": {
            "rule_id": "hardcoded-secrets",
            "category": "Hardcoded secrets",
            "severity": "blocking",
            "title": "Live API key committed in source code",
            "explanation": (
                "This change adds a live payment API key written directly "
                "in the source code. Anyone who can read this repository "
                "can copy the key and use it, and the key stays in the git "
                "history even after the line is removed. Move the key into "
                "an environment variable or a secrets manager, and rotate "
                "the exposed key, because it has to be treated as leaked."
            ),
            "evidence": "STRIPE_API_KEY assigned a live-format API key (added line 7)",
        },
        "verify_survives": True,
        "verify_note": (
            "Confirmed: the added line is a live-format API key assigned "
            "to a constant, not a placeholder or a test fixture."
        ),
    },
    {
        # demo/sample-diffs/03-removed-auth-check.diff
        "marker": "require_auth",
        "removed_only": True,
        "finding": {
            "rule_id": "missing-auth",
            "category": "Missing authentication checks",
            "severity": "blocking",
            "title": "Login check removed from the account settings endpoint",
            "explanation": (
                "This change removes the login check from the account "
                "settings endpoint. Without it, anyone on the internet "
                "can open that page and view or change account details "
                "without signing in first. Put the check back, or replace "
                "it with an equivalent one, before this is merged."
            ),
            "evidence": "-@require_auth",
        },
        "verify_survives": True,
        "verify_note": (
            "Confirmed: the removed line is the only authentication "
            "decorator on the endpoint, and no replacement check is "
            "added anywhere in the diff."
        ),
    },
]


class MockEmberClient:
    """Recorded responses for the bundled sample diffs. Zero API spend."""

    name = MODEL_NAME
    mock = True

    def _usage_for(self, text: str, findings: list) -> Usage:
        # Deterministic pseudo token counts so the ledger has something
        # realistic to display in mock mode. Cost is still recorded as $0.
        return Usage(
            input_tokens=max(1, len(text) // 4),
            output_tokens=120 + 90 * len(findings),
        )

    def review_file(self, file_diff, policy):
        """Return canned findings for one file's diff."""
        added = file_diff.added_text()
        removed = file_diff.removed_text()
        findings = []
        for scenario in _MOCK_SCENARIOS:
            marker = scenario["marker"]
            if scenario.get("removed_only"):
                hit = marker in removed
            else:
                hit = marker in added
            if not hit:
                continue
            spec = dict(scenario["finding"])
            rule = policy.rule(spec["rule_id"])
            if rule is not None:
                spec["severity"] = rule.severity
                spec["category"] = rule.category
            findings.append(Finding(file=file_diff.path, **spec))
        return findings, self._usage_for(file_diff.render(), findings)

    def verify_finding(self, finding, file_diff):
        """Recorded verify outcomes for the canned scenarios."""
        for scenario in _MOCK_SCENARIOS:
            if scenario["finding"]["rule_id"] == finding.rule_id:
                usage = Usage(input_tokens=180, output_tokens=60)
                return scenario["verify_survives"], scenario["verify_note"], usage
        # Unknown findings do not survive a verify pass they were never
        # recorded for; live mode replaces this with a real refutation.
        return False, "No recorded verify response for this finding.", Usage(
            input_tokens=180, output_tokens=60
        )


class LiveEmberClient:
    """Real Muse Ember client. Not wired yet, on purpose.

    The hackathon API key does not exist until calibration day, and the
    plan forbids accidental live spend during development. This class
    exists so review.py, verify.py, and main.py are written against the
    final interface; the network implementation lands on day 3.
    """

    name = MODEL_NAME
    mock = False

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("META_MODEL_API_KEY", "")

    def review_file(self, file_diff, policy):
        raise NotImplementedError(
            "Live Ember client is not wired yet (day 3 of the build plan). "
            "Run with EMBERGUARD_MOCK=1 to use recorded responses."
        )

    def verify_finding(self, finding, file_diff):
        raise NotImplementedError(
            "Live Ember client is not wired yet (day 3 of the build plan). "
            "Run with EMBERGUARD_MOCK=1 to use recorded responses."
        )


def mock_mode_enabled() -> bool:
    """Mock mode is on when EMBERGUARD_MOCK=1, or when no API key exists."""
    flag = os.environ.get("EMBERGUARD_MOCK", "").strip()
    if flag == "1":
        return True
    if flag == "0":
        return False
    return not os.environ.get("META_MODEL_API_KEY")


def get_client():
    if mock_mode_enabled():
        return MockEmberClient()
    return LiveEmberClient()


def build_review_prompt(file_diff, policy) -> str:
    """The prompt a live run sends for one file. Built in mock mode too,
    so prompt shape is testable without spending credits."""
    return (
        "You are a security reviewer for a pull request. Review the diff "
        "for one file against this policy pack:\n\n%s\n\n"
        "File: %s\n\nDiff:\n%s\n\n"
        "Report only findings that match a policy rule. For each finding "
        "give the rule id, a short title, and a plain-English explanation "
        "a developer without a security background can act on."
        % (policy.prompt_text(), file_diff.path, file_diff.render())
    )


def review_pr(files, policy, client, ledger) -> list:
    """Review every kept file and record each call in the ledger."""
    findings = []
    for file_diff in files:
        _prompt = build_review_prompt(file_diff, policy)  # shape parity
        file_findings, usage = client.review_file(file_diff, policy)
        ledger.record_call(
            stage="review",
            model=client.name,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            mock=client.mock,
            note="review %s" % file_diff.path,
        )
        findings.extend(file_findings)
    return findings
