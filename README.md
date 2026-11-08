# ZF Lotto Robot V34 — Regime-aware formula

Weights: long-term frequency 20%; smoothed recent 25/75/200 draw rates 30%; momentum 10%; gap 5%; pair residual 10%; trend stability 15%; reversion 10%.

All eligible numbers are included. Uses only Main LOTTO results before the selected target date; preserves Predict → Reveal → Compare and walk-forward backtesting. Ten rows use diversity penalties to avoid excessive repetition. Local prediction requests do not fetch external sites.

Install: extract ZIP, upload all files to GitHub, commit, redeploy Render, hard-refresh browser.

No historical scoring formula changes the odds of a fair lottery draw. This is an experimental ranking method, not validated predictive advantage.

V34 change: Predict, Reveal, and walk-forward backtest now handle ten unique rows (instead of five). The seven-factor V33 formula is unchanged.
