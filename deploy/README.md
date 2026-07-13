# Server deployment (Mafex room booking)

**Ubuntu server?** Use the focused guide: **[UBUNTU.md](./UBUNTU.md)**.

Deploy **PostgreSQL**, **FastAPI backend** (`mafexAll-main`), **Next.js frontend** (`mafexFe-main`), and **Nginx** as the public entry point.

## Architecture

```text
https://YOUR_DOMAIN
        │
     Nginx :443
        ├── /api/v1, /storage, /health  → 127.0.0.1:8000 (uvicorn)
        └── /*                          → 127.0.0.1:3000 (next start)
PostgreSQL :5432 (localhost only)
```

## 1. Prepare the server (Ubuntu)

- **Ubuntu 22.04 or 24.04 LTS** recommended
- DNS `A` record pointing `YOUR_DOMAIN` to the server

One-command system prep:

```bash
sudo DOMAIN=your.hostname.edu bash deploy/install-server.sh
```

Then app setup as user `mafex`:

```bash
sudo -u mafex DOMAIN=https://your.hostname.edu bash deploy/setup-app.sh
```

## 2. PostgreSQL

```bash
sudo -u postgres createuser mafex --pwprompt
sudo -u postgres createdb mafex -O mafex
```

## 3. Backend (`mafexAll-main`)

```bash
sudo mkdir -p /opt/mafex
sudo chown $USER:$USER /opt/mafex
cd /opt/mafex
# git clone or copy mafexAll-main here

cd mafexAll-main
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env: DATABASE_URL, JWT_SECRET_KEY, SMTP_*, CORS_ORIGINS=https://YOUR_DOMAIN

export PYTHONPATH=.
alembic upgrade head
python -m app.scripts.seed_bootstrap
python -m app.scripts.create_admin --email admin@example.com --name "Admin"

# Quick test
uvicorn app.main:app --host 127.0.0.1 --port 8000
curl http://127.0.0.1:8000/health
```

**`.env` production notes**

| Variable | Example |
|----------|---------|
| `DATABASE_URL` | `postgresql+psycopg://mafex:***@localhost:5432/mafex` |
| `JWT_SECRET_KEY` | `openssl rand -hex 32` |
| `CORS_ORIGINS` | `https://YOUR_DOMAIN` (add `http://localhost:3000` only if needed) |
| `STORAGE_ROOT` | `/opt/mafex/mafexAll-main/storage` (absolute path recommended) |

## 4. Frontend (`mafexFe-main`)

```bash
cd /opt/mafex/mafexFe-main
cp .env.production.example .env.local
# Set NEXT_PUBLIC_API_BASE_URL=https://YOUR_DOMAIN/api/v1

npm ci
npm run build
npm run start:prod
# Test: curl -I http://127.0.0.1:3000
```

Rebuild frontend whenever `NEXT_PUBLIC_API_BASE_URL` changes.

## 5. Systemd services

Adjust paths in `mafex-api.service` / `mafex-web.service` if not using `/opt/mafex`.

```bash
sudo cp deploy/mafex-api.service /etc/systemd/system/
sudo cp deploy/mafex-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mafex-api mafex-web
sudo systemctl status mafex-api mafex-web
```

Run services as a dedicated user (`mafex`) and `chown` app directories accordingly.

## 6. Nginx

```bash
sudo cp deploy/nginx-mafex.conf /etc/nginx/sites-available/mafex
# Edit YOUR_DOMAIN in the file
sudo ln -s /etc/nginx/sites-available/mafex /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

HTTPS:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d YOUR_DOMAIN
```

## 7. Verify

| URL | Expected |
|-----|----------|
| `https://YOUR_DOMAIN/` | Redirect to login or `/findroom` |
| `https://YOUR_DOMAIN/api/v1/docs` | OpenAPI UI |
| `https://YOUR_DOMAIN/health` | `{"status":"ok"}` |
| Signup / login | OTP email sent |
| Book a room | Works for approved users |

## Troubleshooting

- **API 502** — `systemctl status mafex-api`, check `.env` and Postgres.
- **Blank frontend** — `journalctl -u mafex-web`, confirm `npm run build` succeeded.
- **CORS errors** — add `https://YOUR_DOMAIN` to `CORS_ORIGINS` in backend `.env`, restart API.
- **Images 404** — check `STORAGE_ROOT`, Nginx `/storage/` proxy, file permissions.
- **OTP not sent** — verify SMTP from server (`telnet smtp.host 587` or logs).

## File map

| File | Purpose |
|------|---------|
| `nginx-mafex.conf` | Reverse proxy |
| `mafex-api.service` | Backend daemon |
| `mafex-web.service` | Frontend daemon |
| `install-server.sh` | Optional bootstrap |
