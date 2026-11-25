# 🔥 EmberGuard

Always-on pull request security review for solo maintainers and small teams, powered by [Muse Ember](https://cerebralvalley.ai/e/muse-ember-hackathon), the smallest and most efficient model in Meta's Muse series.

Frontier models are too expensive to run over every diff, so most small projects merge with no security review at all. EmberGuard reviews every pull request against a security policy pack, posts a pass/fail verdict as a PR comment and a commit status, and prints the measured cost of the review right in the comment. If a review costs pennies, review everything stops being an enterprise luxury.

Built for the Cerebral Valley Muse Ember Hackathon (November 23 to December 2, 2026). The entire build, development, testing, and demo included, runs on the hackathon's $10 in Meta Model API credits.

## 📑 Table of Contents

- [How It Works](#-how-it-works)
- [Quick Start (Mock Mode)](#-quick-start-mock-mode)
- [Mock Mode](#-mock-mode)
- [The Policy Pack](#-the-policy-pack)
- [Cost Discipline](#-cost-discipline)
- [Demo](#-demo)
- [Repo Layout](#-repo-layout)
- [What Remains for Live Mode](#-what-remains-for-live-mode)
- [Scope](#-scope)

## 🧩 How It Works

| Step | What happens |
|---|---|
| 1. Trigger | A pull request opens or updates; the GitHub Action starts |
| 2. Fetch | The Action gets the PR diff with `gh pr diff`; lock files, vendored code, and generated files are filtered out, and oversized hunks are capped |
| 3. Review | Each changed file's diff goes to Muse Ember with the repo's policy pack |
| 4. Verify | A second, adversarial pass tries to refute each finding; findings that do not survive are dropped |
| 5. Verdict | One summary comment (verdict, findings, cost of this review) plus a commit status: success on pass, failure on a blocking finding |
| 6. Gate | Add the status to branch protection to enforce it, or stay in observe mode and block nothing while trust builds |

Modes: **observe** (default) comments and never blocks. **Enforce** sets a failing commit status when a blocking finding stands.

## 🚀 Quick Start (Mock Mode)

No API key, no spend, Python 3 stdlib only.

```bash
git clone https://github.com/tupacalypse187/emberguard.git
cd emberguard

# Run the three seeded scenarios
EMBERGUARD_MOCK=1 python3 -m src.main --diff demo/sample-diffs/01-clean.diff
EMBERGUARD_MOCK=1 python3 -m src.main --diff demo/sample-diffs/02-hardcoded-secret.diff
EMBERGUARD_MOCK=1 python3 -m src.main --diff demo/sample-diffs/03-removed-auth-check.diff

# Run the tests
python3 -m unittest discover -s tests -v
```

Expected results: scenario 1 passes, scenario 2 fails on a hardcoded secret, scenario 3 fails on a removed login check with a plain-English explanation. Add `--mode enforce` to see the failing exit code a blocking status produces.

## 🧪 Mock Mode

Mock mode is the default development path and the reason the $10 budget survives contact with a 10-day build.

- Set `EMBERGUARD_MOCK=1` (mock also engages automatically when no API key is configured).
- The Ember client returns recorded responses keyed to the bundled sample diffs in `demo/sample-diffs/`, so the full pipeline (parse, review, verify, verdict, ledger) runs end to end.
- Every call is recorded in the cost ledger with realistic token counts and a cost of exactly $0.00.
- The test suite runs entirely in mock mode. CI spends nothing.

## 📜 The Policy Pack

Policy is a single markdown file in the target repo at `.emberguard/policy.md`, written in plain language and versioned with the code. When a repo has no pack, EmberGuard uses the bundled default in [`policies/default-security.md`](policies/default-security.md).

| Rule | Severity | Catches |
|---|---|---|
| hardcoded-secrets | Blocking | API keys, passwords, and private keys written into source |
| injection | Blocking | Input concatenated into SQL, shell commands, or HTML |
| missing-auth | Blocking | Endpoints added or changed without an auth check, or an existing check removed |
| unsafe-deserialization | Blocking | Untrusted data fed to object-building deserializers |
| disabled-tls-verification | Blocking | Certificate verification switched off |
| broad-permissions | Advisory | Wildcards and world-open permissions a human should confirm |

Only blocking findings fail the commit status. Advisory findings appear in the comment and never block.

## 💲 Cost Discipline

The $10 credit budget covers development, testing, and the demo combined. The design rules that protect it:

| Rule | How |
|---|---|
| Mock mode first | All iteration runs on cached sample diffs; live calls happen only for calibration and verification |
| Calibrate before iterating | Representative sample PRs run live first, and the measured cost per review drives every later decision |
| Ledger with a hard cap | Every call's tokens and cost are recorded per review; the ledger raises and halts before any call that would exceed the budget |
| Diff hygiene | Lock files, vendored and generated files are skipped; hunks are capped per file |
| The cost is the demo | Every verdict comment prints what the review cost, and the submission reports the measured cost per review and how many reviews $10 bought |

## 🎬 Demo

Three seeded pull requests carry the demo; see [`demo/seeded-prs.md`](demo/seeded-prs.md) for how each is constructed and [`docs/demo-script.md`](docs/demo-script.md) for the 3-minute video outline. The video is narrated with a computer-generated female voice, generated as text-to-speech segments matched to each PR, at $0 against the API budget.

| PR | Change | Verdict |
|---|---|---|
| 1 | Billing formatting helpers with tests | ✅ Pass |
| 2 | Payments module with a live API key in source | ❌ Fail, blocking, merge gated |
| 3 | Account settings endpoint with its login check removed | ❌ Fail, with a plain-English fix explanation |

## 📁 Repo Layout

| Path | Contents |
|---|---|
| `action.yml` | The GitHub Action definition (inputs: mode, budget, policy path) |
| `.github/workflows/emberguard.yml` | Dogfood workflow: tests plus an observe-mode review of PRs in this repo |
| `src/main.py` | Entry point: diff in, verdict out |
| `src/diff.py` | Diff parsing, file filtering, hunk capping |
| `src/review.py` | Ember review loop, client interface, mock client |
| `src/verify.py` | Adversarial verify pass |
| `src/policy.py` | Policy pack loading and severity rules |
| `src/verdict.py` | Verdict, comment formatting, GitHub posting |
| `src/ledger.py` | Token and cost accounting with the budget hard cap |
| `policies/default-security.md` | The bundled default policy pack |
| `demo/` | Sample diffs and the seeded PR construction notes |
| `tests/` | Mock-mode tests; no live API calls |
| `docs/demo-script.md` | The demo video outline and narration plan |

## 🔌 What Remains for Live Mode

The scaffold is complete through the mock pipeline. Live mode needs:

| Piece | State |
|---|---|
| Real Ember client | `LiveEmberClient` in `src/review.py` sits behind the same interface as the mock client and raises until wired; the Meta Model API key does not exist until calibration day, and no live call is attempted before then |
| Calibration | Run representative PRs live, replace the placeholder per-token rates in `src/ledger.py` with measured Muse Ember rates, and record the measured cost per review here |
| GitHub token wiring | Posting already works through the Action's `github.token` when `EMBERGUARD_POST=1`; mock mode forces a dry run so development can never post or spend by accident |
| Branch protection | On the demo repo, require the `emberguard` status check to make the enforce-mode verdict a real merge gate |

## 🎯 Scope

Review and verdict only. EmberGuard never edits code, never merges, and never approves. The agent advises and gates; humans still merge.

---

Built by NeuralSec Advisory. EmberGuard is a working name for a hackathon build that doubles as a product seed: the same review agent, offered to the small teams who currently merge with no security review at all.
