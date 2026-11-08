ZF Lotto V3 prediction engine (standalone upgrade)

Files:
- zf_prediction_v3.py: prediction strategies, walk-forward testing, strategy selection
- test_zf_prediction_v3.py: automated tests

To test: python -m unittest -v test_zf_prediction_v3.py

To integrate in existing server.py (do not replace your server.py blindly):
from zf_prediction_v3 import prediction_for_date, backtest, matches

The API adapter must convert ResultsZA responses into a list of:
  {"date":"2026-07-29", "numbers":[1,2,3,4,5,6]}
Call prediction_for_date(draws, "2026-08-01", rows=5).
The response has 'predictions', 'method', 'training_draws', and 'validation'.
Store predictions before revealing actual winning numbers; reveal should use a separately fetched verified draw and call matches(predictions, actual).

IMPORTANT: Historical results may have multiple draws on the same date (e.g. separate games). This engine assumes one SA Lotto 6/52 draw per date. Filter for Lotto only, not Lotto Plus or Daily Lotto.
No claims of predictive edge; compare to random baseline. Never use future draws in training or model selection.
No budget or ticket spending features included.
