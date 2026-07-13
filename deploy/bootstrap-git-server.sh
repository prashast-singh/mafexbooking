#!/usr/bin/env bash
# One-time: connect /opt/mafex to GitHub (keeps existing .env files).
#
#   export GITHUB_REPO=https://github.com/prashast-singh/mafexbooking.git
#   sudo bash deploy/bootstrap-git-server.sh
set -eu

APP=/opt/mafex
REPO="${GITHUB_REPO:-https://github.com/prashast-singh/mafexbooking.git}"
BRANCH="${GITHUB_BRANCH:-main}"
BACKEND="$APP/mafexAll-main"
FRONTEND="$APP/mafexFe-main"

if [[ ! -d "$BACKEND" || ! -d "$FRONTEND" ]]; then
  echo "Expected $BACKEND and $FRONTEND — run install-server.sh / setup-app.sh first, or clone fresh:"
  echo "  sudo mkdir -p $APP && sudo chown mafex:mafex $APP"
  echo "  sudo -u mafex git clone $REPO $APP"
  exit 1
fi

echo "==> Backing up env files"
cp "$BACKEND/.env" /tmp/mafex-backend.env.bak 2>/dev/null || true
cp "$FRONTEND/.env.local" /tmp/mafex-frontend.env.bak 2>/dev/null || true

if [[ -d "$APP/.git" ]]; then
  echo "Git already initialized in $APP"
  sudo -u mafex bash -lc "cd $APP && git remote set-url origin $REPO || git remote add origin $REPO"
else
  echo "==> Initializing git in $APP"
  sudo -u mafex bash -lc "cd $APP && git init && git remote add origin $REPO"
fi

echo "==> Fetching $BRANCH (first deploy must be pushed to GitHub already)"
sudo -u mafex bash -lc "cd $APP && git fetch origin $BRANCH && git checkout -B $BRANCH origin/$BRANCH"

cp /tmp/mafex-backend.env.bak "$BACKEND/.env" 2>/dev/null || true
cp /tmp/mafex-frontend.env.bak "$FRONTEND/.env.local" 2>/dev/null || true
sudo chown -R mafex:mafex "$APP"

echo "Done. Future deploys: sudo bash $APP/deploy/git-deploy.sh"
