"""Tests for deployment-readiness behaviour.

These cover the two things that make a hosted deploy quietly wrong: binding a
port the platform never forwards to, and storing data somewhere that vanishes
on redeploy. Neither fails loudly at boot, so both are asserted here.
"""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO = os.path.dirname(BACKEND)


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, relative))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


db = load("sb_db", os.path.join("backend", "app", "db.py"))


class DockerPortTests(unittest.TestCase):
    """Render and Railway route to $PORT, never to a hardcoded 8000."""

    def setUp(self):
        with open(os.path.join(REPO, "Dockerfile"), encoding="utf-8") as handle:
            self.text = handle.read()

    def test_command_line_honours_the_port_variable(self):
        self.assertIn("--port ${PORT:-8000}", self.text)

    def test_healthcheck_probes_the_same_port(self):
        self.assertIn("${PORT:-8000}/api/health", self.text)

    def test_the_app_is_not_pinned_to_a_single_port(self):
        # The exec-form CMD cannot expand a variable, which is exactly why it
        # must not come back. Guard against that regression.
        self.assertNotIn('CMD ["uvicorn"', self.text)

    def test_port_has_a_local_default(self):
        self.assertIn("ENV PORT=8000", self.text)

    def test_uvicorn_runs_as_pid_one(self):
        # exec replaces the shell so SIGTERM reaches uvicorn directly.
        self.assertIn("CMD exec uvicorn", self.text)

    def test_binds_all_interfaces(self):
        self.assertIn("--host 0.0.0.0", self.text)

    def test_app_path_is_the_real_entrypoint(self):
        self.assertIn("app.main:app", self.text)
        self.assertIn("--app-dir backend", self.text)


class DeployConfigTests(unittest.TestCase):
    def read(self, name):
        with open(os.path.join(REPO, name), encoding="utf-8") as handle:
            return handle.read()

    def test_render_points_at_the_real_health_endpoint(self):
        self.assertIn("healthCheckPath: /api/health", self.read("render.yaml"))

    def test_render_uses_the_dockerfile_we_actually_test(self):
        self.assertIn("dockerfilePath: Dockerfile", self.read("render.yaml"))

    def test_railway_points_at_the_real_health_endpoint(self):
        self.assertIn('healthcheckPath = "/api/health"', self.read("railway.toml"))

    def test_railway_has_no_meaningless_services_table(self):
        # A [[services]] block with only a name is not part of Railway's schema.
        # It parses, so nothing complains, but it documents nothing.
        self.assertNotIn("[[services]]", self.read("railway.toml"))

    def test_both_configs_warn_about_ephemeral_storage(self):
        for name in ("render.yaml", "railway.toml"):
            self.assertIn("SKILLBRIDGE_DB", self.read(name))
            self.assertIn("persistent", self.read(name))


class StorageReportTests(unittest.TestCase):
    def test_report_names_the_database_file(self):
        report = db.storage_report()
        self.assertEqual(report["path"], db.DB_PATH.name)

    def test_report_never_leaks_the_host_directory_layout(self):
        # The endpoint is public. A full path would reveal the OS, the service
        # account and the host layout.
        report = db.storage_report()
        self.assertNotIn("/", report["path"])
        self.assertNotIn("\\", report["path"])
        self.assertLess(len(report["path"]), 60)

    def test_storage_is_one_of_two_known_states(self):
        self.assertIn(db.storage_report()["storage"], ("volume", "container-filesystem"))

    def test_container_storage_warns_and_volume_does_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = db.storage_report(Path(tmp) / "skillbridge.db")
            # A plain temp dir is not durable storage, so the honest answer is
            # container-filesystem with a warning attached.
            self.assertFalse(report["persistent"])
            self.assertIsNotNone(report["warning"])
            self.assertIn("lost on the next deploy", report["warning"])

    def test_warning_is_null_when_storage_is_durable(self):
        report = db.storage_report()
        self.assertEqual(report["warning"] is None, report["persistent"])

    def test_persistent_flag_matches_storage_label(self):
        for path in (Path(tempfile.gettempdir()), Path(__file__).resolve()):
            report = db.storage_report(path / "x.db")
            self.assertEqual(
                report["persistent"],
                report["storage"] == "volume",
            )

    def test_overlay_and_tmpfs_are_never_called_durable(self):
        for name in ("overlay", "tmpfs", "ramfs", "squashfs"):
            self.assertIn(name, db.EPHEMERAL_FILESYSTEMS)

    def test_real_block_filesystems_are_allowed_through(self):
        for name in ("ext4", "xfs", "btrfs", "zfs"):
            self.assertNotIn(name, db.EPHEMERAL_FILESYSTEMS)

    def test_mount_table_is_parsed_when_available(self):
        table = db._linux_mount_table()
        if table is None:
            self.skipTest("not Linux")
        self.assertIn("/", table)
        self.assertTrue(all(isinstance(v, str) for v in table.values()))

    def test_filesystem_root_is_not_reported_as_a_volume(self):
        # "/" resolves to the image's own overlay on Linux and to the drive root
        # elsewhere. Neither is an attached persistent volume.
        root = Path("/") if os.name != "nt" else Path(Path(__file__).anchor)
        self.assertFalse(db.on_mounted_volume(root))

    def test_missing_path_still_resolves_to_something_measurable(self):
        self.assertIsInstance(
            db.on_mounted_volume(Path(tempfile.gettempdir()) / "nope" / "deep" / "x.db"),
            bool,
        )

    def test_root_of_the_filesystem_resolves_without_hanging(self):
        # Guards the upward walk in on_mounted_volume.
        self.assertIsInstance(db.on_mounted_volume(Path("/" if os.name != "nt" else "C:\\")), bool)

    def test_env_var_still_controls_the_path(self):
        # db.py reads SKILLBRIDGE_DB at import time; re-import to prove it.
        script = (
            "import importlib.util, os, sys;"
            "spec = importlib.util.spec_from_file_location('d', {!r});"
            "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m);"
            "print(m.DB_PATH)"
        ).format(os.path.join(REPO, "backend", "app", "db.py"))
        env = dict(os.environ, SKILLBRIDGE_DB="/data/custom.db")
        import subprocess

        proc = subprocess.run(
            ["python", "-c", script],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        self.assertIn("custom.db", proc.stdout.decode("utf-8", "replace"))


class HealthEndpointTests(unittest.TestCase):
    def test_health_reports_storage_truthfully(self):
        import subprocess

        proc = subprocess.run(
            [
                "python",
                "-c",
                "import sys; sys.path.insert(0, {!r});"
                "from app.main import health; import json; print(json.dumps(health()))".format(
                    BACKEND
                ),
            ],
            env=dict(os.environ, SKILLBRIDGE_DB="/data/h.db"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        payload = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["service"], "skillbridge")
        # The frontend badge reads .version, so that key must survive.
        self.assertIn("version", payload)
        self.assertIn("database", payload)
        self.assertIn("persistent", payload["database"])


if __name__ == "__main__":
    unittest.main()
