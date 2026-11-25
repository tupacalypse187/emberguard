"""Policy pack loading tests."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import policy as policy_mod  # noqa: E402


class TestDefaultPack(unittest.TestCase):
    def setUp(self):
        self.pack = policy_mod.load_policy(repo_root="/nonexistent-repo")

    def test_default_pack_loads_six_rules(self):
        ids = {r.rule_id for r in self.pack.rules}
        self.assertEqual(
            ids,
            {
                "hardcoded-secrets",
                "injection",
                "missing-auth",
                "unsafe-deserialization",
                "disabled-tls-verification",
                "broad-permissions",
            },
        )

    def test_severities(self):
        self.assertEqual(self.pack.rule("hardcoded-secrets").severity, "blocking")
        self.assertEqual(self.pack.rule("missing-auth").severity, "blocking")
        self.assertEqual(self.pack.rule("broad-permissions").severity, "advisory")
        self.assertEqual(len(self.pack.blocking_rules()), 5)
        self.assertEqual(len(self.pack.advisory_rules()), 1)


class TestRepoPackOverride(unittest.TestCase):
    def test_repo_policy_md_wins_over_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack_dir = os.path.join(tmp, ".emberguard")
            os.makedirs(pack_dir)
            with open(os.path.join(pack_dir, "policy.md"), "w",
                      encoding="utf-8") as fh:
                fh.write(
                    "# Custom pack\n\n"
                    "## Rule: no-todo-comments\n"
                    "- Severity: advisory\n"
                    "- Category: TODO comments\n"
                    "- Patterns: TODO\n"
                    "- Guidance: TODO comments must link an issue.\n"
                )
            pack = policy_mod.load_policy(repo_root=tmp)
            self.assertEqual([r.rule_id for r in pack.rules], ["no-todo-comments"])
            self.assertIn(".emberguard", pack.source)


if __name__ == "__main__":
    unittest.main()
