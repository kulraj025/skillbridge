# SkillBridge runnable prototype

The first student-flow prototype is now included in the repository.

## Run on Windows PowerShell

```powershell
cd "C:\Users\ADMIN\Documents\Default Project\skillbridge"
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m uvicorn app.main:app --app-dir backend --reload
```

Open `http://127.0.0.1:8000`.

Health check: `http://127.0.0.1:8000/api/health`.

## First demo

1. Click **Load sample data**.
2. Review the sample profile and opportunity.
3. Drag the 3D scene to rotate it, and hover a node to see which skill it is.
4. Inspect the match score, matched requirements, gaps, and project evidence.
5. Edit the profile or opportunity and run the flow again. The 3D scene updates
   to reflect the new result.

The prototype uses deterministic, explainable matching and does not require a model API key.

## Run the checks

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

This validates the documentation set, runs the Python unit tests, checks the
frontend syntax, and runs the 3D scene math tests.

To run only the frontend tests:

```powershell
node --test frontend/tests/scene.test.js
```

## Troubleshooting

**The badge in the top right says "API not reachable".**
The page is open but the backend is not running, or the tab is pointed at an old
port from a previous run. Stop any old server, then start it on the port you are
actually viewing:

```powershell
python -m uvicorn app.main:app --app-dir backend --reload
```

The page is served by the same server as the API, so both must use the same port.
The badge re-checks whenever you return to the tab.

**A save shows an HTTP error.**
The toast now includes the method, path, and status, for example
`POST /api/profiles failed (HTTP 422): ensure this value has at most 100 characters`.
That message names the exact problem instead of a generic failure.

**The page looks like it is running old code.**
Static files are served with `Cache-Control: no-cache`, so a normal reload
picks up changes. If a page still looks stale, use a hard refresh
(`Ctrl+Shift+R`) once.
