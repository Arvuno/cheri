"""Tests for task filesystem scanning and path filtering."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cheri_cloud_cli.task.models import TaskDefinition, TaskRuntimeState
from cheri_cloud_cli.task.runtime import (
    _path_allowed,
    build_snapshot,
    scan_task,
)


SENSITIVE_FILES = [
    ".env",
    ".env.local",
    ".env.production",
    "app.env",
    "credentials.json",
    "api.key",
    "client.pem",
    "id_rsa",
    "id_rsa.pub",
    "id_ed25519",
    "id_ed25519.pub",
    ".npmrc",
    ".pypirc",
    ".netrc",
    "secrets.json",
    "secret.json",
]


def make_task(overrides: dict | None = None) -> TaskDefinition:
    base = {
        "id": "test_task_1",
        "workspace_id": "ws_1",
        "workspace_name": "test-workspace",
        "target_type": "directory",
        "target_path": "/tmp/cheri_test_target",
        "sync_mode": "on-change",
        "recursive": True,
        "include_patterns": [],
        "exclude_patterns": [],
        "debounce_seconds": 3,
        "direction": "upload-only",
    }
    if overrides:
        base.update(overrides)
    return TaskDefinition(**base)


def make_runtime(overrides: dict | None = None) -> TaskRuntimeState:
    base = {
        "task_id": "test_task_1",
        "snapshot": {},
        "last_detected_change_at": "",
        "next_interval_run_at": "",
        "active_run_id": "",
        "active_run_started_at": "",
        "watcher_pid": 0,
        "watcher_started_at": "",
        "watcher_heartbeat_at": "",
        "watcher_log_path": "",
        "updated_at": "",
    }
    if overrides:
        base.update(overrides)
    return TaskRuntimeState(**base)


class PathAllowedTests(unittest.TestCase):
    def test_allows_normal_files(self) -> None:
        task = make_task()
        self.assertTrue(_path_allowed("readme.md", task))
        self.assertTrue(_path_allowed("src/app.js", task))
        self.assertTrue(_path_allowed("docs/guide.pdf", task))

    def test_excludes_git_metadata_files(self) -> None:
        task = make_task()
        self.assertFalse(_path_allowed(".git/config", task))
        self.assertFalse(_path_allowed(".git/hooks/pre-commit", task))
        self.assertTrue(_path_allowed(".gitignore", task))

    def test_excludes_cheri_directory(self) -> None:
        task = make_task()
        self.assertFalse(_path_allowed(".cheri/tasks.json", task))
        self.assertFalse(_path_allowed(".cheri/config.json", task))

    def test_excludes_temporary_files(self) -> None:
        task = make_task()
        self.assertFalse(_path_allowed("notes.swp", task))
        self.assertFalse(_path_allowed("data.tmp", task))
        self.assertFalse(_path_allowed("download.part", task))

    def test_excludes_os_metadata(self) -> None:
        task = make_task()
        self.assertFalse(_path_allowed(".DS_Store", task))
        self.assertFalse(_path_allowed("Thumbs.db", task))

    def test_excludes_env_files(self) -> None:
        task = make_task()
        self.assertFalse(_path_allowed(".env", task))
        self.assertFalse(_path_allowed(".env.local", task))
        self.assertFalse(_path_allowed(".env.production", task))
        self.assertFalse(_path_allowed(".env/devel", task))
        self.assertFalse(_path_allowed("app.env", task))
        self.assertFalse(_path_allowed("frontend.env", task))

    def test_excludes_credentials_and_keys(self) -> None:
        task = make_task()
        self.assertFalse(_path_allowed("credentials.json", task))
        self.assertFalse(_path_allowed("api.key", task))
        self.assertFalse(_path_allowed("client.pem", task))
        self.assertFalse(_path_allowed("server.key", task))
        self.assertFalse(_path_allowed("cert.pem", task))

    def test_excludes_ssh_keys(self) -> None:
        task = make_task()
        self.assertFalse(_path_allowed("id_rsa", task))
        self.assertFalse(_path_allowed("id_rsa.pub", task))
        self.assertFalse(_path_allowed("id_ed25519", task))
        self.assertFalse(_path_allowed("id_ed25519.pub", task))

    def test_excludes_config_files(self) -> None:
        task = make_task()
        self.assertFalse(_path_allowed(".npmrc", task))
        self.assertFalse(_path_allowed(".pypirc", task))
        self.assertFalse(_path_allowed(".netrc", task))

    def test_excludes_secret_json(self) -> None:
        task = make_task()
        self.assertFalse(_path_allowed("secrets.json", task))
        self.assertFalse(_path_allowed("secret.json", task))
        self.assertTrue(_path_allowed("my_app_secrets.json", task))

    def test_include_patterns_take_priority(self) -> None:
        task = make_task({"include_patterns": ["*.md", "*.txt"]})
        self.assertTrue(_path_allowed("readme.md", task))
        self.assertTrue(_path_allowed("notes.txt", task))
        self.assertFalse(_path_allowed("data.json", task))

    def test_exclude_patterns_can_extend_defaults(self) -> None:
        task = make_task({"exclude_patterns": ["*.log", "*.bak"]})
        self.assertFalse(_path_allowed("debug.log", task))
        self.assertFalse(_path_allowed("backup.bak", task))

    def test_windows_path_separators_normalized(self) -> None:
        task = make_task()
        self.assertTrue(_path_allowed("src\\app.js", task))
        self.assertTrue(_path_allowed("docs\\readme.md", task))

    def test_task_exclude_patterns_override_defaults(self) -> None:
        task = make_task({"exclude_patterns": ["custom.txt"]})
        self.assertFalse(_path_allowed("custom.txt", task))


class BuildSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.target_dir = Path(self.temp_dir) / "scan_target"
        self.target_dir.mkdir()
        self.task = make_task({"target_path": str(self.target_dir)})

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_snapshot_includes_all_allowed_files(self) -> None:
        (self.target_dir / "readme.md").write_text("hello")
        (self.target_dir / "data.json").write_text('{"a":1}')
        (self.target_dir / "subdir").mkdir()
        (self.target_dir / "subdir" / "notes.txt").write_text("world")

        snapshot = build_snapshot(self.task)
        paths = set(snapshot.keys())
        self.assertIn("readme.md", paths)
        self.assertIn("data.json", paths)
        self.assertIn("subdir/notes.txt", paths)

    def test_snapshot_excludes_sensitive_files(self) -> None:
        (self.target_dir / "readme.md").write_text("safe")
        (self.target_dir / ".env").write_text("SECRET=xyz")
        (self.target_dir / "credentials.json").write_text('{"token":"abc"}')
        (self.target_dir / "api.key").write_text("PRIVATE_KEY")

        snapshot = build_snapshot(self.task)
        paths = set(snapshot.keys())
        self.assertIn("readme.md", paths)
        self.assertNotIn(".env", paths)
        self.assertNotIn("credentials.json", paths)
        self.assertNotIn("api.key", paths)

    def test_snapshot_records_mtime_and_size(self) -> None:
        test_file = self.target_dir / "notes.txt"
        test_file.write_text("content here")

        import time

        time.sleep(0.01)
        snapshot = build_snapshot(self.task)
        entry = snapshot["notes.txt"]
        self.assertIn("mtime_ns", entry)
        self.assertIn("size", entry)
        self.assertEqual(entry["size"], 12)

    def test_snapshot_empty_for_directory_with_only_excluded_files(self) -> None:
        (self.target_dir / ".env").write_text("SECRET=xyz")
        (self.target_dir / "credentials.json").write_text('{"token":"abc"}')

        snapshot = build_snapshot(self.task)
        self.assertEqual(len(snapshot), 0)


class ScanTaskTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.target_dir = Path(self.temp_dir) / "scan_target"
        self.target_dir.mkdir()
        self.task = make_task({"target_path": str(self.target_dir)})

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_scan_detects_new_file(self) -> None:
        runtime = make_runtime({"snapshot": {}})

        (self.target_dir / "newfile.txt").write_text("hello")

        result = scan_task(self.task, runtime)
        self.assertIn("newfile.txt", result.changed_paths)
        self.assertEqual(result.deleted_paths, [])

    def test_scan_detects_modified_file_mtime(self) -> None:
        test_file = self.target_dir / "notes.txt"
        test_file.write_text("version1")

        import time

        time.sleep(0.01)
        snapshot = build_snapshot(self.task)

        runtime = make_runtime({"snapshot": snapshot})
        test_file.write_text("version2")

        result = scan_task(self.task, runtime)
        self.assertIn("notes.txt", result.changed_paths)

    def test_scan_detects_modified_file_size(self) -> None:
        test_file = self.target_dir / "data.bin"
        test_file.write_text("x" * 100)

        snapshot = build_snapshot(self.task)
        runtime = make_runtime({"snapshot": snapshot})

        test_file.write_text("y" * 150)

        result = scan_task(self.task, runtime)
        self.assertIn("data.bin", result.changed_paths)

    def test_scan_detects_deleted_file(self) -> None:
        test_file = self.target_dir / "todelete.txt"
        test_file.write_text("delete me")

        snapshot = build_snapshot(self.task)
        runtime = make_runtime({"snapshot": snapshot})

        test_file.unlink()

        result = scan_task(self.task, runtime)
        self.assertIn("todelete.txt", result.deleted_paths)

    def test_scan_detects_no_changes(self) -> None:
        test_file = self.target_dir / "stable.txt"
        test_file.write_text("stable content")

        snapshot = build_snapshot(self.task)
        runtime = make_runtime({"snapshot": snapshot})

        result = scan_task(self.task, runtime)
        self.assertEqual(result.changed_paths, [])
        self.assertEqual(result.deleted_paths, [])

    def test_scan_force_returns_all_files(self) -> None:
        (self.target_dir / "a.txt").write_text("a")
        (self.target_dir / "b.txt").write_text("b")

        runtime = make_runtime({"snapshot": {}})

        result = scan_task(self.task, runtime, force=True)
        self.assertEqual(sorted(result.changed_paths), ["a.txt", "b.txt"])

    def test_scan_excludes_sensitive_files_from_results(self) -> None:
        (self.target_dir / "safe.txt").write_text("safe")
        (self.target_dir / ".env").write_text("SECRET=xyz")

        runtime = make_runtime({"snapshot": {}})

        result = scan_task(self.task, runtime)
        self.assertIn("safe.txt", result.changed_paths)
        self.assertNotIn(".env", result.changed_paths)
        self.assertNotIn(".env", result.current_snapshot)

    def test_scan_includes_files_matching_include_patterns(self) -> None:
        task = make_task(
            {
                "target_path": str(self.target_dir),
                "include_patterns": ["*.md", "*.txt"],
            }
        )
        (self.target_dir / "readme.md").write_text("readme")
        (self.target_dir / "notes.txt").write_text("notes")
        (self.target_dir / "data.json").write_text('{"a":1}')

        runtime = make_runtime({"snapshot": {}})

        result = scan_task(task, runtime)
        paths = set(result.changed_paths)
        self.assertIn("readme.md", paths)
        self.assertIn("notes.txt", paths)
        self.assertNotIn("data.json", paths)

    def test_scan_excludes_files_matching_task_exclude_patterns(self) -> None:
        task = make_task(
            {
                "target_path": str(self.target_dir),
                "exclude_patterns": ["*.log"],
            }
        )
        (self.target_dir / "readme.md").write_text("readme")
        (self.target_dir / "debug.log").write_text("log data")

        runtime = make_runtime({"snapshot": {}})

        result = scan_task(task, runtime)
        paths = set(result.changed_paths)
        self.assertIn("readme.md", paths)
        self.assertNotIn("debug.log", paths)

    def test_scan_default_secret_exclusions_applied(self) -> None:
        for filename in SENSITIVE_FILES:
            (self.target_dir / filename).write_text("sensitive content")

        runtime = make_runtime({"snapshot": {}})

        result = scan_task(self.task, runtime)
        for filename in SENSITIVE_FILES:
            self.assertNotIn(filename, result.changed_paths, f"{filename} should be excluded")


if __name__ == "__main__":
    unittest.main()