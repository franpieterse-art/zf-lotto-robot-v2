# ZF Lotto Robot V40 — Walk-forward testing

Run locally: `pip install -r requirements.txt && python server.py`. Open http://localhost:5000.

Upload historical CSV through the UI (or place `za_lotto.csv` next to `server.py`). CSV rows must have an ISO, DD/MM/YYYY, YYYY/MM/DD or DD-MM-YYYY date and six individual numeric main-number fields. If your CSV has extra numeric fields before the main numbers, normalize it first. Date parsing is day-first for slash dates.

**Predict** hides actual results until **Reveal**. The server recomputes deterministic predictions rather than trusting browser-submitted tickets. **Backtest** compares seven engines over up to 300 dates. Adaptive weights are learned using only earlier results, never the target draw. Five unique lines per engine and date. Learning does not imply statistical predictive power.

For Render free instances, uploaded CSV data may be lost on redeploy/restart due to ephemeral storage. Commit the CSV to the repository or use persistent storage. This is a standalone V40 prototype; it does not automatically include any features from earlier ZIPs without the source files.


## V41 performance repair
- Historical adaptive learning results are cached within each backtest request; each base engine is evaluated only once per historical draw in the required training window.
- HTTP error pages now show understandable errors rather than JSON parsing exceptions.
- Unhandled backtest exceptions are logged and returned as JSON.
- No future-data leakage: each evaluated draw uses only earlier draws.
- This is not a claim of improved lottery prediction accuracy.

Deploy to the existing `v40-testing` branch and the separate Render test service only.
