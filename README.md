# ZF Lotto Robot V32 — Improved Formula
V32 uses all eligible numbers and a six-factor, smoothed ensemble:
long-term frequency 25%, multi-horizon recent frequency 25%, momentum 15%, gap 5%, pair co-occurrence 15%, stability 15%.

Changes: Bayesian-style smoothing, 20/60/150 draw lookbacks, historical number eligibility, deterministic five unique prediction rows, local-only Predict/Reveal/Backtest (no network waiting), date-based walk-forward testing with past-only data. No draw result is fabricated.

Install: Extract ZIP, replace repository files, commit, redeploy Render, Ctrl+F5.
No formula can reliably predict an independent fair lottery draw. Backtest against random selections before claiming improvement.
