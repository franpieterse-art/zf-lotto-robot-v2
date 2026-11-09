# ZF Lotto Robot V40 — Learning evaluation

Adds **TEST IF LEARNING WORKS**, a chronological, leakage-free comparison of 10 rows from: (1) original fixed V39 formula, (2) sequentially learning model, (3) random baseline. Each historical draw is predicted BEFORE the actual is used to update the learner. Reports show average matches per row, average best row, 3+ and 4+ matches. Every report is saved to SQLite in an `evaluations` table. Previous Predict / Reveal / Learn workflow remains.

Default evaluation is 30 draws (up to 100); can take time. Uses locally bundled Main Lotto CSV only, no external requests while predicting or testing. No claim of superior prediction until results are compared. SQLite on Render requires persistent disk via LOTTO_DB_PATH to survive restarts.

Deployment: extract ZIP to GitHub repository, commit, redeploy Render, Ctrl+F5.
