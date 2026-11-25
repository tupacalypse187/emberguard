"""End-to-end mock pipeline tests over the three seeded sample diffs."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["EMBERGUARD_MOCK"] = "1"

from src import main as main_mod  # noqa: E402

SAMPLE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "demo",
    "sample-diffs",
)


def load_sample(name):
    with open(os.path.join(SAMPLE_DIR, name), "r", encoding="utf-8") as fh:
        return fh.read()


class TestMockPipeline(unittest.TestCase):
    def run_sample(self, name):
        return main_mod.run(load_sample(name), repo_root=".")

    def test_clean_change_passes(self):
        result = self.run_sample("01-clean.diff")
        verdict = result["verdict"]
        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.findings, [])
        self.assertEqual(verdict.files_reviewed, 2)
        self.assertIn("PASS", result["comment"])

    def test_hardcoded_secret_fails_and_blocks(self):
        result = self.run_sample("02-hardcoded-secret.diff")
        verdict = result["verdict"]
        self.assertFalse(verdict.passed)
        self.assertEqual(len(verdict.blocking), 1)
        finding = verdict.blocking[0]
        self.assertEqual(finding.rule_id, "hardcoded-secrets")
        self.assertTrue(finding.verified)
        self.assertIn("FAIL", result["comment"])

    def test_removed_auth_check_fails_with_plain_english(self):
        result = self.run_sample("03-removed-auth-check.diff")
        verdict = result["verdict"]
        self.assertFalse(verdict.passed)
        self.assertEqual(len(verdict.blocking), 1)
        finding = verdict.blocking[0]
        self.assertEqual(finding.rule_id, "missing-auth")
        self.assertTrue(finding.verified)
        # The explanation has to be actionable by a non-security reader.
        self.assertIn("anyone on the internet", finding.explanation)
        self.assertIn("Put the check back", finding.explanation)

    def test_mock_mode_costs_zero(self):
        result = self.run_sample("02-hardcoded-secret.diff")
        ledger = result["ledger"]
        self.assertTrue(all(r.mock for r in ledger.records))
        self.assertEqual(ledger.total_cost_usd, 0.0)
        self.assertIn("$0.00", result["comment"])

    def test_comment_carries_cost_line(self):
        result = self.run_sample("01-clean.diff")
        self.assertIn("Cost of this review:", result["comment"])
        self.assertIn("$10.00 budget", result["comment"])


if __name__ == "__main__":
    unittest.main()
