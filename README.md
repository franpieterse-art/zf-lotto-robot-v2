# ZF Lotto Robot V2 — GitHub + Render

This is a static HTML app; no Node.js, Python server, database, or API key is required.

## Publish on GitHub
1. Create a new GitHub repository named `zf-lotto-robot-v2`.
2. Upload **the contents of this folder** (`index.html`, `render.yaml`, and `README.md`) to the repository root and commit.

## Deploy on Render
1. Sign into https://dashboard.render.com and connect your GitHub account.
2. Choose **New > Blueprint** and select your `zf-lotto-robot-v2` repository.
3. Render reads `render.yaml` and provisions the static site. Approve the deployment.
4. Wait for the deployment to finish; open the `onrender.com` URL displayed in your Render dashboard.

Alternative: **New > Static Site**, choose repository, set Build Command to `echo ready`, Publish Directory to `.`, and deploy.

## Use
Import a CSV containing actual historic SA Lotto results with header:
`date,n1,n2,n3,n4,n5,n6`

Use ISO dates `YYYY-MM-DD`; each draw must contain six distinct numbers from 1 to 52. The app does not download results automatically. Only prior draws are used when predicting an earlier date. Sample/demo data, if used, is not evidence of forecasting performance.

Lottery draws are random. This app cannot guarantee wins or 80% accuracy.
