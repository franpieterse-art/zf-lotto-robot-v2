# ZF Lotto Robot V18 — BetTip SA Lotto API

Based on the user's V17 app, retaining all-number eligibility, five prediction strategies, date-based blind Predict → Reveal → Compare, Main LOTTO / PLUS 1 / PLUS 2 display, CSV import/export, SQLite cache and walk-forward testing.

## Correct BetTip API integration

Documented API: https://bettip.co.za/api/v1/lotto/draws.json

BetTip's JSON uses a `data` envelope with a mixed-game list. V18 requests this endpoint once, then separates records by `game`: `lotto`, `lotto-plus-1`, `lotto-plus-2` (if ever present). PowerBall and Daily Lotto are excluded. It validates dates, six distinct numbers and rejects conflicting records before saving to SQLite. Refreshes are throttled to six hours. Existing local CSV data remains available offline. BetTip is credited in the interface, as its terms request.

**Coverage warning:** BetTip's published documentation lists SA Lotto and Lotto Plus 1, but NOT Lotto Plus 2. The app will label Plus 2 unavailable unless a verified alternative archive or CSV supplies it. Do not substitute Lotto 5 MAX for Plus 2. A separate optional Lottology HTML fallback remains.

**Verification:** Local parser tests and Python syntax checks passed; the live API cannot be reached from this build environment, and successful deployment on Render is not guaranteed. BetTip's feed may lag and its data is third-party, not independently verified by the app.

## GitHub/Render

Upload all eight files to the root of https://github.com/franpieterse-art/zf-lotto-robot-v2 and commit. Render build: `pip install -r requirements.txt`. Render start: `gunicorn server:app --bind 0.0.0.0:$PORT --timeout 120`. Click **RETRY HISTORICAL DOWNLOAD** and check the three per-game counts. If a game is unavailable, import verified CSV under Historical results data source.

No hot/cold numbers excluded. No predictive advantage is established by past lottery data.
