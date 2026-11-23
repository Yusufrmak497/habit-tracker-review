## Problem
There was no way to see how many days in a row a habit has been done (Task 1 in `docs/TASKS.md`).

## Approach
- New `GET /habits/{id}/streak` returns `{"habit_id": id, "streak": N}`. It counts back from **today** while
  each day has a check-in. Duplicate check-ins on the same day count once, future-dated check-ins are ignored,
  and an unknown habit returns 404.
- `today()` wraps `date.today()`, so tests can pin the date without a time-freezing dependency.
- Tests use a per-test SQLite file (`conftest.py`) instead of the shared `habits.db`.

## Testing
`scripts/check.sh` (black + ruff + pytest): **13 passed**. The streak cases covered are: no check-ins, a 3-day run,
stopping at a gap, no check-in today, duplicates and future days, malformed stored days, month boundary,
year boundary, isolation between habits, and the 404.

## Tradeoffs and follow-ups
- **No check-in yet today means a streak of 0.** That is the literal reading of the spec ("up to and including today").
  A friendlier rule would count back from yesterday until the day is over. That is a product decision, so it's left open.
- **"Today" is the server-local date**, so users in other timezones may see the count change at the server's midnight, not theirs.
- **Malformed stored days are skipped.** The real fix is input validation, which the Validation PR adds.
- All of a habit's check-ins are loaded into memory. That is fine at this scale; once days are validated, the query can be bounded with `day <= today`.

Commits: `edff38f` is the agent's one-shot implementation. `f22b2e8` and `3ae1d42` are the review fixes.
