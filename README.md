# ZF Lotto Robot V21 — All Previous Historical Results

Built from V20. All five strategies, all numbers eligible, Predict → Reveal → Compare, three result panels, and historical CSV are retained.

## Change requested
For any chosen historical prediction date, use **every stored verified Main LOTTO result before that date**, including older game-rule periods. The previous same-era date restriction has been removed. Never include the chosen draw or any later result in prediction or walk-forward training.

The valid prediction number range still follows the selected draw date's game rules. Older draws may have different ball pools (e.g., 6/58 vs 6/52), so the engine only scores eligible numbers in the current pool. Cross-era frequencies can be biased; using more draws does **not** guarantee improved prediction quality. The archive's completeness and rule boundaries require independent verification.

No external API request occurs during Predict. Use Retry Historical Download to refresh data separately.

## Install
Upload the eight files from this ZIP to the GitHub repository root, replacing V20. Render build: `pip install -r requirements.txt`; start: `gunicorn server:app --bind 0.0.0.0:$PORT --timeout 120`.
