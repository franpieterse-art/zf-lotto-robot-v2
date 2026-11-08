# ZF Lotto Robot V7 — BetTip integration (candidate)

This replaces V6 while retaining the five strategies, blind Predict -> Reveal -> Compare, reset, and chronological backtesting.

## Important provider warning
The advertised BetTip endpoint `https://bettip.co.za/api/v1/lotto/draws.json` could not be reached or independently validated in the build environment. The code attempts this endpoint, checks HTTPS, validates six unique numbers and dates, caches the archive for six hours, and displays errors instead of fabricating results. Its actual JSON schema and historical coverage have NOT been confirmed. If the API is unavailable or has a different schema, use a verified `draws.csv` archive or configure `LOTTO_ARCHIVE_URL` to a trusted compatible JSON/CSV archive. Data from earlier game formats must be reviewed: the current validator checks number bounds, not historical game rules.

## GitHub
Upload `server.py`, `engine.py`, `index.html`, `requirements.txt`, `render.yaml` and README to repository root. Do not upload `__pycache__` or `.pyc` files. Optional `draws.csv` with columns `date,n1,n2,n3,n4,n5,n6` provides persistent fallback.

## Render Web Service
Build: `pip install -r requirements.txt`
Start: `gunicorn server:app --bind 0.0.0.0:$PORT --timeout 120`
Python: 3.12.8. No API key is used for BetTip.

## Limitations
The six-number match percentage is descriptive, not a winning probability. Random lottery outcomes are not predictably improved by historical patterns. Five strategies are preserved from V6; its 'pairs/triplets' row actually uses pair statistics, not triplet counts. Backtesting requires trustworthy, chronological and complete data. Render's in-memory cache resets on restart; for persistent history commit a verified draws.csv file.
