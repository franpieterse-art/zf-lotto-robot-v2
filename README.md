# ZF Lotto Robot V37 — Learn From Historical Mistakes
This fixes the misconception that V36's deterministic output was learning from a revealed result. V37 displays error diagnostics after Reveal (best row, missed numbers, number coverage, and learned historical window weights). The model recalibrates using past-only walk-forward validation for each selected date. The target draw is never used to produce its own predictions, even after Reveal. Ten unique rows, all eligible numbers, and Reset generates alternative rows.
No persistent online model updates are claimed. A fair lottery is independent; learning from past errors does not ensure future prediction accuracy.
Install: extract files into GitHub repository, commit and redeploy Render, hard refresh.
