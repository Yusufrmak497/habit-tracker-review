# Week 6 — AI Code Review & Testing: The Habit Tracker

**Student:** Yusuf Irmak

> **Process note:** I used Claude Code throughout. One-shot `claude -p` sessions did the implementation, and the
> line-by-line review and the fixes were done in a separate Claude Code session that I directed. The AI
> reviewer was another, fresh Claude Code session given only the diff and a reviewer prompt
> (see §4 on why it is not Graphite).

## 1. Guardrails (Part I)
| Command | What it catches |
|---|---|
| `black --check --diff .` | Any formatting drift (line length 100, see `pyproject.toml`) |
| `ruff check .` | Unused imports and names (F), import order (I), likely bugs such as mutable defaults and `except` without `from` (B), old syntax (UP), simplifications (SIM) |
| `pytest` | Behaviour regressions. A failing test makes the run exit non-zero |

`scripts/check.sh` runs all three and exits **1** if any of them fails. The same script runs in
**GitHub Actions** (`.github/workflows/ci.yml`) on every push and PR, so a failing test fails the build.
Evidence: [`evidence/guardrails-failing.txt`](evidence/guardrails-failing.txt) shows a deliberately broken change with
an unused `import os`, unformatted code and a wrong test expectation. black reported `would reformat main.py`,
ruff reported `F401 'os' imported but unused`, pytest reported `FAILED test_main.py::test_checkin_flow`, and the script
ended with `✖ guardrails FAILED` and exit code 1.

## 2. The two PRs (Part II)
| PR | Branch | Agent's one-shot commit | Review-fix commits | Tests |
|---|---|---|---|---|
| Streak (Task 1) | `feature/streak` | `edff38f` | `f22b2e8`, `3ae1d42` | 13 passed |
| Validation (Task 2) | `feature/validation` | `34c1d0b` | `8c5a7be`, `fb66396` | 24 passed |

The PR descriptions (problem, approach, testing, tradeoffs) are in [`docs/prs/`](docs/prs/).
The one-shot prompts are in `evidence/prompt-*.txt`. Each prompt was the task text from `docs/TASKS.md`
plus "run scripts/check.sh until it passes, do not commit".

## 3. Manual review findings

### Streak
| # | Where | Finding | Type | Action |
|---|---|---|---|---|
| 1 | `test_main.py` (all tests) | Tests write to the real, shared `habits.db`, so data builds up between runs, and the hard-coded `99999` "unknown" id could one day exist | test gap | **Fixed**: an autouse fixture in `conftest.py` gives every test its own SQLite file |
| 2 | `get_streak` | No check-in yet today means streak = 0, so a 30-day streak shows 0 every morning | API shape / UX | Kept (it is the literal spec), documented as a tradeoff in the PR |
| 3 | `today()` | Server-local date, so the result depends on timezone | correctness risk | Documented |
| 4 | `get_streak` | Loads every check-in into memory | perf (minor) | Documented as a follow-up |

### Validation
| # | Where | Finding | Type | Action |
|---|---|---|---|---|
| 1 | `ISO_DAY_RE` | `\d` matches **any Unicode digit**, so `"٢٠٢٦-٠٩-٢٢"` passed the format check and got the misleading "not a valid calendar date" message | correctness | **Fixed** (`[0-9]`), with the regression test `test_checkin_rejects_non_ascii_digits`. I confirmed it fails on the agent's original code |
| 2 | tests | Same shared-DB problem as in Streak | test gap | **Fixed** (same fixture) |
| 3 | `HabitIn.name` | No maximum length | robustness | Documented, then fixed after the AI review raised it too |

## 4. AI reviewer
**Tool:** Claude Code in a fresh session (`claude -p`) with a reviewer prompt, read-only tools, and only the
PR diff (`git diff main...HEAD`). It produced GitHub-style `file:line [severity]` comments. The full output is in
[`evidence/ai-review-streak.md`](evidence/ai-review-streak.md) and
[`evidence/ai-review-validation.md`](evidence/ai-review-validation.md).
The default, Graphite Diamond, needs its GitHub app installed through a browser sign-up. The PRs and these
comments are posted on GitHub when the repo is pushed.

**Verdicts:** Streak → `REQUEST_CHANGES` (14 comments). Validation → `APPROVE` (13 comments).

## 5. Human vs. AI review

**Where the AI was better**
- **Breadth of edge cases.** It suggested the year-boundary test (`2026-12-30 … 2027-01-01`), the
  isolation-between-habits test (checks that the `habit_id` filter really works), and the wrong-JSON-type tests
  (`{"day": 20260922}`, `null`). None of these were in my review. I added all of them.
- **Invisible-character names.** `"​"` (zero-width space) survives `strip()`, so the API stored a name that
  looks empty. I missed this. It is now rejected and tested.
- **Connecting the two PRs.** On Streak it said that skipping malformed rows "papers over" the missing input validation,
  which is exactly what the Validation PR fixes.
- **A leftover side effect of my own fix.** `import main` still runs `init_db()` against the real `habits.db`
  before the fixture swaps the path. It is harmless, since the file is git-ignored and the tests never write to it, but it was true.

**Where the AI was worse**
- **It missed the Unicode-digit bug.** To be fair, it reviewed the final diff, where the bug was already fixed.
  But it also didn't flag the `\d` vs `[0-9]` question as a general risk. Our human review caught it by reading the regex.
- **Noise.** 27 comments across two small PRs. About a third were nits: `response_model`, `{v!r}` quoting,
  "move evidence files out of the PR", and a version-difference note about `fromisoformat`. It even marked some
  of its own points as harmless. The `fromisoformat` point turned out to be irrelevant once the Validation PR
  added a strict regex check. You still have to triage the output yourself.
- **Product decisions phrased as defects.** "Streak is 0 until you check in today" was raised as a `risk`.
  That is a spec question, not a bug. Both reviews noticed it, but only a person can decide it.
- **Inconsistent verdicts.** Streak got REQUEST_CHANGES for issues of about the same weight as the Validation
  issues, which got APPROVE. The verdict alone isn't a reliable merge signal.

**Accepted vs. rejected AI comments:** I accepted 6: year boundary, cross-habit test, documenting the streak
semantics, invisible names, max length, `fullmatch`/wrong-type tests. I rejected or deferred the rest (typing `day` as
`datetime.date`, which changes the stored value path; a lifespan hook for `init_db`; `response_model`; stylistic nits),
each for a stated reason.

## 6. What I learned
<!-- Yusuf: 3–5 sentences on combining guardrails with LLM review, and your comfort trusting AI reviews. -->
