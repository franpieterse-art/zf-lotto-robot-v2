# ZF Lotto Robot V28 — Eight-factor formula, all numbers allowed

Five unique prediction rows. All eligible numbers are included (no hot/cold exclusions).

Formula: S(n) = .20 Frequency + .15 Momentum + .15 Gap + .15 Recency + .10 Pairing + .10 Cycle + .10 Trend + .05 Backtest. Each factor is standardized before weighting.

Predict and backtest use **all locally available Main LOTTO draws strictly before the chosen date**, never future draws. Reveal compares separately with locally stored LOTTO / PLUS 1 / PLUS 2 or 5 MAX where available. Draw format boundaries are provisional and should be verified. Historical data may be incomplete.

Install: pip install -r requirements.txt
Run: gunicorn server:app --bind 0.0.0.0:$PORT --timeout 120
Deploy: extract ZIP and upload all files to GitHub, commit, redeploy Render.

This formula is experimental. Fair lottery draws are independent; historical patterns do not improve theoretical winning odds.
