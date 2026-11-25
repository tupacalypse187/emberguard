"""Token and cost accounting for EmberGuard reviews.

The $10 hackathon credit budget is a feature of the demo, so spend is
measured, not asserted. Every model call is recorded here with its token
counts and computed cost. The ledger hard-stops: recording a call that
would push total spend past the budget cap raises BudgetExceeded instead
of letting the run continue.

Rates below are placeholders. Day 1 calibration (see the build plan)
replaces them with measured Muse Ember rates.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

DEFAULT_BUDGET_USD = 10.00

# Placeholder rates in USD per 1,000 tokens, pending day 1 calibration.
INPUT_USD_PER_1K = 0.0002
OUTPUT_USD_PER_1K = 0.0008


class BudgetExceeded(RuntimeError):
    """Raised when a call would push total spend past the budget cap."""


def estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    """Compute the cost of one call from its token counts."""
    return (
        input_tokens / 1000.0 * INPUT_USD_PER_1K
        + output_tokens / 1000.0 * OUTPUT_USD_PER_1K
    )


@dataclass
class CallRecord:
    stage: str          # "review" or "verify"
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    mock: bool
    note: str = ""


@dataclass
class Ledger:
    budget_usd: float = DEFAULT_BUDGET_USD
    records: list = field(default_factory=list)

    @property
    def total_cost_usd(self) -> float:
        return sum(r.cost_usd for r in self.records)

    @property
    def total_tokens(self) -> int:
        return sum(r.input_tokens + r.output_tokens for r in self.records)

    @property
    def remaining_usd(self) -> float:
        return self.budget_usd - self.total_cost_usd

    def check_can_spend(self, projected_cost_usd: float) -> None:
        """Raise BudgetExceeded if spending this much would break the cap."""
        if self.total_cost_usd + projected_cost_usd > self.budget_usd:
            raise BudgetExceeded(
                "Budget cap reached: total $%.4f + projected $%.4f exceeds "
                "the $%.2f budget. Halting before further API calls."
                % (self.total_cost_usd, projected_cost_usd, self.budget_usd)
            )

    def record_call(
        self,
        stage: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        mock: bool = False,
        note: str = "",
    ) -> CallRecord:
        """Record one model call. Mock calls always cost $0.00.

        Raises BudgetExceeded when a live call would exceed the cap; the
        call is not recorded in that case.
        """
        cost = 0.0 if mock else estimate_cost_usd(input_tokens, output_tokens)
        self.check_can_spend(cost)
        record = CallRecord(
            stage=stage,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            mock=mock,
            note=note,
        )
        self.records.append(record)
        return record

    def cost_line(self) -> str:
        """One-line cost summary used in the verdict comment."""
        if self.records and all(r.mock for r in self.records):
            return (
                "Cost of this review: $0.00 (mock mode, no live API calls). "
                "Total spend so far: $%.2f of the $%.2f budget."
                % (self.total_cost_usd, self.budget_usd)
            )
        return (
            "Cost of this review: $%.4f across %d model call(s). "
            "Total spend so far: $%.4f of the $%.2f budget ($%.4f remaining)."
            % (
                self.total_cost_usd,
                len(self.records),
                self.total_cost_usd,
                self.budget_usd,
                self.remaining_usd,
            )
        )

    def to_dict(self) -> dict:
        return {
            "budget_usd": self.budget_usd,
            "total_cost_usd": self.total_cost_usd,
            "total_tokens": self.total_tokens,
            "records": [asdict(r) for r in self.records],
        }

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)
