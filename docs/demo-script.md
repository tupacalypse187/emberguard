# Demo Video Script Outline (3 minutes)

The demo video is narrated, not recorded live. Narration is scripted
here first, then generated as text-to-speech audio with a
computer-generated female voice, in segments matched to the sections
below so any one segment can be regenerated on its own. The audio is
laid over a screen recording of the three seeded PRs being reviewed
live. Narration is not a Muse Ember API call, so it costs $0 against
the $10 hackathon budget.

| Segment | Time | On screen | Narration covers |
|---|---|---|---|
| Intro | 0:00 to 0:30 | EmberGuard repo and README | The problem: small projects merge PRs with no security review because frontier models cost too much per diff. EmberGuard reviews every PR on Muse Ember for pennies. |
| PR 1: clean change | 0:30 to 1:05 | Seeded PR 1, verdict comment appears | A normal feature PR passes. Point at the cost line in the comment: this is what one review actually cost. |
| PR 2: hardcoded secret | 1:05 to 1:50 | Seeded PR 2, FAIL verdict and red commit status | A live API key in source code. The finding survives the adversarial verify pass, the status goes red, branch protection blocks the merge. |
| PR 3: removed auth check | 1:50 to 2:35 | Seeded PR 3, FAIL verdict | An endpoint loses its login check. Read the plain-English explanation: written so a developer without a security background knows exactly what to fix. |
| Cost close | 2:35 to 3:00 | The cost ledger totals | Total spent across every demo review, and how many full PR reviews the remaining credit would still buy. Review everything stops being an enterprise luxury. |

## Production notes

- Record the screen flow first, then generate narration segments to
  fit the timing; regenerate single segments as edits require.
- Keep the cost figures in the narration generic until the live runs
  are done, then re-record the cost close segment with measured
  numbers from the ledger.
- Captions on: the verdict comments carry the detail, the narration
  carries the story.
