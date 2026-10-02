"""Derive SkillBridge's contribution streak from real git history.

Every number this script prints is computed from `git log HEAD`. There is no
manual entry, no counter someone can nudge upward by editing a file, and no
way to backdate a day. If the graph looks bad, the fix is to ship something,
not to edit this script.

The output is regenerated in full on each run, so the committed report is a
snapshot of real history rather than a running tally that drifts.

Usage:
    python scripts/streak.py                 # print the report
    python scripts/streak.py --json          # machine-readable summary
    python scripts/streak.py --write docs/STREAK.md
    python scripts/streak.py --weeks 26      # widen the calendar strip
"""

import argparse
import json
import subprocess
import sys
from datetime import date, timedelta

SEP = "\t"


def _run_git(repo, args):
    """Run a git command and return stdout, or raise a readable error."""
    try:
        proc = subprocess.run(
            ["git"] + args,
            cwd=repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        raise SystemExit("git is not installed or not on PATH.")
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", "replace").strip()
        raise SystemExit("git {} failed: {}".format(" ".join(args), detail))
    return proc.stdout.decode("utf-8", "replace")


def read_commits(repo):
    """Return (commit_count, {iso_date: [summaries]}) for the current branch."""
    # A directory that is not a repository at all is a user error, so say so.
    # A repository that simply has no commits yet is an honest empty streak.
    inside = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if inside.returncode != 0:
        raise SystemExit("{} is not a git repository.".format(repo))
    has_head = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if has_head.returncode != 0:
        return 0, {}
    raw = _run_git(
        repo,
        ["log", "HEAD", "--date=short", "--format=%ad{}%s".format(SEP)],
    )
    by_day = {}
    total = 0
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split(SEP, 1)
        if len(parts) != 2:
            continue
        day, subject = parts[0].strip(), parts[1].strip()
        by_day.setdefault(day, []).append(subject)
        total += 1
    return total, by_day


def longest_run(days):
    """Longest run of consecutive ISO dates present in `days`."""
    parsed = sorted(date.fromisoformat(d) for d in days)
    if not parsed:
        return 0, None, None
    best = 0
    best_start = None
    best_end = None
    run_start = parsed[0]
    run_end = parsed[0]
    # The trailing None closes the final run without a special case after the loop.
    for current in parsed[1:] + [None]:
        if current is not None and current - run_end == timedelta(days=1):
            run_end = current
            continue
        length = (run_end - run_start).days + 1
        if length > best:
            best = length
            best_start = run_start
            best_end = run_end
        if current is not None:
            run_start = current
            run_end = current
    return best, best_start, best_end


def current_run(days, today):
    """Consecutive active days ending today or yesterday.

    Yesterday is accepted on purpose: a day is not over until it is over, so
    an unbroken run should not be reported as broken at 09:00.
    """
    if not days:
        return 0
    parsed = {date.fromisoformat(d) for d in days}
    cursor = today
    if cursor not in parsed:
        cursor = today - timedelta(days=1)
        if cursor not in parsed:
            return 0
    count = 0
    while cursor in parsed:
        count += 1
        cursor -= timedelta(days=1)
    return count


def calendar_strip(by_day, weeks, today):
    """ASCII contribution strip, weeks as columns, Monday-first rows.

    Returns (start, end, labels, rows, grid) where `grid` holds the real date
    behind each cell, so a caller can check a claim instead of trusting glyphs.
    """
    days = {date.fromisoformat(d): len(v) for d, v in by_day.items()}
    end = today + timedelta(days=(6 - today.weekday()))
    start = end - timedelta(days=weeks * 7 - 1)
    rows = []
    grid = []
    for weekday in range(7):
        cells = []
        dates = []
        for week in range(weeks):
            day = start + timedelta(days=week * 7 + weekday)
            dates.append(day)
            if day > today:
                cells.append(" ")
                continue
            count = days.get(day, 0)
            cells.append("." if count == 0 else str(min(count, 4)))
        rows.append("".join(cells))
        grid.append(dates)
    labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return start, end, labels, rows, grid


def build_report(repo, weeks, today):
    total_commits, by_day = read_commits(repo)
    best, best_start, best_end = longest_run(by_day)
    streak = current_run(by_day, today)
    days = sorted(by_day)
    last_active = days[-1] if days else None
    idle = (today - date.fromisoformat(last_active)).days if last_active else None

    start, end, labels, rows, _grid = calendar_strip(by_day, weeks, today)

    if streak == 0:
        headline = "No active streak. No commits landed today or yesterday."
    elif streak == 1:
        headline = "1 day. One commit is not a habit yet."
    else:
        headline = "{} days and counting.".format(streak)

    lines = []
    lines.append("# Contribution streak")
    lines.append("")
    lines.append("> Generated by `scripts/streak.py` from `git log HEAD`.")
    lines.append("> Do not edit this file by hand; the next run overwrites it.")
    lines.append("> There is no manual counter here on purpose.")
    lines.append("")
    lines.append("## Status")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    lines.append("| Current streak | **{}** |".format(streak))
    lines.append("| Longest streak | {} |".format(best))
    if best_start is not None:
        lines.append(
            "| Longest run | {} to {} |".format(best_start.isoformat(), best_end.isoformat())
        )
    lines.append("| Total commits | {} |".format(total_commits))
    lines.append("| Active days | {} |".format(len(by_day)))
    if days:
        lines.append("| First commit | {} |".format(days[0]))
        lines.append("| Last commit | {} |".format(last_active))
        lines.append("| Days since last commit | {} |".format(idle))
    lines.append("")
    lines.append("## {}".format(today.isoformat()))
    lines.append("")
    lines.append("{}".format(headline))
    lines.append("")
    if idle is not None and idle >= 1:
        lines.append(
            "Gap of {} day(s) before today. The streak is broken; it restarts "
            "on the next real commit.".format(idle)
        )
        lines.append("")

    lines.append("## Last {} weeks".format(weeks))
    lines.append("")
    lines.append("`.` = no commit, `1`-`4` = commits that day.")
    lines.append("")
    header = "      " + " ".join(
        "%02d" % (((start + timedelta(days=w * 7)).isocalendar()[1]) % 100)
        for w in range(weeks)
    )
    lines.append(header)
    for label, row in zip(labels, rows):
        lines.append("{}  |{}|".format(label, " ".join(row)))
    lines.append("")
    lines.append("Range: {} to {}.".format(start.isoformat(), end.isoformat()))
    lines.append("")

    lines.append("## Commit log")
    lines.append("")
    lines.append("| Date | Commits | Subjects |")
    lines.append("| --- | --- | --- |")
    for day in reversed(days):
        subjects = by_day[day]
        joined = "<br>".join(s.replace("|", "\\|") for s in subjects)
        lines.append("| {} | {} | {} |".format(day, len(subjects), joined))
    lines.append("")
    return "\n".join(lines) + "\n", {
        "streak": streak,
        "longest": best,
        "total_commits": total_commits,
        "active_days": len(by_day),
        "first_commit": days[0] if days else None,
        "last_commit": last_active,
        "days_since_last": idle,
        "today": today.isoformat(),
    }


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="path to the git repository")
    parser.add_argument("--weeks", type=int, default=14, help="calendar width in weeks")
    parser.add_argument("--write", metavar="PATH", help="write the report to PATH")
    parser.add_argument("--json", action="store_true", help="print JSON instead")
    args = parser.parse_args(argv)

    if args.weeks < 1 or args.weeks > 104:
        raise SystemExit("--weeks must be between 1 and 104")

    report, stats = build_report(args.repo, args.weeks, date.today())

    if args.json:
        print(json.dumps(stats, indent=2))
        return 0
    if args.write:
        with open(args.write, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(report)
        print("Wrote {}".format(args.write))
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
