#!/usr/bin/env bash
# Ubuntu — install Python/Node deps, migrate DB, build frontend.
# Run as the app user after code is in /opt/mafex (or set APP_ROOT).
#
#   export DOMAIN=https://rooms.example.edu
#   bash deploy/setup-app.sh
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/mafex}"
BACKEND="$APP_ROOT/mafexAll-main"
FRONTEND="$APP_ROOT/mafexFe-main"
DOMAIN="${DOMAIN:-}"

if [[ ! -d "$BACKEND" || ! -d "$FRONTEND" ]]; then
  echo "Missing $BACKEND or $FRONTEND — copy the project first."
  exit 1
fi

echo "==> Backend venv + dependencies"
cd "$BACKEND"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created $BACKEND/.env — edit DATABASE_URL, JWT_SECRET_KEY, SMTP_* before continuing."
  echo "Generate JWT: openssl rand -hex 32"
  exit 1
fi

export PYTHONPATH="$BACKEND"
alembic upgrade head
python -m app.scripts.seed_bootstrap

echo "==> Frontend build"
cd "$FRONTEND"
if [[ ! -f .env.local ]]; then
  if [[ -z "$DOMAIN" ]]; then
    echo "Set DOMAIN=https://your-hostname then re-run, or create .env.local with:"
    echo "  NEXT_PUBLIC_API_BASE_URL=https://your-hostname/api/v1"
    exit 1
  fi
  echo "NEXT_PUBLIC_API_BASE_URL=${DOMAIN%/}/api/v1" > .env.local
  echo "API_INTERNAL_BASE_URL=http://127.0.0.1:8000/api/v1" >> .env.local
fi
npm ci
npm run build

echo ""
echo "Done. Create admin (once):"
echo "  cd $BACKEND && source .venv/bin/activate && PYTHONPATH=. python -m app.scripts.create_admin --email YOU@uni-marburg.de --name 'Admin'"
echo "Start services: sudo systemctl enable --now mafex-api mafex-web nginx"
