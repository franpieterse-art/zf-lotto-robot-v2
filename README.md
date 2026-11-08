# ZF Lotto Robot V30 — six-factor formula integrated

Formula: S(n) = 0.20 LongFrequency + 0.20 RecentFrequency + 0.15 Momentum + 0.10 Gap + 0.15 Pairing + 0.20 TrendStability. Components are min-max normalized to a 0–1 scale.

All eligible numbers remain available, with no hottest/coldest exclusions. Five unique rows are generated using historical Main Lotto draws strictly before the selected date. Predict, Reveal, Compare and walk-forward Backtest remain available. Local historical CSV files are bundled. Results from different games are stored separately; missing results are not invented.

Deploy to Render: build `pip install -r requirements.txt`, start `gunicorn server:app --bind 0.0.0.0:$PORT --timeout 120`.

The formula is experimental and does not improve the mathematical odds of a fair lottery. Verify historical archives and game rule changes before drawing conclusions.
