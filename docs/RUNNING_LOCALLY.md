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
3. Inspect the match score, matched requirements, gaps, and project evidence.
4. Edit the profile or opportunity and run the flow again.

The prototype uses deterministic, explainable matching and does not require a model API key.
