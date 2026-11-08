# ZF Lotto Robot — online historical results

Deploy on Render as a **Web Service**, not a Static Site. Connect the GitHub repository, set runtime Python, start command `python server.py`, and add the environment variable `RESULTSZA_API_KEY` with a key obtained from https://resultsza.co.za/api_docs . Never put the key in `index.html` or commit it to GitHub.

The app retrieves prior draws from ResultsZA and uses only earlier dates for the prediction. The actual selected draw is requested only after Reveal is pressed. No results are invented. A third-party API key, coverage, provider uptime and quota are required; dates are limited by the provider's archive. The server fetches up to 80 earlier draws, so first prediction may be slow and may use substantial API quota. The frequency/recency heuristic is not a proven way to beat random lottery odds.
