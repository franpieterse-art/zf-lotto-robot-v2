# ZF Lotto Robot V6

Five historical strategies, five six-number rows, blind reveal and walk-forward backtesting. This is a research tool, not a demonstrated winning-number predictor. In a fair 6/52 draw, any one six-number row has an expected 36/52 = 0.6923 matches.

## Deploy to GitHub / Render
Upload files to the repository root (do not upload __pycache__). Create a Render **Web Service**. Build command `pip install -r requirements.txt`; start command `gunicorn server:app --bind 0.0.0.0:$PORT --timeout 120`. Or deploy using `render.yaml` as Blueprint. `index.html`, `server.py`, `engine.py`, and `requirements.txt` are required.

## Historical data
No unverifiable draw results are bundled. Upload a verified CSV with `date,n1,n2,n3,n4,n5,n6` columns. This is a fallback for historical backtests; the app cannot honestly predict without earlier results. Import is in an expandable Data Source panel. Data imported through the UI is held in server memory and is lost on Render restart; to persist, commit a verified `draws.csv` to the repo or use durable storage. The CSV should contain **main draw numbers only**, not bonus balls. Draws should be from the same 6/52 rules era.

## Optional automatic online reveal
Set `LOTTO_RESULTS_URL_TEMPLATE` on Render to a **verified** HTTPS JSON endpoint, with `{date}` placeholder, e.g. `https://your-provider.example/draw?date={date}`. Expected JSON: `{"date":"2026-08-01","numbers":[1,2,3,4,5,6]}`. No real provider is assumed. This endpoint is only contacted **after Reveal**. The model uses only draws strictly before the selected date. To automatically load historical training data, a verified archive must be provided; this version does not fabricate or scrape it. API keys should be kept server-side; if your provider requires a custom authentication header, adapt `fetch_date` rather than putting credentials in the URL.

## Method
Each strategy produces one row: frequency/recency, hot/cold and gaps, pair/triplet-related pair weighting, online logistic learning, and equal-weight ensemble. The pair model uses observed pair co-occurrences; triplet-specific scoring is not yet implemented. Online logistic training reconstructs feature vectors from preceding draws. The deterministic reset seed changes candidates but not the historical information. Reveal reports each row's matches and matched-number percentage; this percentage is **not a win probability**. Backtest scores out-of-sample predictions sequentially and reports histograms and >=3 / >=4 matches. Never select a strategy using test data and then claim the same test is independent validation.
