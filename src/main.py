"""EmberGuard entry point: PR diff in, verdict out.

Local and mock usage:

    EMBERGUARD_MOCK=1 python3 -m src.main --diff demo/sample-diffs/01-clean.diff

In the GitHub Action, the workflow produces the PR diff with `gh pr diff`
and calls this module the same way. Posting the comment and commit
status happens only when EMBERGUARD_POST=1 and a GITHUB_TOKEN is
present; mock mode never posts.

Exit code: 1 only in enforce mode when the verdict fails. Observe mode
(the default) always exits 0.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import diff as diff_mod
from . import ledger as ledger_mod
from . import policy as policy_mod
from . import review as review_mod
from . import verdict as verdict_mod
from . import verify as verify_mod


def run(diff_text: str, repo_root: str = ".", policy_path: str = None,
        mode: str = verdict_mod.MODE_OBSERVE, budget_usd: float = None,
        client=None) -> dict:
    """Run the full pipeline on diff text. Returns a result dict."""
    pack = policy_mod.load_policy(repo_root=repo_root, policy_path=policy_path)
    files, skipped = diff_mod.prepare_diff(diff_text)
    budget = budget_usd
    if budget is None:
        budget = float(os.environ.get("EMBERGUARD_BUDGET_USD",
                                      ledger_mod.DEFAULT_BUDGET_USD))
    ledger = ledger_mod.Ledger(budget_usd=budget)
    client = client or review_mod.get_client()

    findings = review_mod.review_pr(files, pack, client, ledger)
    files_by_path = {f.path: f for f in files}
    survivors = verify_mod.verify_findings(findings, files_by_path, client, ledger)

    result_verdict = verdict_mod.build_verdict(
        survivors, files_reviewed=len(files), files_skipped=skipped
    )
    comment = verdict_mod.format_comment(result_verdict, ledger, mode, pack.source)
    return {
        "verdict": result_verdict,
        "comment": comment,
        "ledger": ledger,
        "policy_source": pack.source,
        "mode": mode,
        "mock": client.mock,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="emberguard",
                                     description="EmberGuard PR security review")
    parser.add_argument("--diff", required=True,
                        help="Path to a unified diff file for the pull request")
    parser.add_argument("--repo-root", default=".",
                        help="Target repo root (for .emberguard/policy.md)")
    parser.add_argument("--policy", default=None,
                        help="Explicit policy pack path (overrides repo pack)")
    parser.add_argument("--mode", choices=[verdict_mod.MODE_OBSERVE,
                                           verdict_mod.MODE_ENFORCE],
                        default=os.environ.get("EMBERGUARD_MODE",
                                               verdict_mod.MODE_OBSERVE))
    parser.add_argument("--budget-usd", type=float, default=None,
                        help="Budget cap in USD (default: $10.00)")
    parser.add_argument("--ledger-out", default=None,
                        help="Write the cost ledger JSON to this path")
    args = parser.parse_args(argv)

    with open(args.diff, "r", encoding="utf-8") as fh:
        diff_text = fh.read()

    result = run(
        diff_text,
        repo_root=args.repo_root,
        policy_path=args.policy,
        mode=args.mode,
        budget_usd=args.budget_usd,
    )

    comment = result["comment"]
    print(comment)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write(comment + "\n")

    if args.ledger_out:
        result["ledger"].save(args.ledger_out)

    if os.environ.get("EMBERGUARD_POST") == "1":
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        pr_number = int(os.environ.get("EMBERGUARD_PR_NUMBER", "0") or 0)
        sha = os.environ.get("EMBERGUARD_PR_SHA", "")
        posted = verdict_mod.post_to_github(
            repo, pr_number, sha, comment, result["verdict"], args.mode,
            dry_run=result["mock"],
        )
        print(json.dumps({"post_result": posted}, indent=2), file=sys.stderr)

    if args.mode == verdict_mod.MODE_ENFORCE and not result["verdict"].passed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
