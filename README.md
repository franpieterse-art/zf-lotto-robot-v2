# ZF Lotto Robot V39 — Learn Button (future predictions)

New Learn button analyses which original predictions were correct, which selected numbers were wrong, and which winning numbers were missed. It compares historical feature profiles (20, 60, 150, 300-draw smoothed frequency and gap) of winning vs incorrect selections, then saves small capped weight updates in SQLite.

When predicting a LATER date, the robot loads only lessons from dates strictly BEFORE that date and applies the learned feature adjustments. The original draw never trains its own prediction. Repeating Learn for the same session is blocked. Ten rows, all eligible numbers, and blind Predict→Reveal retained.

**How to test:** Predict an old draw → Reveal → LEARN FROM CORRECT & WRONG NUMBERS → select a later draw → Predict again. The status displays how many saved lessons were applied. Learning from past lottery outcomes cannot reliably beat fair random draws; do not interpret a match as evidence of causation.

Learning is stored in `lotto_history.sqlite3` via `LOTTO_DB_PATH`. Render's ephemeral filesystem loses data on redeploy unless a persistent disk or external database is configured. Existing retrospective V38 endpoint remains for compatibility, but the new Learn button uses `/api/learn`.
