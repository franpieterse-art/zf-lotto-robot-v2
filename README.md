# ZF Lotto Robot V11 — three results auto-download fix

V9 attempted unverified BetTip Plus 1/Plus 2 URLs and displayed unavailable results. V10 adds a combined-archive HTML downloader for all three games from https://lottology.com/south-africa-lotto/draws . The combined archive contains columns `draws`, `plus_1` and `plus_2`. A strict parser matches dates and columns, validates each six-number draw, and refuses conflicting results. BetTip is retained as a fallback. No API key is required for the HTML archive.

**Important:** Source accessibility from Render is not verified; the page may block automated requests or change structure. The combined archive was observed to be behind the latest draw; it is not guaranteed current. The archive contains older 6/58 results, so V10 only imports dates from 2026-06-04 onward into the current 6/52 prediction engine. The user can upload verified CSVs for missing dates. Future data is never included in the training subset for a selected historical date. The ten cold-number exclusions and five strategies remain.

Deploy six files to GitHub root, build `pip install -r requirements.txt`, start `gunicorn server:app --bind 0.0.0.0:$PORT --timeout 120`.

## V11 change: ten coldest numbers excluded
For every prediction date, rank all 52 numbers by their total appearances across all available verified **Main Lotto** draws strictly before that date. Exclude the 10 least frequent numbers from **all five** predicted rows. Ties are resolved by longest absence, then smallest number. This leaves 42 eligible numbers. Walk-forward backtesting applies the same date-specific rule without future data. Reveal still compares all five rows with Main Lotto, Plus 1, and Plus 2 where verified results are available.

**Statistical caution:** In a fair lottery, cold numbers are not less likely to occur next. This filter does not improve the theoretical odds of a specific six-number combination.
