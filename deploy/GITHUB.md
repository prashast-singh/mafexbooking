# Deploy via GitHub

Repo: [prashast-singh/mafexbooking](https://github.com/prashast-singh/mafexbooking)

This is faster than uploading a tarball over SSH. The server only runs `git pull` + build.

## 1. Push from your machine (once, then after each change)

```bash
cd BookingSystem
git init
git remote add origin https://github.com/prashast-singh/mafexbooking.git
git add .
git commit -m "Initial commit"
git branch -M main
git push -u origin main
```

`.env` and `.env.local` are **not** committed. Keep them only on the server.

## 2. One-time server setup

SSH to the server, then:

```bash
sudo bash /opt/mafex/deploy/bootstrap-git-server.sh
```

If `/opt/mafex` does not exist yet (fresh server):

```bash
sudo mkdir -p /opt/mafex
sudo chown mafex:mafex /opt/mafex
sudo -u mafex git clone https://github.com/prashast-singh/mafexbooking.git /opt/mafex
# configure .env / .env.local, then:
sudo bash /opt/mafex/deploy/setup-app.sh
```

## 3. Deploy updates

After you `git push` to `main`:

```bash
ssh roetzc@vhrz2425.hrz.uni-marburg.de
sudo bash /opt/mafex/deploy/git-deploy.sh
```

Or in one line from your PC:

```bash
ssh -i ~/.ssh/bookingServerSSHKey roetzc@vhrz2425.hrz.uni-marburg.de "sudo bash /opt/mafex/deploy/git-deploy.sh"
```

## Workflow summary

| Step | Where | Command |
|------|--------|---------|
| Change code | Local | edit + test |
| Publish | Local | `git add . && git commit -m "..." && git push` |
| Deploy | Server | `sudo bash /opt/mafex/deploy/git-deploy.sh` |
