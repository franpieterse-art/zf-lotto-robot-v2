# ZF Lotto Robot V6 automatic history patch
Replace **server.py** and **requirements.txt** in the existing GitHub repository. Keep your existing `engine.py` and `index.html` unchanged.

Render build: `pip install -r requirements.txt`
Render start: `gunicorn server:app --bind 0.0.0.0:$PORT --timeout 120`

The server attempts to load 2026+ results from https://www.lottery.co.za/lotto/results/2026 (and later years), using the first six balls only. It does not use a private API key. Third-party website structure or access restrictions may break extraction; `/api/status` returns `sync_error` if so. Archive is cached in memory for six hours and repopulated after restart. `/api/sync` forces refresh. A saved verified `draws.csv` remains supported as a fallback. Dates before June 2026 are deliberately blocked until rule-era handling is added; 2025 draws used a different number matrix. Results from the external archive are not independently certified as official. Predictions are not guaranteed to outperform chance.

The UI has not been modified. This patch has been syntax checked and parser-tested against representative HTML, but a live request from Render has not yet been tested.
