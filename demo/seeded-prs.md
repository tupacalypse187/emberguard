# Seeded Demo Pull Requests

The demo repo carries three seeded pull requests. Each one maps to a
cached diff in `sample-diffs/`, which is also what mock mode and the
test suite run against. On demo day the same three changes are opened
as live PRs in the demo repo and reviewed on camera.

| # | PR | Sample diff | Expected verdict |
|---|---|---|---|
| 1 | Small billing formatting helpers with tests | `sample-diffs/01-clean.diff` | ✅ Pass, no findings, review cost shown in the comment |
| 2 | Payment charging module with a live API key written into the source | `sample-diffs/02-hardcoded-secret.diff` | ❌ Fail: hardcoded secrets (blocking), finding survives the verify pass, commit status blocks the merge |
| 3 | Account settings endpoint with its login check removed | `sample-diffs/03-removed-auth-check.diff` | ❌ Fail: missing authentication check (blocking), with a plain-English explanation a non-security developer can act on |

## How each PR is constructed

1. **Clean change.** Two new files: a formatting helper module and its
   tests. Nothing touches credentials, endpoints, permissions, or
   network calls. Any finding here is a false positive by definition.
2. **Hardcoded secret.** A new payments module that assigns a
   live-format API key to a constant and uses it for an Authorization
   header. The key in the sample diff is a clearly fake placeholder
   with a live-key shape: GitHub push protection blocks even the
   provider's published documentation example key, so the fixture
   uses a stand-in that no scanner mistakes for a real credential.
3. **Removed auth check.** A diff against an existing routes module:
   the `require_auth` decorator and the current-user lookup come off
   the account settings endpoint, and the handler switches to trusting
   an email address supplied in the form. Constructed so the verify
   pass can confirm no replacement check exists anywhere in the diff.

## Building the live demo repo

1. Create a public repo and commit the base code (the account routes
   module in its pre-diff state, plus a README).
2. Open PR 1 from a branch carrying the clean change.
3. Open PR 2 from a branch carrying the payments module.
4. Open PR 3 from a branch carrying the auth removal.
5. Install the EmberGuard Action in observe mode first; switch PR 2
   and PR 3 to enforce mode when demonstrating the blocking status.
