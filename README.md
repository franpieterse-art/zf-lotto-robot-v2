# ZF Lotto Robot V17 — All Numbers Allowed

Based on the V16 adaptive prediction package. **No hot or cold numbers are excluded.** Every number from 1 through the selected date’s configured valid ball maximum is eligible in all five prediction rows. The adaptive window validation also evaluates all eligible numbers without exclusion.

Preserved: five strategies, adaptive fifth row, date selection, Predict → Reveal → Compare for Main LOTTO, LOTTO PLUS 1, LOTTO PLUS 2, historical CSV import and cache, and walk-forward backtesting. Predictions use only historical draws earlier than the selected date.

To deploy, upload all eight files to the existing GitHub repository root. Render build: `pip install -r requirements.txt`; start: `gunicorn server:app --bind 0.0.0.0:$PORT --timeout 120`.

No statistical method is known to improve jackpot odds for a fair lottery. Live API/data integrity not verified.
