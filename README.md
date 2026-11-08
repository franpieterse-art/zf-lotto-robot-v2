# ZF Lotto Robot V9 — triple draw comparison

V9 keeps V8 five coldest-number exclusions and five prediction strategies, and compares each of the five rows to three independent draw results: Main Lotto, Lotto Plus 1, Lotto Plus 2. Click Predict first, then Reveal. A missing result is shown as unavailable, not invented.

## Historical data

Main Lotto prediction training uses **only Main Lotto results strictly earlier than the chosen date**. Plus 1/2 are comparison-only and are not used to train predictions or calculate the five coldest numbers.

The application attempts three BetTip endpoints. **The Plus endpoint paths are unverified and may not exist.** If downloads fail, supply verified `draws.csv`, `draws_plus1.csv`, and `draws_plus2.csv` in the GitHub repository, or import via the UI game selector. CSV columns: `date,n1,n2,n3,n4,n5,n6`. Each date must be checked against an authoritative source. Optional env vars: `LOTTO_ARCHIVE_URL`, `LOTTO_PLUS1_ARCHIVE_URL`, `LOTTO_PLUS2_ARCHIVE_URL`.

## Render

Build: `pip install -r requirements.txt`
Start: `gunicorn server:app --bind 0.0.0.0:$PORT --timeout 120`

## Limitations

A fair Lotto draw is random. Excluding cold numbers does not improve mathematical odds. Live API availability is unverified. Main game backtesting is retained from V8; Plus comparisons are shown in Reveal, not included in the aggregate backtest summary.
