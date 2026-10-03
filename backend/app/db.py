"""SQLite storage for the SkillBridge student prototype."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "backend" / "data" / "skillbridge.db"
DB_PATH = Path(os.getenv("SKILLBRIDGE_DB", str(DEFAULT_DB_PATH)))


SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    major TEXT NOT NULL DEFAULT '',
    graduation_year INTEGER,
    skills_json TEXT NOT NULL DEFAULT '[]',
    projects_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS opportunities (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    organization TEXT NOT NULL,
    description TEXT NOT NULL,
    required_skills_json TEXT NOT NULL DEFAULT '[]',
    preferred_skills_json TEXT NOT NULL DEFAULT '[]',
    source_url TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS matches (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL,
    opportunity_id TEXT NOT NULL,
    score REAL NOT NULL,
    matched_required_json TEXT NOT NULL DEFAULT '[]',
    missing_required_json TEXT NOT NULL DEFAULT '[]',
    matched_preferred_json TEXT NOT NULL DEFAULT '[]',
    evidence_json TEXT NOT NULL DEFAULT '[]',
    explanation_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_matches_profile_id ON matches(profile_id);
CREATE INDEX IF NOT EXISTS idx_matches_opportunity_id ON matches(opportunity_id);
"""


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# Filesystems whose contents vanish with the container. The root of an image
# is an overlay; a tmpfs mount is memory. Neither is durable storage.
EPHEMERAL_FILESYSTEMS = frozenset(
    {
        "overlay",
        "overlayfs",
        "tmpfs",
        "ramfs",
        "devtmpfs",
        "squashfs",
        "aufs",
        "rootfs",
        "proc",
        "sysfs",
        "cgroup",
        "cgroup2",
        "devpts",
        "securityfs",
        "debugfs",
        "tracefs",
        "mqueue",
        "pstore",
        "configfs",
        "fusectl",
        "bpf",
        "binfmt_misc",
        "hugetlbfs",
        "mqueue",
        "nsfs",
    }
)


def _linux_mount_table():
    """Map of mount point -> filesystem type, or None off Linux."""
    try:
        with open("/proc/self/mountinfo", encoding="utf-8") as handle:
            raw = handle.read()
    except OSError:
        return None
    table = {}
    for line in raw.splitlines():
        fields = line.split(" ")
        if len(fields) < 7 or "-" not in fields:
            continue
        separator = fields.index("-")
        if separator + 1 >= len(fields):
            continue
        mount_point = fields[4]
        table[mount_point] = fields[separator + 1]
    return table or None


def _nearest_existing(path: Path) -> Path:
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return probe


def on_mounted_volume(path: Path = None) -> bool:
    """True when `path` sits on durable storage that survives a redeploy.

    Containers do not advertise durability by flag; they advertise it by
    filesystem type. An attached volume is a real block filesystem, while the
    image's writable layer is an overlay and a scratch mount is tmpfs. Both of
    those are reported as not persistent, which is the honest answer.
    """
    target = _nearest_existing(path or DB_PATH)

    table = _linux_mount_table()
    if table is not None:
        probe = str(target)
        while True:
            if probe in table:
                return table[probe].lower() not in EPHEMERAL_FILESYSTEMS
            parent = os.path.dirname(probe)
            if parent == probe:
                return False
            probe = parent

    # Off Linux, fall back to comparing device ids: a mount point has a
    # different device from its own parent directory.
    parent = target.parent
    if parent == target:
        return False
    try:
        return target.stat().st_dev != parent.stat().st_dev
    except OSError:
        return False


def storage_report(path: Path = None) -> Dict[str, Any]:
    """Describe where the database lives, without overselling durability."""
    persistent = on_mounted_volume(path)
    return {
        "path": str(path or DB_PATH),
        "storage": "volume" if persistent else "container-filesystem",
        "persistent": persistent,
        "warning": None
        if persistent
        else "Profiles, opportunities and matches are stored in a container "
        "filesystem and will be lost on the next deploy or restart. Attach a "
        "persistent volume, or set SKILLBRIDGE_DB to a mounted path.",
    }


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(SCHEMA)
