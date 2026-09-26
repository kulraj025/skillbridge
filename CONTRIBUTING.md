# Contributing to SkillBridge

SkillBridge is developed in small, verifiable steps. The GitHub history should show problem understanding, engineering decisions, evaluation, and iteration.

## Daily loop

```powershell
.\scripts\check.ps1
git status
git add .
git commit -m "Describe one meaningful change"
git push
```

## Commit style

Use focused messages such as:

- `Define student profile and evidence schema`
- `Add opportunity requirement extraction`
- `Add explainable match scoring`
- `Create labeled evaluation dataset`
- `Document interview findings`

Avoid mixing unrelated features in one commit.

## Definition of done

- Checks pass
- New behavior has a test or documented manual verification
- README and roadmap are updated when behavior changes
- No secrets, private data, or local databases are committed
- AI decisions remain explainable and human-reviewable
