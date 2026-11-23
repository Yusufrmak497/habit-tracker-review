## Problem
`POST /habits` accepted empty names, and check-ins accepted any string as `day` (e.g. `"yesterday"`). That
bad data broke anything that reads dates (Task 2 in `docs/TASKS.md`).

## Approach
These checks are Pydantic `field_validator`s, so FastAPI returns a standard **422** with a clear `msg`:
- **name**: the outer whitespace is trimmed. A name that is empty, whitespace-only or made only of invisible characters
  (e.g. U+200B) gets `habit name must not be empty`. Over 100 characters gets `habit name must be at most 100 characters`.
- **day**: it must fully match `[0-9]{4}-[0-9]{2}-[0-9]{2}`, ASCII digits only, otherwise the message is
  `day must be an ISO date in YYYY-MM-DD format`. It must also be a real calendar date, otherwise
  `day '2026-02-30' is not a valid calendar date`.

## Testing
`scripts/check.sh`: **24 passed**. Covered: empty, whitespace-only and invisible-only names, a missing name, an over-long name,
trimming, 6 malformed day formats, 3 impossible dates, non-ASCII digits, wrong JSON types, and the leap day `2028-02-29` (accepted).
The rejection tests also check that nothing was stored.

## Tradeoffs and follow-ups
- 422 (FastAPI's standard error) was chosen over 400, so clients get one consistent error shape.
- Existing rows with bad `day` values are not migrated. Only new writes are validated.
- `day` stays a `str` in the model (the API shape is unchanged). Typing it as `datetime.date` would improve the OpenAPI docs.

Commits: `34c1d0b` is the agent's one-shot implementation. `8c5a7be` and `fb66396` are the review fixes.
