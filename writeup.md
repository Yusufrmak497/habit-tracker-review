# Week 6 — AI Code Review & Testing: The Habit Tracker

**Student:** Yusuf Irmak

> **Process note:** I used Claude Code throughout. One-shot `claude -p` sessions did the implementation, and the
> line-by-line review and the fixes were done in a separate Claude Code session that I directed. The AI
> reviewers were **CodeRabbit** (the course default, installed on the repo) and, as a second opinion,
> a fresh Claude Code session given only the diff and a reviewer prompt (see §4).

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
| [#1 Streak (Task 1)](https://github.com/Yusufrmak497/habit-tracker-review/pull/1) | `feature/streak` | `edff38f` | `f22b2e8`, `3ae1d42` | 13 passed |
| [#2 Validation (Task 2)](https://github.com/Yusufrmak497/habit-tracker-review/pull/2) | `feature/validation` | `34c1d0b` | `8c5a7be`, `fb66396`, `22b4734` (CodeRabbit) | 33 passed |

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

## 4. AI reviewers
### CodeRabbit (primary)
Installed on the public repo and triggered with `@coderabbitai review` on both PRs; its comments are on the PRs.
- **Streak (#1):** no actionable comments. Its security note was that the route loads the habit's whole
  check-in history to compute one number, which is the same perf point as my manual finding #4.
- **Validation (#2):** 2 actionable comments, **both real**, both of which my review and the Claude reviewer missed:
  1. `main.py:62`: a name of only `U+034F` (combining grapheme joiner) passed, because Python treats
     that mark as printable. Fixed: a name now needs at least one letter, number, punctuation or symbol.
  2. `main.py:75`: `v.strip()` ran *before* the format check, so `"2026-09-22\n"` and `" 2026-09-22 "` were
     accepted. Fixed: the submitted string must itself be `YYYY-MM-DD`.

  I reproduced both (HTTP 200), added 8 regression tests that failed before the fix, and pushed `22b4734`;
  each CodeRabbit thread has a "Fixed in 22b4734" reply.

### Claude Code reviewer (second opinion)
**Tool:** Claude Code in a fresh session (`claude -p`) with a reviewer prompt, read-only tools, and only the
PR diff (`git diff main...HEAD`). It produced GitHub-style `file:line [severity]` comments. The full output is in
[`evidence/ai-review-streak.md`](evidence/ai-review-streak.md) and
[`evidence/ai-review-validation.md`](evidence/ai-review-validation.md).
The same comments are posted on
[PR #1](https://github.com/Yusufrmak497/habit-tracker-review/pull/1) and
[PR #2](https://github.com/Yusufrmak497/habit-tracker-review/pull/2).

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
  But it also didn't flag the `\d` vs `[0-9]` question as a general risk. The manual review caught it by reading the regex.
- **Noise.** 27 comments across two small PRs. About a third were nits: `response_model`, `{v!r}` quoting,
  "move evidence files out of the PR", and a version-difference note about `fromisoformat`. It even marked some
  of its own points as harmless. The `fromisoformat` point turned out to be irrelevant once the Validation PR
  added a strict regex check. You still have to triage the output yourself.
- **Product decisions phrased as defects.** "Streak is 0 until you check in today" was raised as a `risk`.
  That is a spec question, not a bug. Both reviews noticed it, but only a person can decide it.
- **Inconsistent verdicts.** Streak got REQUEST_CHANGES for issues of about the same weight as the Validation
  issues, which got APPROVE. The verdict alone isn't a reliable merge signal.

**Accepted vs. rejected AI comments:** I accepted 7: year boundary, cross-habit test, using `99999` for the 404 test, documenting the streak
semantics, invisible names, max length, `fullmatch`/wrong-type tests. I rejected or deferred the rest (typing `day` as
`datetime.date`, which changes the stored value path; a lifespan hook for `init_db`; `response_model`; stylistic nits),
each for a stated reason.

**CodeRabbit vs. Claude reviewer vs. me:** CodeRabbit was far quieter (2 comments vs. 27) but both
of its comments were real bugs, and both sit in the same "invisible/odd Unicode input" area where my own
best finding (the Arabic-digit regex) was. None of the three reviews caught everything alone.

## 6. What I learned
The guardrails (black, ruff, pytest) only check that the code is well formed and that the tests pass, and the regex that accepted Arabic digits went through all of them; I only found that bug by reading the code line by line. The human and the AI caught different things: the AI didn't flag the Unicode-digit issue, but it found the invisible-character names and the year-boundary test that I had missed, and we both noticed the missing name length limit. The Claude reviewer's 27 comments were a fast second pair of eyes, though about a third were nits I had to triage, while CodeRabbit posted only 2 comments and both were real bugs that everyone else had missed. So I trust AI review as an assistant but not as the final word: it lists obvious gaps quickly, it can miss subtle logic bugs, and its verdicts weren't consistent, so the final approval still has to come from a person.
