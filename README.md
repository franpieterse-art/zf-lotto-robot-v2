# ZF Lotto Robot V36 — Adaptive Evidence + Diversity

10 prediction rows, all eligible numbers, Predict / Reveal / Compare, walk-forward backtesting.

New experimental formula: compare four smoothed frequency windows (20, 60, 150, 300 historical draws) on up to 12 past-only holdouts; mildly adjust their weights based on historical match counts; combine their normalized scores; diversify the 10 rows using number/pair repetition penalties.

**Caution:** A fair lottery draw is independent of earlier results. Calibration is not evidence of predictive power; compare V36 with random rows on unseen historical draws. No external network calls during prediction.

Install: extract, replace GitHub repository files, commit, redeploy Render, refresh Ctrl+F5.
