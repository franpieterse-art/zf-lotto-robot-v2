# ZF Lotto Robot V12 — exclude five hottest, include ten coldest

The previous V11 exclusion of **10 coldest** numbers is removed entirely. All 52 numbers are evaluated for frequency, and the **five most frequently drawn** numbers across the available verified Main LOTTO draws strictly before the selected prediction date are excluded from all five prediction rows. Thus 47 numbers remain eligible, including all ten numbers formerly classified as coldest unless they independently rank among the five hottest under the new rule.

Ties are broken by most recent appearance, then lowest number. The five excluded numbers are displayed on the Predictions screen. All five prediction strategies, date-based Predict → Reveal → Compare for Main Lotto, Lotto Plus 1 and Lotto Plus 2, and chronological backtesting remain. Each historical test recomputes its hot-number exclusion using earlier draws only.

**Note:** No mathematical advantage is established by excluding frequently drawn numbers. Independent fair draws have no memory.

## Deploy
Upload the six files to the root of the existing GitHub repository and commit. Render build: `pip install -r requirements.txt`. Render start: `gunicorn server:app --bind 0.0.0.0:$PORT --timeout 120`. The external historical data sources inherited from V11 remain unverified on Render; missing results are never fabricated.
