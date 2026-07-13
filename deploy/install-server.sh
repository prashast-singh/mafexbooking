#!/usr/bin/env bash
# Ubuntu 22.04 / 24.04 — install system packages, app user, nginx site, systemd units.
# Usage (on the server, from the BookingSystem repo):
#   sudo DOMAIN=rooms.example.edu bash deploy/install-server.sh
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/mafex}"
DOMAIN="${DOMAIN:-YOUR_DOMAIN}"
DEPLOY_USER="${DEPLOY_USER:-mafex}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$DOMAIN" == "YOUR_DOMAIN" ]]; then
  echo "Set your hostname: sudo DOMAIN=rooms.example.edu bash deploy/install-server.sh"
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run with sudo."
  exit 1
fi

echo "==> Ubuntu packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
  python3 python3-venv python3-pip \
  nginx postgresql postgresql-contrib \
  git rsync curl ca-certificates gnupg ufw

# Node.js 20 LTS (Next.js 15 needs a recent Node; Ubuntu apt node may be too old)
if ! command -v node &>/dev/null || [[ "$(node -v | cut -d. -f1 | tr -d v)" -lt 20 ]]; then
  echo "==> Node.js 20 (NodeSource)"
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi
echo "Node $(node -v), npm $(npm -v)"

echo "==> Firewall (UFW): allow SSH, HTTP, HTTPS"
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo "==> App user: $DEPLOY_USER"
if ! id -u "$DEPLOY_USER" &>/dev/null; then
  useradd -r -m -d "$APP_ROOT" -s /bin/bash "$DEPLOY_USER"
fi
mkdir -p "$APP_ROOT"
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$APP_ROOT"

echo "==> PostgreSQL database user (interactive password)"
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='mafex'" | grep -q 1; then
  sudo -u postgres createuser mafex --pwprompt
fi
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='mafex'" | grep -q 1; then
  sudo -u postgres createdb mafex -O mafex
fi

echo "==> systemd units"
sed "s|/opt/mafex|$APP_ROOT|g" "$SCRIPT_DIR/mafex-api.service" > /etc/systemd/system/mafex-api.service
sed "s|/opt/mafex|$APP_ROOT|g" "$SCRIPT_DIR/mafex-web.service" > /etc/systemd/system/mafex-web.service
# Run npm from NodeSource path
NODE_BIN="$(command -v npm)"
sed -i "s|/usr/bin/npm|$NODE_BIN|" /etc/systemd/system/mafex-web.service
systemctl daemon-reload

echo "==> Nginx site for $DOMAIN"
sed "s|YOUR_DOMAIN|$DOMAIN|g" "$SCRIPT_DIR/nginx-mafex.conf" > /etc/nginx/sites-available/mafex
ln -sf /etc/nginx/sites-available/mafex /etc/nginx/sites-enabled/mafex
rm -f /etc/nginx/sites-enabled/default
nginx -t

echo ""
echo "System prep done. Next (as your deploy user):"
echo "  1. Copy code to $APP_ROOT/mafexAll-main and $APP_ROOT/mafexFe-main"
echo "  2. sudo -u $DEPLOY_USER bash deploy/setup-app.sh"
echo "  3. sudo systemctl enable --now mafex-api mafex-web nginx"
echo "  4. sudo apt install -y certbot python3-certbot-nginx && sudo certbot --nginx -d $DOMAIN"
