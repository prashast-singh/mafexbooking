#!/usr/bin/env bash
set -eu
APP=/opt/mafex
EXTRACT=/tmp/mafex-extract-$$
cp "$APP/mafexAll-main/.env" /tmp/mafex-backend.env.bak 2>/dev/null || true
cp "$APP/mafexFe-main/.env.local" /tmp/mafex-frontend.env.bak 2>/dev/null || true
mkdir -p "$EXTRACT"
tar -xzf /tmp/mafex-deploy.tar.gz -C "$EXTRACT"
sudo rsync -a --delete --exclude .venv --exclude .env --exclude .env.local --exclude node_modules --exclude .next "$EXTRACT/mafexAll-main/" "$APP/mafexAll-main/"
sudo rsync -a --delete --exclude node_modules --exclude .next --exclude .env.local "$EXTRACT/mafexFe-main/" "$APP/mafexFe-main/"
sudo rsync -a "$EXTRACT/deploy/" "$APP/deploy/"
rm -rf "$EXTRACT"
cp /tmp/mafex-backend.env.bak "$APP/mafexAll-main/.env" 2>/dev/null || true
cp /tmp/mafex-frontend.env.bak "$APP/mafexFe-main/.env.local" 2>/dev/null || true
sudo chown -R mafex:mafex "$APP"
sudo -u mafex bash -lc 'cd /opt/mafex/mafexAll-main && source .venv/bin/activate && pip install -q -r requirements.txt && export PYTHONPATH=/opt/mafex/mafexAll-main && alembic upgrade head'
sudo -u mafex bash -lc 'cd /opt/mafex/mafexFe-main && npm ci && npm run build'
sudo systemctl restart mafex-api mafex-web
sleep 2
curl -s http://127.0.0.1:8000/health
echo
systemctl is-active mafex-api mafex-web nginx
