# ZF Lotto Robot V42 — Research edition

Based on V41. Keeps CSV import, date-based Predict → Reveal → Compare, 5 unique lines, and walk-forward backtesting. Adds three engines: multi-window history (10/25/50/100/250/500), dependency-free online logistic regression, and lightweight gradient-boosted decision stumps. Existing adaptive strategy learns weights from earlier historical results only. Five-row selection penalizes overlap. Champion is chosen using the earlier 70% of tested draws; later 30% is held out and compared with random.

**Limitations:** A lottery designed to be independent and random is not predictably learnable from past draws. Training performance is not evidence of future performance. Five-row diversity improves coverage, not per-ticket winning odds. This is a research tool, not a guaranteed winning system.

## Deploy safely
Upload the ZIP contents to GitHub branch `v40-testing`, **not** `main`. Keep your existing `za_lotto.csv` file. On the separate Render test service, build with `pip install -r requirements.txt` and start with `gunicorn server:app --bind 0.0.0.0:$PORT --timeout 120`. The Free instance can be slow; test 3–5 draws first. The program reads CSV from `za_lotto.csv` and an uploaded CSV saved on Render's ephemeral disk may disappear on redeploy; commit your CSV if persistence is needed.

## Test protocol
Choose a historical date, Predict, then Reveal. Run 3–5 draws initially and then larger batches if performance allows. For meaningful comparisons, use many unseen draws, multiple random seeds and confidence intervals. The champion report is a descriptive holdout check, not statistical proof.
