# ZF Lotto Robot V38 — Iterative Feedback

**Fix:** V37 only displayed error diagnostics; it did not feed revealed errors into the next same-date row generation. V38 adds a working **LEARN FROM MISTAKES → NEW 10 ROWS** button.

Workflow: Predict (blind, past only) → Reveal → inspect errors → Learn (10 new rows with feedback from the revealed winning numbers) → Learn again for another iteration. The server keeps per-session feedback and iteration count (up to 20) until restart. Each iteration shows its results and remains visible. A different date starts a fresh blind prediction.

**Crucial:** revised same-date rows use the known winning numbers and are labeled **HINDSIGHT**, not legitimate predictions. Blind backtesting still excludes the target draw. Repeated learning on a known result is not evidence of future accuracy. Model weights are not permanently saved across Render restarts.

Install: extract ZIP to GitHub repository, commit, redeploy Render, Ctrl+F5.
