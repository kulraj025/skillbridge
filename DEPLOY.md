# SkillBridge Deployment Guide

This project is a FastAPI application that serves both the API and the static frontend. It can be deployed to any platform that supports Docker or Python web applications.

## Quick Deploy Options

### 1. Railway (Recommended - Easiest)
1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click "New Project" → "Deploy from GitHub repo"
3. Select `kulraj025/skillbridge`
4. Railway will auto-detect the Dockerfile and deploy
5. Add environment variable: `SKILLBRIDGE_DB=/app/backend/data/skillbridge.db`
6. Your app will be live at `https://skillbridge-production.up.railway.app`

### 2. Render
1. Go to [render.com](https://render.com) and sign in with GitHub
2. Click "New +" → "Web Service"
3. Connect your GitHub repo `kulraj025/skillbridge`
4. Render will use the `render.yaml` config
5. Your app will be live at `https://skillbridge.onrender.com`

### 3. Google Cloud Run
```bash
# One-time setup
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

# Deploy
gcloud run deploy skillbridge \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000
```

### 4. Fly.io
```bash
flyctl launch --name skillbridge --dockerfile Dockerfile
flyctl deploy
```

### 5. DigitalOcean App Platform
1. Go to [cloud.digitalocean.com/apps](https://cloud.digitalocean.com/apps)
2. Create new app from GitHub repo
3. Select `kulraj025/skillbridge`
4. DigitalOcean will detect the Dockerfile
5. Deploy

## Local Development

```bash
# Backend
cd /path/to/skillbridge
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\Activate.ps1 on Windows
pip install -r backend/requirements.txt
python -m uvicorn app.main:app --app-dir backend --reload

# Open http://127.0.0.1:8000
```

## Docker

```bash
# Build
docker build -t skillbridge .

# Run
docker run -p 8000:8000 -v skillbridge-data:/app/backend/data skillbridge
```

## GitHub Actions CI/CD

The repository includes:
- `.github/workflows/ci.yml` - Runs tests on every push
- `.github/workflows/deploy.yml` - Template for deployment workflows

To enable auto-deploy:
1. Go to GitHub repo Settings → Secrets and variables → Actions
2. Add the required secrets for your chosen platform:
   - **Railway**: `RAILWAY_TOKEN`
   - **Render**: `RENDER_API_KEY`, `RENDER_SERVICE_ID`
   - **GCP**: `GCP_PROJECT_ID`, `GCP_SA_KEY`
3. Edit `.github/workflows/deploy.yml` and change `if: false` to `if: true` for your platform

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SKILLBRIDGE_DB` | SQLite database path | `/app/backend/data/skillbridge.db` |
| `PORT` | Port to listen on (some platforms) | `8000` |

## Health Check

All deployments should use `/api/health` for health checks. Returns:
```json
{"status": "ok", "service": "skillbridge", "version": "0.1.0"}
```

## Database Persistence

The app uses SQLite by default. For production:
- Use a persistent volume (Railway, Render, Fly.io provide this)
- Or migrate to PostgreSQL by updating `backend/app/db.py` and adding `DATABASE_URL` env var

## Custom Domain

After deploying, add a custom domain in your platform's dashboard:
- Railway: Settings → Domains
- Render: Settings → Custom Domains
- Cloud Run: Domain Mapping
