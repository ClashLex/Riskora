# Simplest live demo: Render

This repository supports a **single Render web service**. The Docker build compiles React and runs FastAPI in the same service, so the frontend can use its existing relative `/api/v1` requests. You do not need a domain name, VPS, Caddy, or separate frontend/backend services. The checked-in Blueprint uses Render's free plan for a temporary public demo.

Current hosted demo: <https://riskora-demo.onrender.com/>. It serves only the fictional synthetic dataset; the supplied ABSL workbooks are not in this deployment image.

## Deploy

1. Push this version of the repository to GitHub. Make sure `Dockerfile`, `.dockerignore`, and `render.yaml` are at the repository root.
2. Sign in at <https://render.com> and connect the GitHub repository.
3. In Render, choose **New → Blueprint** (or create a service from the repository and select its `render.yaml`).
4. When prompted for `RISKORA_ADMIN_TOKEN`, enter a new long private random value and save it somewhere safe. Do not add it to source code, frontend settings, screenshots, or a public GitHub repository. For an existing Blueprint, set a missing secret in the Render service settings; `sync: false` prompts only when the Blueprint is first created.
5. Apply/deploy the Blueprint. After it finishes, Render gives the service an `https://...onrender.com` URL. Open that URL.
6. Check `/health`, **Evaluation**, and **Predictions** at the service URL. The synthetic sample and its monthly model are created on startup. Enter the admin token in **Data management** only when you need to import data or run a new training job.

## What you get

- One public URL for the React interface and FastAPI API.
- A `/health` check for the host.
- A clearly labelled synthetic sample and monthly model are recreated at startup when the ephemeral database is empty. Visitors can inspect the saved synthetic evaluation and rankings without the token.
- The image does not include the supplied ABSL workbooks or normalized holdings; it does not claim a real-market backtest.
- No external LLM key is required for the basic demo.

## Important free-hosting limits

Render's [free web service](https://render.com/docs/free) spins down after 15 minutes without traffic and loses local filesystem changes when it spins down, restarts, or redeploys. The synthetic sample and synthetic model are recreated at startup, but user-imported holdings, events, and any additional training runs are **not persistent**. This setup is for demos only. For persistent real-data usage, add a paid persistent disk or migrate storage to a managed database and object storage before relying on it.

Do not describe the synthetic demonstration as real-world prediction performance. The repository's real ABSL snapshots still need verified publication dates and a broader historical dataset before they can support a genuine backtest.
