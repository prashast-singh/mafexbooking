# Mafex Room Booking

- **Backend:** `mafexAll-main` (FastAPI)
- **Frontend:** `mafexFe-main` (Next.js)
- **Deploy:** `deploy/` — see [deploy/GITHUB.md](deploy/GITHUB.md) for GitHub-based deploy

```bash
# Local backend
cd mafexAll-main && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && cp .env.example .env
alembic upgrade head && uvicorn app.main:app --reload

# Local frontend
cd mafexFe-main && npm ci && npm run dev
```
