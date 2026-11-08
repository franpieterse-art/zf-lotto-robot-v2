# ZF Lotto Robot V24 — Three results panels

Based on the user-provided V23 package, including its three historical CSV archives.

## Change
After **Predict → Reveal**, show three panels: **1. Main LOTTO**, **2. LOTTO PLUS 1**, and **3. LOTTO PLUS 2 / LOTTO 5 MAX**. The third panel uses a verified PLUS 2 record for the selected date when available; otherwise it uses a verified 5 MAX record. The heading shows the **actual source game** to avoid falsely presenting a 5 MAX draw as a PLUS 2 draw. If neither is stored, it shows unavailable. The backend continues to store PLUS 2 and 5 MAX independently, and bonus balls are tied to the correct game.

All five prediction rows are compared to each of the three available result panels. The engine still trains only on all earlier Main LOTTO results; all valid numbers are eligible. Prediction and Reveal do not make network calls.

## Deploy
Extract and upload all 10 files to the GitHub repository root, replacing matching files. Render build: `pip install -r requirements.txt`; start: `gunicorn server:app --bind 0.0.0.0:$PORT --timeout 120`. Hard refresh browser with Ctrl+F5.

## Limitations
Historical files were supplied by the user, not independently verified against official results. The online archive/API connection is unverified. LOTTO 5 MAX and LOTTO PLUS 2 are distinct games, not identical draws. Prediction heuristics do not increase the mathematical odds of a fair Lotto combination.
