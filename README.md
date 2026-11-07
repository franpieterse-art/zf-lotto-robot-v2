# ZF Lotto Robot — corrected flow
1. Select a historical draw date.
2. Click PREDICT to lock six numbers calculated only from earlier records.
3. Click REVEAL REAL NUMBERS to compare against the bundled demo archive.
4. View matching numbers and match percentage.

## Deploy
Upload index.html and render.yaml to the root of a GitHub repository. On Render choose **Static Site**, build command `echo Ready`, publish directory `.`.

## Important limitation
This version does NOT perform a live online search. It has a small, unverified bundled archive for demonstrating the correct workflow. Never describe the archive as verified without independently checking each draw. An online results provider/backend is needed for arbitrary dates. Lottery draws are random and historical analysis cannot guarantee improved accuracy.
