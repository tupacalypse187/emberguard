"""Cost ledger tests, including the hard budget cap."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import ledger as ledger_mod  # noqa: E402


class TestLedger(unittest.TestCase):
    def test_mock_calls_cost_zero(self):
        ledger = ledger_mod.Ledger(budget_usd=10.0)
        ledger.record_call("review", "muse-ember", 5000, 2000, mock=True)
        self.assertEqual(ledger.total_cost_usd, 0.0)
        self.assertEqual(ledger.total_tokens, 7000)

    def test_live_calls_accumulate(self):
        ledger = ledger_mod.Ledger(budget_usd=10.0)
        ledger.record_call("review", "muse-ember", 1000, 500, mock=False)
        expected = ledger_mod.estimate_cost_usd(1000, 500)
        self.assertAlmostEqual(ledger.total_cost_usd, expected)
        self.assertAlmostEqual(ledger.remaining_usd, 10.0 - expected)

    def test_budget_cap_hard_stops(self):
        ledger = ledger_mod.Ledger(budget_usd=0.001)
        with self.assertRaises(ledger_mod.BudgetExceeded):
            ledger.record_call("review", "muse-ember", 100000, 100000,
                               mock=False)
        # The rejected call is not recorded.
        self.assertEqual(ledger.records, [])

    def test_check_can_spend(self):
        ledger = ledger_mod.Ledger(budget_usd=1.0)
        ledger.check_can_spend(0.50)  # fine
        with self.assertRaises(ledger_mod.BudgetExceeded):
            ledger.check_can_spend(1.50)


if __name__ == "__main__":
    unittest.main()
