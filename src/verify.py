"""Adversarial verify pass.

Every finding from the review loop gets a second pass whose job is to
refute it: is this a real instance of the policy rule, or a false
positive (a test fixture, a placeholder, a check that moved elsewhere)?
Findings that do not survive are dropped before the verdict is built,
which is what keeps the blocking status trustworthy.
"""

from __future__ import annotations


def verify_findings(findings, files_by_path, client, ledger) -> list:
    """Run the verify pass. Returns the surviving findings, annotated."""
    survivors = []
    for finding in findings:
        file_diff = files_by_path.get(finding.file)
        survives, note, usage = client.verify_finding(finding, file_diff)
        ledger.record_call(
            stage="verify",
            model=client.name,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            mock=client.mock,
            note="verify %s in %s" % (finding.rule_id, finding.file),
        )
        if survives:
            finding.verified = True
            finding.verify_note = note
            survivors.append(finding)
    return survivors
