# ZF Lotto Robot V19 — History / API diagnostics fix

Based on the actual V18 ZIP. Preserves all numbers eligible, five prediction strategies, date-locked prediction, Reveal comparison for Main Lotto, Lotto Plus 1 and Lotto Plus 2, bundled Main Lotto CSV, SQLite storage, imports and exports, and Render setup.

## Fixes
- A selected date with **12–24** earlier same-era draws now permits a prediction with a clear short-history warning; previously it was blocked by a fixed 25-draw threshold. Fewer than 12 still fails safely. This does **not** magically fill the archive, nor does it establish reliable predictive accuracy.
- Adaptive-window validation handles the smaller history without target/future leakage.
- The BetTip endpoint and last-attempt timestamp appear in `/api/status`, alongside the actual network/parser error and combined-archive error. The Retry button surfaces those errors.
- The refresh endpoint no longer repeats the same BetTip request separately for Plus 1 and Plus 2, reducing avoidable timeouts.
- Plus results remain separate and never substitute Main Lotto numbers. Plus 2 availability from BetTip is unconfirmed.

## Important data warning
The provided Main Lotto CSV has 1,230 records overall, but the app detected only 19 compatible earlier draws for 2026-08-08. Those 19 may be enough to run V19, but they are a **small sample**. Historical era boundaries are provisional and must be verified against official rules. The app never fabricates Plus results or changes historical records to make predictions possible.

## Deploy
Upload the eight files in this ZIP to the root of your existing GitHub repository. Render build: `pip install -r requirements.txt`; start: `gunicorn server:app --bind 0.0.0.0:$PORT --timeout 120`.

## Diagnostics
Click **RETRY HISTORICAL DOWNLOAD** then **CHECK DATA COVERAGE**. Check `/api/status` for `fetch_error`, `combined_error`, `plus_draws`, `bet_tip_endpoint`, and `bet_tip_last_attempt`. BetTip live access has not been verified in this build.

A fair lottery is random. These methods have no established edge over random picks.
