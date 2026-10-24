# Host Riskora live

This guide deploys the current repository on **one Ubuntu VPS** with a domain name. Caddy serves the built React site over HTTPS and forwards `/api/*` to a local FastAPI process. SQLite, imported CSVs, and saved models stay on the VPS's persistent disk. This is suitable for a small, read-only public demo with one trusted operator; the app has one shared management token rather than user accounts. For a temporary one-service demo, see the [Render guide](DEPLOY-RENDER-SIMPLE.md).

```text
Browser → HTTPS/Caddy → frontend/dist
                      ↘ /api/* → FastAPI on 127.0.0.1:8001 → /var/lib/riskora
```

The browser uses relative `/api/v1` URLs, so the site and API must be served from the same domain with this layout. Vite's development proxy is not part of the production build. [Vite's production guide](https://vite.dev/guide/build) describes the static `dist` output; [Caddy's routing guide](https://caddyserver.com/docs/caddyfile/directives/route) covers the API and static-site split.

## Before you start

- Use a non-root Linux login with `sudo`, Ubuntu with Python 3.11+, and Node.js 20.19+ or 22.12+ as required by [Vite](https://vite.dev/guide/). Check `python3 --version` and `node --version` before installing dependencies.
- Point an `A` record for your domain to the VPS. If you publish an `AAAA` record, its IPv6 address must reach the same VPS. Allow inbound ports **80 and 443** through the VPS provider's firewall; retain SSH access. Keep port **8001** private. Caddy needs the domain and these ports for [automatic HTTPS](https://caddyserver.com/docs/quick-starts/https).
- Commit and push the code and input files you intend to deploy. `git clone` cannot see uncommitted local changes. The SQLite database and `data/absl_flexi_cap/downloads/` are ignored by Git.
- Decide what visitors may see: the API's read endpoints are public. Do not load private holdings, market data, or licensed material into a public instance without the right to publish it.

Commands below are for a Bash shell on the VPS. Replace `example.com` with your domain, `YOUR_LINUX_USER` with the non-root account that will run the API, and `YOUR_LINUX_GROUP` with that account's primary group (`id -gn`).

## 1. Install the app

Install system packages, then install a compatible Node.js release from the [official Node.js downloads](https://nodejs.org/en/download). Verify the version before building.

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip curl openssl
node --version
```

Clone the repository into a path the web server can read. If your repository is private, use your normal authenticated Git URL.

```bash
sudo install -d -o "$USER" -g "$(id -gn)" /srv/riskora
git clone https://github.com/ClashLex/Riskora.git /srv/riskora
cd /srv/riskora/backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd ../frontend
npm ci
npm run build
```

The build should create `/srv/riskora/frontend/dist/index.html`. Install Caddy using its [official Ubuntu package instructions](https://caddyserver.com/docs/install#debian-ubuntu-raspbian); the package starts a `caddy` systemd service.

## 2. Put application data and secrets outside the checkout

Run the API under your non-root login and give that login a persistent data directory:

```bash
sudo install -d -o "$USER" -g "$(id -gn)" -m 700 /var/lib/riskora
sudoedit /etc/riskora.env
sudo chmod 600 /etc/riskora.env
```

Put these lines in `/etc/riskora.env`, replacing the domain and secret. Generate a secret with `openssl rand -hex 32`. Do not commit this file or put the token in frontend code.

```dotenv
RISKORA_ADMIN_TOKEN=REPLACE_WITH_RANDOM_HEX_SECRET
RISKORA_DB=/var/lib/riskora/riskora.sqlite3
RISKORA_UPLOAD_DIR=/var/lib/riskora/uploads
CORS_ORIGINS=https://example.com
```

The model files are written to `/var/lib/riskora/models/`, beside the SQLite database. Optional `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` belong in this server-only file if you enable event extraction. The app does not automatically read `backend/.env.example`.

## 3. Run FastAPI with systemd

Create `/etc/systemd/system/riskora.service` with `sudoedit`:

```ini
[Unit]
Description=Riskora API
After=network.target

[Service]
User=YOUR_LINUX_USER
Group=YOUR_LINUX_GROUP
WorkingDirectory=/srv/riskora/backend
EnvironmentFile=/etc/riskora.env
ExecStart=/srv/riskora/backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Use one API process for this SQLite-backed prototype. Then start it and check the local health endpoint:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now riskora
curl -fsS http://127.0.0.1:8001/health
```

If it fails, inspect `sudo journalctl -u riskora -n 100 --no-pager`. The service account must be able to write `/var/lib/riskora`.

## 4. Serve the site and proxy the API

Replace `/etc/caddy/Caddyfile` with this configuration, using your real domain:

```caddyfile
example.com {
    encode zstd gzip

    handle /api/* {
        reverse_proxy 127.0.0.1:8001
    }

    handle {
        root * /srv/riskora/frontend/dist
        try_files {path} /index.html
        file_server
    }
}
```

`handle` keeps API requests out of the single-page app fallback, and `reverse_proxy` preserves `/api/v1/...` for FastAPI. Caddy serves only the built `dist` directory; `/health` and `/docs` stay available locally on port 8001. See the [Caddy `handle`/routing example](https://caddyserver.com/docs/caddyfile/directives/route) and [reverse proxy reference](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).

```bash
sudo -u caddy test -r /srv/riskora/frontend/dist/index.html
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
curl -fsS https://example.com/api/v1/overview
```

If the first check fails, give the `caddy` user read access to `frontend/dist` and traversal access to its parent directories. Caddy's [service guide](https://caddyserver.com/docs/running#using-the-service) explains its filesystem permissions and logs. Open `https://example.com` and check the browser's Network tab: `/api/v1/overview` should return JSON, not `index.html`.

## 5. Load data and verify the demo

The new server starts with an empty database. The two supplied ABSL snapshots can be loaded from the repository checkout. Run this as the same Linux login used by the API service:

```bash
cd /srv/riskora
RISKORA_DB=/var/lib/riskora/riskora.sqlite3 \
RISKORA_UPLOAD_DIR=/var/lib/riskora/uploads \
backend/.venv/bin/python scripts/load_supplied_disclosures.py
```

The loader validates the workbooks and CSVs before importing. These snapshots remain **Observed** and cannot train a real-data model because their exact publication dates are unverified. To demonstrate training and rankings, privately enter the management token in **Data management**, load the fictional sample, and train it from **Evaluation**. Visitors can then inspect its saved results without the token. Do not publish or share the token.

Check the **Overview**, **Fund explorer**, and **Evaluation** screens. If predictions are unavailable, inspect **Evaluation → Training readiness**; a live URL alone does not create the historical data needed for a model.

## Updates and backups

Before updating, back up `/var/lib/riskora`: use SQLite's [online backup API](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup) for `riskora.sqlite3`, and preserve the `uploads/` and `models/` directories. Keep a copy off the VPS. Model artifact paths are stored in the database, so restore to the same directory or update those paths together.

After pushing a new version, update from the VPS:

```bash
cd /srv/riskora
git pull --ff-only
backend/.venv/bin/python -m pip install -r backend/requirements.txt
cd frontend
npm ci
npm run build
sudo systemctl restart riskora
```

Reload Caddy only if its configuration changes. Use `sudo journalctl -u riskora -n 100 --no-pager` and `sudo journalctl -u caddy -n 100 --no-pager` to investigate failures. For a multi-user or write-heavy service, add individual authentication, operational controls, and a database designed for concurrent production use before inviting general users.
