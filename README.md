# ZF Lotto Robot V13 — Historical archive and persistence upgrade

Keeps the V12 five-strategy predictions, exclusion of the five historically hottest numbers, blind Predict → Reveal → Compare for three games, and chronological walk-forward backtests.

## Improvements
- SQLite result cache, deduplication and conflict rejection by game/date.
- Loads cached results before fetching online; CSV imports are also cached.
- BetTip JSON/CSV and Lottology HTML fallback inherited from V12 (availability and endpoint format **not verified**).
- Optional paginated JSON/CSV archive downloads configured by URL templates; stops on errors and never invents results.
- Data coverage endpoint `/api/data-health` and CSV backups `/api/export/lotto`, `/api/export/plus1`, `/api/export/plus2`.
- CSV import supports `date,n1,n2,n3,n4,n5,n6`; rejects invalid rows and conflicts.
- Historical draws before 2026-06-04 excluded because the robot's current engine is for 6/52 only. Older draws require separate ruleset-specific modelling; the app cannot legitimately promise 5–10 years of comparable 6/52 results.

## Run
`pip install -r requirements.txt` then `python server.py`. For Render use included `render.yaml`.

## Data persistence on Render
Default database is `lotto_history.sqlite3` in the working directory. **Render free filesystem is ephemeral**; downloaded/imported data may disappear after restart or deployment. For a paid persistent disk mounted at `/var/data`, set `LOTTO_DB_PATH=/var/data/lotto_history.sqlite3`. Otherwise export the CSVs after importing and commit them to the GitHub repo as `draws.csv`, `draws_plus1.csv`, and `draws_plus2.csv` for repeatable deploys.

## Optional paginated source
Set `LOTTO_LOTTO_PAGED_URL`, `LOTTO_PLUS1_PAGED_URL`, `LOTTO_PLUS2_PAGED_URL` to **real verified HTTPS URL templates** containing `{page}`, for example `https://example.org/archive?page={page}` (example only, not a real provider). Set `LOTTO_ARCHIVE_MAX_PAGES` (default 30, maximum 500). On Retry Historical Download, the server visits each page and imports compatible JSON or CSV. Do not use this option until an actual working endpoint is confirmed.

## Limits
Source results are third-party, not automatically official-verified. Imported numbers are checked for format and conflicts, not independently verified against the lottery operator. Missing data remains missing. No number-frequency strategy improves the theoretical odds of an individual ticket in a fair lottery.
