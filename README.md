# ZF Lotto Robot V25 — Seven experimental research methods

Built from V24 with all uploaded historical CSV files retained. Five prediction rows are chosen from seven models: Markov-style transitions, Bayesian smoothing, momentum, multi-window rank stability, historical triplet support, Monte Carlo sampling, and adaptive-window frequency. Each model is scored on up to eight **earlier** completed draws, then five are selected for the target date. No selected-date or later results are used for prediction. The same selected rows are compared to Main Lotto, Lotto Plus 1, and the correctly labelled Plus 2 / Lotto 5 Max third panel after Reveal.

All valid numbers remain eligible. Historical data still comes from user-uploaded CSV files and cached sources. The existing historical game-era logic is retained. Model validation is exploratory and may overfit; no predictive advantage over random selection has been established. For a fair 6/52 game each combination has jackpot odds of 1 in 20,358,520.

Deploy the ten files to the GitHub repository root. Render build: `pip install -r requirements.txt`; start: `gunicorn server:app --bind 0.0.0.0:$PORT --timeout 120`.
