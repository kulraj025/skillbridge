"""Tests for the contribution-streak tracker.

The point of these tests is that the tracker cannot be flattered. Every case
below builds a real throwaway git repository with real commits on chosen
dates, so a passing suite means the numbers come from history rather than
from arithmetic that happens to look right.
"""

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from datetime import date, timedelta

SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "scripts",
    "streak.py",
)

_spec = importlib.util.spec_from_file_location("skillbridge_streak", SCRIPT)
streak = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(streak)


def make_repo(commit_days):
    """Create a temp repo with one commit per ISO date in `commit_days`."""
    path = tempfile.mkdtemp(prefix="streak-repo-")
    env = dict(os.environ)
    env.update(
        {
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
        }
    )
    subprocess.run(["git", "init", "-q"], cwd=path, env=env, check=True)
    for day in commit_days:
        stamp = "{}T12:00:00".format(day)
        env["GIT_AUTHOR_DATE"] = stamp
        env["GIT_COMMITTER_DATE"] = stamp
        with open(os.path.join(path, "f.txt"), "w", encoding="utf-8") as handle:
            handle.write(day)
        subprocess.run(
            ["git", "add", "-A"], cwd=path, env=env, check=True, stdout=subprocess.PIPE
        )
        subprocess.run(
            ["git", "commit", "-q", "--allow-empty", "-m", "work on {}".format(day)],
            cwd=path,
            env=env,
            check=True,
            stdout=subprocess.PIPE,
        )
    return path


def read_days(repo):
    return sorted(streak.read_commits(repo)[1])


class LongestRunTests(unittest.TestCase):
    def test_empty_history_has_no_run(self):
        self.assertEqual(streak.longest_run([]), (0, None, None))

    def test_single_day(self):
        best, start, end = streak.longest_run(["2026-01-05"])
        self.assertEqual((best, start, end), (1, date(2026, 1, 5), date(2026, 1, 5)))

    def test_consecutive_days_count_every_one(self):
        best, start, end = streak.longest_run(["2026-01-01", "2026-01-02", "2026-01-03"])
        self.assertEqual((best, start, end), (3, date(2026, 1, 1), date(2026, 1, 3)))

    def test_gap_splits_runs_and_longest_wins(self):
        days = ["2026-01-01", "2026-01-02", "2026-01-09", "2026-01-10", "2026-01-11", "2026-01-12"]
        best, start, end = streak.longest_run(days)
        self.assertEqual((best, start, end), (4, date(2026, 1, 9), date(2026, 1, 12)))

    def test_longest_run_not_at_the_end(self):
        days = ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-20"]
        best, start, end = streak.longest_run(days)
        self.assertEqual((best, start, end), (4, date(2026, 1, 1), date(2026, 1, 4)))

    def test_input_order_does_not_matter(self):
        days = ["2026-01-03", "2026-01-01", "2026-01-02"]
        self.assertEqual(streak.longest_run(days)[0], 3)


class CurrentRunTests(unittest.TestCase):
    TODAY = date(2026, 5, 10)

    def test_no_history_is_zero(self):
        self.assertEqual(streak.current_run([], self.TODAY), 0)

    def test_commit_today_counts(self):
        self.assertEqual(streak.current_run(["2026-05-10"], self.TODAY), 1)

    def test_yesterday_grace_keeps_streak_alive(self):
        days = ["2026-05-08", "2026-05-09"]
        self.assertEqual(streak.current_run(days, self.TODAY), 2)

    def test_two_day_gap_breaks_streak(self):
        days = ["2026-05-07", "2026-05-08"]
        self.assertEqual(streak.current_run(days, self.TODAY), 0)

    def test_streak_counts_back_from_today_not_from_first(self):
        days = ["2026-05-01", "2026-05-08", "2026-05-09", "2026-05-10"]
        self.assertEqual(streak.current_run(days, self.TODAY), 3)


class ReadCommitsTests(unittest.TestCase):
    def test_commits_are_grouped_by_real_date(self):
        repo = make_repo(["2026-03-01", "2026-03-01", "2026-03-05"])
        total, by_day = streak.read_commits(repo)
        self.assertEqual(total, 3)
        self.assertEqual(sorted(by_day), ["2026-03-01", "2026-03-05"])
        self.assertEqual(len(by_day["2026-03-01"]), 2)

    def test_subjects_are_captured_for_audit(self):
        repo = make_repo(["2026-03-02"])
        by_day = streak.read_commits(repo)[1]
        self.assertIn("work on 2026-03-02", by_day["2026-03-02"][0])

    def test_outside_a_repository_it_fails_loudly(self):
        empty = tempfile.mkdtemp(prefix="not-a-repo-")
        with self.assertRaises(SystemExit):
            streak.read_commits(empty)


class ReportTests(unittest.TestCase):
    TODAY = date(2026, 5, 10)

    def report(self, commit_days):
        repo = make_repo(commit_days)
        return streak.build_report(repo, 14, self.TODAY)

    def test_streak_is_derived_not_declared(self):
        text, stats = self.report(["2026-05-08", "2026-05-09", "2026-05-10"])
        self.assertEqual(stats["streak"], 3)
        self.assertEqual(stats["total_commits"], 3)
        self.assertEqual(stats["active_days"], 3)

    def test_silent_days_are_reported_as_a_gap(self):
        text, stats = self.report(["2026-04-01"])
        self.assertEqual(stats["streak"], 0)
        self.assertEqual(stats["days_since_last"], 39)
        self.assertIn("Gap of 39 day(s)", text)

    def test_empty_history_makes_no_claims(self):
        repo = make_repo([])
        text, stats = streak.build_report(repo, 14, self.TODAY)
        self.assertEqual(stats["streak"], 0)
        self.assertEqual(stats["total_commits"], 0)
        self.assertIsNone(stats["last_commit"])
        self.assertIn("No active streak", text)

    def test_report_lists_every_commit_subject(self):
        text, _ = self.report(["2026-05-09", "2026-05-10"])
        self.assertIn("work on 2026-05-09", text)
        self.assertIn("work on 2026-05-10", text)

    def test_report_refuses_manual_editing(self):
        text, _ = self.report(["2026-05-10"])
        self.assertIn("Do not edit this file by hand", text)
        self.assertIn("no manual counter here on purpose", text)

    def test_one_day_is_never_called_a_habit(self):
        text, _ = self.report(["2026-05-10"])
        self.assertIn("One commit is not a habit yet", text)

    def test_calendar_never_marks_future_days_as_active(self):
        active = {"2026-05-10"}
        _s, _e, labels, rows, grid = streak.calendar_strip(
            {d: ["x"] for d in active}, 14, self.TODAY
        )
        self.assertEqual(len(labels), 7)
        for row_index, row in enumerate(rows):
            self.assertEqual(len(row), 14)
            for column, cell in enumerate(row):
                day = grid[row_index][column]
                if day > self.TODAY:
                    self.assertEqual(cell, " ")
                elif day.isoformat() in active:
                    self.assertNotEqual(cell, ".")
                else:
                    self.assertEqual(cell, ".")

    def test_calendar_shows_the_active_day_it_was_given(self):
        _s, _e, _l, rows, grid = streak.calendar_strip(
            {"2026-05-10": ["x"]}, 14, self.TODAY
        )
        found = [
            (rows[r][c], grid[r][c])
            for r in range(7)
            for c in range(14)
            if grid[r][c] == date(2026, 5, 10)
        ]
        self.assertEqual(found, [("1", date(2026, 5, 10))])


class CliTests(unittest.TestCase):
    def run_cli(self, argv):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = streak.main(argv)
        return code, buffer.getvalue()

    def test_json_output_is_machine_readable(self):
        today = date.today()
        repo = make_repo([today.isoformat()])
        code, output = self.run_cli(["--repo", repo, "--json"])
        stats = json.loads(output)
        self.assertEqual(code, 0)
        self.assertEqual(stats["streak"], 1)
        self.assertEqual(stats["today"], today.isoformat())

    def test_write_flag_creates_the_report_file(self):
        today = date.today()
        repo = make_repo([today.isoformat()])
        target = os.path.join(repo, "STREAK.md")
        code, _ = self.run_cli(["--repo", repo, "--write", target])
        self.assertEqual(code, 0)
        with open(target, encoding="utf-8") as handle:
            written = handle.read()
        self.assertIn("Generated by `scripts/streak.py`", written)

    def test_print_mode_shows_the_status_table(self):
        today = date.today()
        repo = make_repo([today.isoformat()])
        code, output = self.run_cli(["--repo", repo])
        self.assertEqual(code, 0)
        self.assertIn("| Current streak | **1** |", output)

    def test_rejects_absurd_calendar_widths(self):
        with self.assertRaises(SystemExit):
            streak.main(["--repo", ".", "--weeks", "0"])
        with self.assertRaises(SystemExit):
            streak.main(["--repo", ".", "--weeks", "500"])


if __name__ == "__main__":
    unittest.main()
