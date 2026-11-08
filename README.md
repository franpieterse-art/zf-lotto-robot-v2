# ZF Lotto Robot V8 — five coldest numbers excluded

This update keeps V7's five strategies, Reveal, Reset and walk-forward backtesting.

## New cold-number rule
For each selected historical date, count appearances of every number 1–52 across **all available verified 6/52 draws strictly before that date**. Exclude the five with the fewest appearances from all five prediction rows. Ties are resolved by the longest gap since last appearance, then ascending number. The API response shows which five were excluded. Reset changes the generated rows, but recomputes the same exclusions for the same date/history.

Walk-forward testing recomputes exclusions independently at each test date, with no future draws used. The actual winning result is only accessed when Reveal is requested.

**Important:** This is an experimental heuristic. Cold numbers are not less likely to appear in a fair independent lottery. Excluding five numbers can reduce coverage and does not increase the chance of any particular six-number combination winning.

## Deploy
Upload `engine.py`, `server.py`, `index.html`, `requirements.txt`, `render.yaml` and `README.md` to the root of the existing GitHub repository. Render Web Service build: `pip install -r requirements.txt`; start: `gunicorn server:app --bind 0.0.0.0:$PORT --timeout 120`.

## Data source
The existing V7 BetTip downloader is retained **without live verification**. If the historical provider is unavailable, prediction requires a verified historical archive (`draws.csv`); the application will not fabricate results.
