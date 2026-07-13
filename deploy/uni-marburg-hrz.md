# Uni Marburg HRZ deployment (this project)

Server details for this workspace:

| Item | Value |
|------|--------|
| VM hostname | `vhrz2425.hrz.uni-marburg.de` |
| Public URL (alias) | **`https://workspace.online.uni-marburg.de`** |
| SSH / sudo user | `roetzc` |
| App install path | `/opt/mafex` (recommended) |

## Firewall (required before internet access)

HRZ requires an explicit **port 443** (HTTPS) approval for external access:

[Firewall request — port 443 (share.uni-marburg.de)](https://share.uni-marburg.de/de/hrz/uni-intern/firewall/freigabe-port-443)

Request **443** (and **80** if you use Let’s Encrypt HTTP-01). Do not expose **3000** or **8000** publicly — Nginx terminates HTTPS and proxies locally.

## Frontend API base URL (production)

Set **before** `npm run build` in `mafexFe-main/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=https://workspace.online.uni-marburg.de/api/v1
```

The browser will then call:

- API: `https://workspace.online.uni-marburg.de/api/v1/...`
- Images: `https://workspace.online.uni-marburg.de/storage/...`
- UI: `https://workspace.online.uni-marburg.de/` (redirects to login or `/findroom`)

## Backend `.env` (production)

```env
DATABASE_URL=postgresql+psycopg://mafex:STRONG_PASSWORD@localhost:5432/mafex
JWT_SECRET_KEY=<openssl rand -hex 32>
STORAGE_ROOT=/opt/mafex/mafexAll-main/storage
CORS_ORIGINS=https://workspace.online.uni-marburg.de

SMTP_HOST=smtp.staff.uni-marburg.de
SMTP_PORT=587
SMTP_USERNAME=mafex-ws@staff.uni-marburg.de
SMTP_PASSWORD=...
SMTP_FROM_EMAIL=mafex-ws@staff.uni-marburg.de
SMTP_USE_TLS=true
```

## Quick deploy commands (on the VM)

SSH (from campus VPN or allowed network):

```bash
ssh roetzc@vhrz2425.hrz.uni-marburg.de
```

**1. System prep (once, with sudo):**

```bash
cd /opt/mafex   # after copying BookingSystem there
sudo DOMAIN=workspace.online.uni-marburg.de bash deploy/install-server.sh
```

**2. Backend `.env`** — edit `/opt/mafex/mafexAll-main/.env` (see above).

**3. App build (as `mafex` user):**

```bash
sudo -u mafex DOMAIN=https://workspace.online.uni-marburg.de bash /opt/mafex/deploy/setup-app.sh
```

**4. Admin user:**

```bash
sudo -u mafex bash -c 'cd /opt/mafex/mafexAll-main && source .venv/bin/activate && PYTHONPATH=. python -m app.scripts.create_admin --email YOU@uni-marburg.de --name "Admin"'
```

**5. Start services:**

```bash
sudo systemctl enable --now mafex-api mafex-web nginx
```

**6. HTTPS** (after DNS alias points to VM and firewall 443 is open):

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d workspace.online.uni-marburg.de
```

Nginx config is generated with `server_name workspace.online.uni-marburg.de` when you pass `DOMAIN=` to `install-server.sh`.

## DNS

Ensure **`workspace.online.uni-marburg.de`** resolves to this VM’s IP (HRZ alias / DNS as provided by uni IT). Certbot and users rely on that name.

## Verify

| URL | Expected |
|-----|----------|
| `https://workspace.online.uni-marburg.de/health` | `{"status":"ok"}` |
| `https://workspace.online.uni-marburg.de/` | Login or redirect |
| `https://workspace.online.uni-marburg.de/api/v1/docs` | Swagger UI |

## Copy project from your PC (example)

```powershell
# From BookingSystem folder on Windows (adjust paths)
scp -r mafexAll-main mafexFe-main deploy roetzc@vhrz2425.hrz.uni-marburg.de:/tmp/mafex-upload/
# On server:
sudo mkdir -p /opt/mafex && sudo mv /tmp/mafex-upload/* /opt/mafex/ && sudo chown -R mafex:mafex /opt/mafex
```

Or `git clone` on the server if the repo is on GitHub/GitLab.

General Ubuntu steps: [UBUNTU.md](./UBUNTU.md).
