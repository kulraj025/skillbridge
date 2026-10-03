# SkillBridge Deployment Guide

This project is a FastAPI application that serves both the API and the static
frontend from a single origin on a single port. It deploys to any platform that
can run a Docker image.

## Read this before you trust a hosted copy

Three things about a hosted deployment are not obvious and will otherwise cost
you an afternoon.

**1. The platform chooses the port, not you.** Render and Railway inject a
`PORT` variable and forward traffic to it. The `Dockerfile` reads that variable.
An image that hardcodes a port will start successfully and then serve nothing,
because nothing is listening where the platform expects.

**2. On free tiers your data disappears.** SQLite writes to a file inside the
container. The container's writable layer is an `overlay` filesystem and is
thrown away on every deploy and every restart. On Render's free plan there is no
disk to attach at all.

This is not hidden. `GET /api/health` reports it:

```json
{
  "status": "ok",
  "service": "skillbridge",
  "version": "0.1.0",
  "database": {
    "path": "skillbridge.db",
    "storage": "container-filesystem",
    "persistent": false,
    "warning": "Profiles, opportunities and matches are stored in a container filesystem and will be lost on the next deploy or restart. Attach a persistent volume, or set SKILLBRIDGE_DB to a mounted path."
  }
}
```

`"persistent": true` means the database sits on a real block filesystem rather
than an overlay or tmpfs. Check this after deploying, before sharing the link.

The reported `path` is the file name only. This endpoint is public, so it does
not hand out the host's directory layout or service account; the real path is
in `SKILLBRIDGE_DB` and in the startup logs.

**3. There is no authentication.** Every endpoint is open. Anyone with the URL
can create profiles, opportunities and matches, and can read everything stored.
That is acceptable for a demo you hand to a classmate and unacceptable the
moment you put real student data in it.

## Deploying

Every platform below needs your own account and your own login. Nothing here is
automated, and no URL is listed in advance because the hostname is assigned to
you at deploy time. Read it off the platform's dashboard when it finishes.

### Railway

1. Sign in at [railway.app](https://railway.app) with GitHub.
2. **New Project** → **Deploy from GitHub repo** → pick `kulraj025/skillbridge`.
   Railway reads `railway.toml` and the `Dockerfile`.
3. Add the service variable `SKILLBRIDGE_DB=/data/skillbridge.db`.
4. For data to survive, create a volume: **Volumes → New Volume → mount at
   `/data`**. The volume must be created in the dashboard; it cannot be declared
   in `railway.toml`.
5. Deploy, then confirm `"persistent": true` on `/api/health`.

### Render

1. Sign in at [render.com](https://render.com) with GitHub.
2. **New +** → **Blueprint**, select `kulraj025/skillbridge`. Render reads
   `render.yaml`.
3. Deploy. The `free` plan sleeps after inactivity and has no persistent disk,
   so expect cold starts and expect `"persistent": false`.
4. To keep data, use a paid plan and attach a disk mounted at
   `/app/backend/data`.

### Fly.io

```bash
flyctl launch --name skillbridge --dockerfile Dockerfile
flyctl volumes create skillbridge_data --size 1     # paid, but required
flyctl deploy
```

Then set `SKILLBRIDGE_DB=/data/skillbridge.db` and attach the volume.

### Google Cloud Run

Cloud Run's filesystem is writable but ephemeral, and its filesystem is not a
persistent volume. For data that survives, point Cloud SQL or a managed volume
at it instead.

```bash
gcloud run deploy skillbridge \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

Do not pass `--port 8000`. Cloud Run sets `PORT`, and the `Dockerfile` uses it.

### Local Docker

```bash
docker build -t skillbridge .
docker run -p 8000:8000 -v skillbridge-data:/app/backend/data skillbridge
```

The named volume is what makes `/api/health` report `"persistent": true` here,
matching how a hosted volume behaves.

## Environment variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `SKILLBRIDGE_DB` | SQLite file path | `backend/data/skillbridge.db` |
| `PORT` | Listen port; set by the platform | `8000` |

No secrets are required. The app holds no API keys, so there is nothing to
leak and nothing to rotate.

## Health check

`GET /api/health` is the endpoint every platform should probe.

| Key | Meaning |
|-----|---------|
| `status` | `ok` when the process is serving |
| `version` | Release string |
| `database.persistent` | `true` only on durable storage |
| `database.warning` | Set whenever `persistent` is `false` |

## Continuous integration

- `.github/workflows/ci.yml` runs the test suite on every push.
- `.github/workflows/deploy.yml` is an inactive template. It ships with
  `if: false` on every job on purpose, so nothing deploys until a human adds
  repository secrets and flips the flag.

If you enable it, treat the platform token like a password: scope it to this one
repository, and rotate it if it is ever pasted into a chat, a log, or a commit.

## Custom domains

Available after a deploy, from the platform dashboard: Railway
**Settings → Domains**, Render **Settings → Custom Domains**, Cloud Run
**Domain Mapping**. A custom domain still does not fix the two real limits —
ephemeral storage and the missing authentication.
