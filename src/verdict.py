"""Verdict construction, PR comment formatting, and GitHub posting.

A verdict fails only when at least one blocking finding survives the
verify pass. Advisory findings are reported in the comment but never
fail anything.

Modes:
- observe (default): comment only in spirit; the commit status is set to
  success with an "observe mode" description so nothing is ever blocked
  while a repo builds trust.
- enforce: the commit status is failure when the verdict fails, which is
  what branch protection gates on.

Posting uses the GitHub API over HTTPS with the stdlib only. In mock
mode, or without a token, posting is a dry run that returns the payload
it would have sent. No network call happens in mock mode.
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass, field

MODE_OBSERVE = "observe"
MODE_ENFORCE = "enforce"


@dataclass
class Verdict:
    passed: bool
    findings: list = field(default_factory=list)   # surviving findings
    files_reviewed: int = 0
    files_skipped: list = field(default_factory=list)

    @property
    def blocking(self) -> list:
        return [f for f in self.findings if f.is_blocking]

    @property
    def advisory(self) -> list:
        return [f for f in self.findings if not f.is_blocking]


def build_verdict(findings, files_reviewed: int, files_skipped: list) -> Verdict:
    passed = not any(f.is_blocking for f in findings)
    return Verdict(
        passed=passed,
        findings=findings,
        files_reviewed=files_reviewed,
        files_skipped=files_skipped,
    )


def status_state(verdict: Verdict, mode: str) -> str:
    """Commit status state for this verdict under the given mode."""
    if mode == MODE_OBSERVE:
        return "success"
    return "success" if verdict.passed else "failure"


def status_description(verdict: Verdict, mode: str) -> str:
    if mode == MODE_OBSERVE:
        return "EmberGuard observe mode: %d finding(s), nothing blocked" % len(
            verdict.findings
        )
    if verdict.passed:
        return "EmberGuard: policy check passed"
    return "EmberGuard: %d blocking finding(s)" % len(verdict.blocking)


def format_comment(verdict: Verdict, ledger, mode: str, policy_source: str) -> str:
    """Render the PR summary comment as markdown."""
    lines = []
    if verdict.passed:
        lines.append("## ✅ EmberGuard review: PASS")
    else:
        lines.append("## ❌ EmberGuard review: FAIL")
    lines.append("")
    lines.append(
        "Reviewed %d file(s) against the policy pack (`%s`)."
        % (verdict.files_reviewed, policy_source)
    )
    if verdict.files_skipped:
        lines.append(
            "Skipped %d file(s) (lock files, vendored, generated, or binary): %s"
            % (len(verdict.files_skipped), ", ".join(verdict.files_skipped))
        )
    lines.append("")
    if verdict.blocking:
        lines.append("### 🚫 Blocking findings")
        lines.append("")
        lines.append("| Rule | File | Finding |")
        lines.append("|---|---|---|")
        for f in verdict.blocking:
            lines.append("| %s | `%s` | %s |" % (f.rule_id, f.file, f.title))
        lines.append("")
        for f in verdict.blocking:
            lines.append("**%s** (`%s`)" % (f.title, f.file))
            lines.append("")
            lines.append(f.explanation)
            if f.evidence:
                lines.append("")
                lines.append("Evidence: `%s`" % f.evidence)
            lines.append("")
    if verdict.advisory:
        lines.append("### 💡 Advisory findings (do not block)")
        lines.append("")
        for f in verdict.advisory:
            lines.append("- **%s** in `%s`: %s" % (f.title, f.file, f.explanation))
        lines.append("")
    if not verdict.findings:
        lines.append("No policy findings. Nice and clean.")
        lines.append("")
    lines.append("---")
    lines.append(ledger.cost_line())
    if mode == MODE_OBSERVE:
        lines.append(
            "Running in observe mode: this verdict is advisory and does "
            "not block merging."
        )
    lines.append("")
    lines.append("Reviewed by EmberGuard on Muse Ember.")
    return "\n".join(lines)


def _github_request(method: str, url: str, token: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer %s" % token)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as resp:  # pragma: no cover, network
        return json.loads(resp.read().decode("utf-8"))


def post_to_github(repo: str, pr_number: int, sha: str, comment_body: str,
                   verdict: Verdict, mode: str, token: str = None,
                   dry_run: bool = False) -> dict:
    """Post the summary comment and the commit status.

    Returns a dict describing what was (or would be) sent. When dry_run
    is set, or no token is available, nothing touches the network.
    """
    token = token or os.environ.get("GITHUB_TOKEN", "")
    result = {
        "comment": {
            "repo": repo,
            "pr": pr_number,
            "body": comment_body,
            "posted": False,
        },
        "status": {
            "repo": repo,
            "sha": sha,
            "state": status_state(verdict, mode),
            "description": status_description(verdict, mode),
            "context": "emberguard",
            "posted": False,
        },
    }
    if dry_run or not token:
        result["dry_run"] = True
        return result
    api = "https://api.github.com/repos/%s" % repo
    _github_request(
        "POST",
        "%s/issues/%d/comments" % (api, pr_number),
        token,
        {"body": comment_body},
    )
    result["comment"]["posted"] = True
    _github_request(
        "POST",
        "%s/statuses/%s" % (api, sha),
        token,
        {
            "state": result["status"]["state"],
            "description": result["status"]["description"],
            "context": "emberguard",
        },
    )
    result["status"]["posted"] = True
    return result
