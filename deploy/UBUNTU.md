# Deploy on Ubuntu (22.04 / 24.04 LTS)

**Uni Marburg HRZ (this server):** see **[uni-marburg-hrz.md](./uni-marburg-hrz.md)** —  
`workspace.online.uni-marburg.de` on `vhrz2425.hrz.uni-marburg.de`.

Step-by-step for a fresh Ubuntu server. Replace **`rooms.example.edu`** with your real hostname everywhere.

## Before you start

- SSH access with `sudo`
- DNS **A record** → server public IP
- SMTP credentials for OTP emails
- Copy this repo to the server (git clone, `rsync`, or CI artifact)

Suggested layout:

```text
/opt/mafex/
  mafexAll-main/    # backend
  mafexFe-main/     # frontend
  deploy/           # copy deploy/ from repo (or run from repo root)
```

---

## Step 1 — System packages (once, as root)

From the repo on the server:

```bash
cd /opt/mafex/BookingSystem   # or wherever you cloned it
sudo DOMAIN=rooms.example.edu bash deploy/install-server.sh
```

This installs:

- Python 3, venv, Nginx, PostgreSQL, UFW
- **Node.js 20** (via NodeSource)
- Linux user `mafex`, database `mafex`, Nginx site, systemd units
- Firewall: SSH + HTTP/HTTPS only

---

## Step 2 — Upload application code

Example with `rsync` from your PC:

```bash
rsync -avz --exclude node_modules --exclude .venv --exclude .next \
  ./mafexAll-main ./mafexFe-main ./deploy \
  user@SERVER:/opt/mafex/
```

Or on the server:

```bash
sudo mkdir -p /opt/mafex
sudo chown mafex:mafex /opt/mafex
sudo -u mafex git clone <your-repo-url> /opt/mafex/src
# then copy/link mafexAll-main and mafexFe-main into /opt/mafex/
```

---

## Step 3 — Configure backend `.env`

```bash
sudo -u mafex nano /opt/mafex/mafexAll-main/.env
```

Minimum:

```env
DATABASE_URL=postgresql+psycopg://mafex:YOUR_DB_PASSWORD@localhost:5432/mafex
JWT_SECRET_KEY=paste-output-of-openssl-rand-hex-32
SMTP_HOST=smtp.staff.uni-marburg.de
SMTP_PORT=587
SMTP_USERNAME=mafex-ws@staff.uni-marburg.de
SMTP_PASSWORD=your-smtp-password
SMTP_FROM_EMAIL=mafex-ws@staff.uni-marburg.de
SMTP_USE_TLS=true
STORAGE_ROOT=/opt/mafex/mafexAll-main/storage
CORS_ORIGINS=https://rooms.example.edu
```

Generate JWT:

```bash
openssl rand -hex 32
```

---

## Step 4 — Build app (as `mafex` user)

```bash
sudo -u mafex DOMAIN=https://rooms.example.edu bash /opt/mafex/deploy/setup-app.sh
```

Creates venv, runs migrations, builds Next.js with the correct API URL.

Create admin:

```bash
sudo -u mafex bash -c 'cd /opt/mafex/mafexAll-main && source .venv/bin/activate && PYTHONPATH=. python -m app.scripts.create_admin --email you@uni-marburg.de --name "Admin"'
```

---

## Step 5 — Start services

```bash
sudo systemctl enable --now mafex-api mafex-web nginx
sudo systemctl status mafex-api mafex-web nginx
```

Logs:

```bash
journalctl -u mafex-api -f
journalctl -u mafex-web -f
```

---

## Step 6 — HTTPS (Let’s Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d rooms.example.edu
```

Certbot updates Nginx for TLS and auto-renewal.

---

## Step 7 — Verify

| Check | Command / URL |
|--------|----------------|
| API health | `curl https://rooms.example.edu/health` |
| Site | Browser → `https://rooms.example.edu/` → login → `/findroom` |
| API docs | `https://rooms.example.edu/api/v1/docs` |
| OTP email | Sign up / log in |

---

## Updates after code changes

**Backend:**

```bash
sudo -u mafex bash -c 'cd /opt/mafex/mafexAll-main && source .venv/bin/activate && git pull && pip install -r requirements.txt && PYTHONPATH=. alembic upgrade head'
sudo systemctl restart mafex-api
```

**Frontend:**

```bash
sudo -u mafex bash -c 'cd /opt/mafex/mafexFe-main && git pull && npm ci && npm run build'
sudo systemctl restart mafex-web
```

---

## Common Ubuntu issues

| Problem | Fix |
|---------|-----|
| `nginx: command not found` | `sudo apt install nginx` |
| Node too old for Next | Use `install-server.sh` (Node 20) |
| `502 Bad Gateway` | `journalctl -u mafex-api` — DB URL, venv, `.env` |
| Permission on `storage/` | `sudo chown -R mafex:mafex /opt/mafex/mafexAll-main/storage` |
| Postgres connection refused | `sudo systemctl enable --now postgresql` |

See also [README.md](./README.md) for architecture and troubleshooting.
