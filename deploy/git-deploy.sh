#!/usr/bin/env bash
# Pull latest code from GitHub and redeploy on the HRZ server.
# Run on the server (as a user with sudo), after one-time setup in GITHUB.md.
#
#   sudo bash /opt/mafex/deploy/git-deploy.sh
#   sudo bash /opt/mafex/deploy/git-deploy.sh main
set -eu

APP=/opt/mafex
BRANCH="${1:-main}"
BACKEND="$APP/mafexAll-main"
FRONTEND="$APP/mafexFe-main"

if [[ ! -d "$APP/.git" ]]; then
  echo "Git not initialized in $APP — run deploy/bootstrap-git-server.sh first."
  exit 1
fi

echo "==> Backing up env files"
cp "$BACKEND/.env" /tmp/mafex-backend.env.bak 2>/dev/null || true
cp "$FRONTEND/.env.local" /tmp/mafex-frontend.env.bak 2>/dev/null || true

echo "==> Pulling origin/$BRANCH"
sudo -u mafex bash -lc "cd $APP && git fetch origin && git reset --hard origin/$BRANCH"

cp /tmp/mafex-backend.env.bak "$BACKEND/.env" 2>/dev/null || true
cp /tmp/mafex-frontend.env.bak "$FRONTEND/.env.local" 2>/dev/null || true
sudo chown -R mafex:mafex "$APP"

echo "==> Backend: deps + migrations"
sudo -u mafex bash -lc "cd $BACKEND && source .venv/bin/activate && pip install -q -r requirements.txt && export PYTHONPATH=$BACKEND && alembic upgrade head"

echo "==> Frontend: build"
sudo -u mafex bash -lc "cd $FRONTEND && npm ci && npm run build"

echo "==> Restart services"
sudo systemctl restart mafex-api mafex-web
sleep 2
curl -s http://127.0.0.1:8000/health
echo
systemctl is-active mafex-api mafex-web nginx
