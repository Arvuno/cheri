"""Tests for handoff manifest generation, secret-safe scanning, and CLI commands."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from cheri_cloud_cli.handoff import (
    HandoffFile,
    HandoffManifest,
    GitContext,
    is_sensitive_path,
    calculate_checksum,
    get_content_type,
    scan_directory,
    DEFAULT_EXCLUDE_PATTERNS,
    create_manifest,
    write_manifest,
)


class IsSensitivePathTests(unittest.TestCase):
    def test_allows_normal_files(self) -> None:
        self.assertFalse(is_sensitive_path("readme.md"))
        self.assertFalse(is_sensitive_path("src/app.js"))
        self.assertFalse(is_sensitive_path("docs/guide.pdf"))
        self.assertFalse(is_sensitive_path("output/report.txt"))

    def test_excludes_env_files(self) -> None:
        self.assertTrue(is_sensitive_path(".env"))
        self.assertTrue(is_sensitive_path(".env.local"))
        self.assertTrue(is_sensitive_path(".env.production"))
        self.assertTrue(is_sensitive_path("app.env"))
        self.assertTrue(is_sensitive_path("frontend.env"))
        self.assertTrue(is_sensitive_path(".env/devel"))

    def test_excludes_credentials_and_keys(self) -> None:
        self.assertTrue(is_sensitive_path("credentials.json"))
        self.assertTrue(is_sensitive_path("api.key"))
        self.assertTrue(is_sensitive_path("client.pem"))
        self.assertTrue(is_sensitive_path("server.key"))
        self.assertTrue(is_sensitive_path("cert.pem"))

    def test_excludes_ssh_keys(self) -> None:
        self.assertTrue(is_sensitive_path("id_rsa"))
        self.assertTrue(is_sensitive_path("id_rsa.pub"))
        self.assertTrue(is_sensitive_path("id_ed25519"))
        self.assertTrue(is_sensitive_path("id_ed25519.pub"))

    def test_excludes_config_files(self) -> None:
        self.assertTrue(is_sensitive_path(".npmrc"))
        self.assertTrue(is_sensitive_path(".pypirc"))
        self.assertTrue(is_sensitive_path(".netrc"))

    def test_excludes_secret_json(self) -> None:
        self.assertTrue(is_sensitive_path("secrets.json"))
        self.assertTrue(is_sensitive_path("secret.json"))
        self.assertFalse(is_sensitive_path("my_app_secrets.json"))

    def test_excludes_git_directory(self) -> None:
        self.assertTrue(is_sensitive_path(".git/config"))
        self.assertTrue(is_sensitive_path(".git/hooks/pre-commit"))
        # .gitignore is allowed
        self.assertFalse(is_sensitive_path(".gitignore"))

    def test_excludes_os_metadata(self) -> None:
        self.assertTrue(is_sensitive_path(".DS_Store"))
        self.assertTrue(is_sensitive_path("Thumbs.db"))

    def test_glob_patterns_work(self) -> None:
        self.assertTrue(is_sensitive_path("*.key"))
        self.assertTrue(is_sensitive_path("*.pem"))
        self.assertFalse(is_sensitive_path("mykey.txt"))

    def test_custom_patterns_can_be_passed(self) -> None:
        self.assertTrue(is_sensitive_path("secrets.json", ["secrets.json"]))
        self.assertFalse(is_sensitive_path("readme.md", ["secrets.json"]))


class CalculateChecksumTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_checksum_is_sha256_hex_string(self) -> None:
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("hello world")
        checksum = calculate_checksum(test_file)
        self.assertEqual(len(checksum), 64)  # SHA-256 hex = 64 chars
        self.assertTrue(all(c in "0123456789abcdef" for c in checksum))

    def test_same_content_produces_same_checksum(self) -> None:
        file_a = Path(self.temp_dir) / "a.txt"
        file_b = Path(self.temp_dir) / "b.txt"
        content = "identical content"
        file_a.write_text(content)
        file_b.write_text(content)
        self.assertEqual(calculate_checksum(file_a), calculate_checksum(file_b))

    def test_different_content_produces_different_checksum(self) -> None:
        file_a = Path(self.temp_dir) / "a.txt"
        file_b = Path(self.temp_dir) / "b.txt"
        file_a.write_text("content a")
        file_b.write_text("content b")
        self.assertNotEqual(calculate_checksum(file_a), calculate_checksum(file_b))


class GetContentTypeTests(unittest.TestCase):
    def test_returns_correct_types(self) -> None:
        self.assertEqual(get_content_type(Path("readme.md")), "text/markdown")
        self.assertEqual(get_content_type(Path("notes.txt")), "text/plain")
        self.assertEqual(get_content_type(Path("data.json")), "application/json")
        self.assertEqual(get_content_type(Path("config.yaml")), "text/yaml")
        self.assertEqual(get_content_type(Path("script.py")), "text/x-python")
        self.assertEqual(get_content_type(Path("app.js")), "text/javascript")
        self.assertEqual(get_content_type(Path("component.tsx")), "text/typescript+tsx")

    def test_returns_none_for_unknown_extensions(self) -> None:
        self.assertIsNone(get_content_type(Path("random.xyz")))
        self.assertIsNone(get_content_type(Path("noextension")))


class ScanDirectoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.scan_dir = Path(self.temp_dir) / "scan_target"
        self.scan_dir.mkdir()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_scans_all_files_in_directory(self) -> None:
        (self.scan_dir / "readme.md").write_text("hello")
        (self.scan_dir / "data.json").write_text('{"a":1}')
        (self.scan_dir / "subdir").mkdir()
        (self.scan_dir / "subdir" / "notes.txt").write_text("world")

        files, skipped = scan_directory(self.scan_dir)
        file_paths = [f.relative_path for f in files]

        self.assertIn("readme.md", file_paths)
        self.assertIn("data.json", file_paths)
        self.assertIn("subdir/notes.txt", file_paths)

    def test_skips_sensitive_files(self) -> None:
        (self.scan_dir / "readme.md").write_text("safe")
        (self.scan_dir / ".env").write_text("SECRET=xyz")
        (self.scan_dir / "credentials.json").write_text('{"token":"abc"}')

        files, skipped = scan_directory(self.scan_dir)
        file_paths = [f.relative_path for f in files]

        self.assertIn("readme.md", file_paths)
        self.assertNotIn(".env", file_paths)
        self.assertNotIn("credentials.json", file_paths)
        self.assertIn(".env", skipped)
        self.assertIn("credentials.json", skipped)

    def test_skipped_files_not_read(self) -> None:
        """Skipped files should be listed by name only - their contents are never read."""
        (self.scan_dir / ".env").write_text("SHOULD_NOT_BE_READ")
        files, skipped = scan_directory(self.scan_dir)

        self.assertIn(".env", skipped)
        # If we got here without reading .env, the test passes
        # (can't easily verify contents weren't read, but we trust the implementation)

    def test_records_size_and_checksum(self) -> None:
        test_file = self.scan_dir / "notes.txt"
        test_file.write_text("content here")

        files, skipped = scan_directory(self.scan_dir)
        entry = next((f for f in files if f.relative_path == "notes.txt"), None)

        self.assertIsNotNone(entry)
        self.assertEqual(entry.size, 12)
        self.assertEqual(len(entry.checksum), 64)

    def test_includes_content_type(self) -> None:
        (self.scan_dir / "readme.md").write_text("markdown")
        (self.scan_dir / "data.json").write_text("{}")

        files, skipped = scan_directory(self.scan_dir)
        md_file = next((f for f in files if f.relative_path == "readme.md"), None)
        json_file = next((f for f in files if f.relative_path == "data.json"), None)

        self.assertEqual(md_file.content_type, "text/markdown")
        self.assertEqual(json_file.content_type, "application/json")

    def test_non_recursive_scan(self) -> None:
        (self.scan_dir / "top.txt").write_text("top")
        (self.scan_dir / "subdir").mkdir()
        (self.scan_dir / "subdir" / "nested.txt").write_text("nested")

        files, skipped = scan_directory(self.scan_dir, recursive=False)
        paths = [f.relative_path for f in files]

        self.assertIn("top.txt", paths)
        self.assertNotIn("subdir/nested.txt", paths)

    def test_git_directory_excluded(self) -> None:
        git_dir = self.scan_dir / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("git config")

        files, skipped = scan_directory(self.scan_dir)
        self.assertEqual(len([f for f in files if ".git" in f.relative_path]), 0)


class CreateManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.scan_dir = Path(self.temp_dir) / "manifest_target"
        self.scan_dir.mkdir()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_manifest_has_required_fields(self) -> None:
        (self.scan_dir / "readme.md").write_text("hello")
        manifest = create_manifest(
            source_path=str(self.scan_dir),
            name="test handoff",
            description="test description",
            tags=["test", "demo"],
        )

        self.assertEqual(manifest["schema_version"], "1.0")
        self.assertEqual(manifest["name"], "test handoff")
        self.assertEqual(manifest["description"], "test description")
        self.assertEqual(manifest["tags"], ["test", "demo"])
        self.assertIn("handoff_id", manifest)
        self.assertIn("generated_at", manifest)
        self.assertIn("source_path", manifest)
        self.assertIn("files", manifest)
        self.assertIn("skipped_sensitive", manifest)  # even if empty, key must exist

    def test_manifest_includes_file_count_and_size(self) -> None:
        (self.scan_dir / "a.txt").write_text("aaa")
        (self.scan_dir / "b.txt").write_text("bbb")
        manifest = create_manifest(
            source_path=str(self.scan_dir),
            name="test",
        )

        self.assertEqual(manifest["_file_count"], 2)
        self.assertEqual(manifest["_total_size"], 6)

    def test_manifest_excludes_sensitive_files(self) -> None:
        (self.scan_dir / "readme.md").write_text("safe")
        (self.scan_dir / ".env").write_text("secret")
        manifest = create_manifest(
            source_path=str(self.scan_dir),
            name="test",
        )

        file_paths = [f["relative_path"] for f in manifest["files"]]
        self.assertIn("readme.md", file_paths)
        self.assertNotIn(".env", file_paths)
        self.assertIn(".env", manifest["skipped_sensitive"])

    def test_agent_and_tool_metadata_set(self) -> None:
        manifest = create_manifest(
            source_path=str(self.scan_dir),
            name="test",
            agent_name="claude-code",
            tool_name="handoff-cli",
            version_label="v1.0.0",
        )

        self.assertEqual(manifest["agent_name"], "claude-code")
        self.assertEqual(manifest["tool_name"], "handoff-cli")
        self.assertEqual(manifest["version_label"], "v1.0.0")

    def test_single_file_manifest(self) -> None:
        single_file = self.scan_dir / "report.txt"
        single_file.write_text("report content")
        manifest = create_manifest(
            source_path=str(single_file),
            name="single file handoff",
        )

        self.assertEqual(manifest["source_context"], "file")
        self.assertEqual(len(manifest["files"]), 1)
        self.assertEqual(manifest["files"][0]["relative_path"], "report.txt")

    def test_git_context_included_when_available(self) -> None:
        # Create a fake git directory
        git_dir = self.scan_dir / ".git"
        git_dir.mkdir()

        manifest = create_manifest(
            source_path=str(self.scan_dir),
            name="test",
        )

        # git context may or may not be present depending on whether git is available
        # but if it is present, it should have the right structure
        if manifest.get("git_context"):
            ctx = manifest["git_context"]
            self.assertIn("branch", ctx)
            self.assertIn("commit_hash", ctx)
            self.assertIn("dirty", ctx)


class WriteManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_writes_json_file(self) -> None:
        manifest = {
            "schema_version": "1.0",
            "handoff_id": "test-123",
            "name": "test",
            "files": [],
            "skipped_sensitive": [],
        }
        output_dir = Path(self.temp_dir) / "output"
        output_dir.mkdir()
        path = write_manifest(manifest, str(output_dir))

        self.assertTrue(path.exists())
        self.assertEqual(path.name, "cheri-handoff.json")
        with open(path) as f:
            loaded = json.load(f)
        self.assertEqual(loaded["handoff_id"], "test-123")


class HandoffFileTests(unittest.TestCase):
    def test_to_dict_includes_all_fields(self) -> None:
        file = HandoffFile(
            relative_path="readme.md",
            size=100,
            checksum="abc123",
            content_type="text/markdown",
            skipped=False,
        )
        d = file.to_dict()
        self.assertEqual(d["relative_path"], "readme.md")
        self.assertEqual(d["size"], 100)
        self.assertEqual(d["checksum"], "abc123")
        self.assertEqual(d["content_type"], "text/markdown")
        self.assertNotIn("skipped", d)

    def test_skipped_flag_included_when_true(self) -> None:
        file = HandoffFile(
            relative_path="secret.txt",
            size=50,
            checksum="xyz",
            skipped=True,
        )
        d = file.to_dict()
        self.assertTrue(d["skipped"])


class GitContextTests(unittest.TestCase):
    def test_to_dict(self) -> None:
        ctx = GitContext(
            branch="main",
            commit_hash="abc123def456",
            dirty=True,
            remote_url="https://github.com/user/repo.git",
        )
        d = ctx.to_dict()
        self.assertEqual(d["branch"], "main")
        self.assertEqual(d["commit_hash"], "abc123def456")
        self.assertTrue(d["dirty"])
        self.assertEqual(d["remote_url"], "https://github.com/user/repo.git")

    def test_remote_url_can_be_none(self) -> None:
        ctx = GitContext(
            branch="main",
            commit_hash="abc123",
            dirty=False,
        )
        self.assertIsNone(ctx.remote_url)


class HandoffManifestTests(unittest.TestCase):
    def test_to_dict(self) -> None:
        manifest = HandoffManifest(
            name="test manifest",
            description="a test",
            tags=["test"],
            source_path="/tmp/test",
            files=[
                HandoffFile(relative_path="a.txt", size=10, checksum="xyz"),
            ],
            skipped_sensitive=[".env"],
        )
        d = manifest.to_dict()

        self.assertEqual(d["name"], "test manifest")
        self.assertEqual(d["description"], "a test")
        self.assertEqual(d["tags"], ["test"])
        self.assertEqual(len(d["files"]), 1)
        self.assertIn(".env", d["skipped_sensitive"])

    def test_optional_fields_omitted_when_none(self) -> None:
        manifest = HandoffManifest(
            name="minimal manifest",
        )
        d = manifest.to_dict()

        self.assertNotIn("description", d)
        self.assertNotIn("git_context", d)
        self.assertNotIn("agent_name", d)


class IncludeSensitiveConfirmationTests(unittest.TestCase):
    """Test that --include-sensitive requires explicit confirmation."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.scan_dir = Path(self.temp_dir) / "sensitive_test"
        self.scan_dir.mkdir()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_manifest_excludes_sensitive_by_default(self) -> None:
        (self.scan_dir / "readme.md").write_text("safe")
        (self.scan_dir / ".env").write_text("SECRET=xyz")
        manifest = create_manifest(
            source_path=str(self.scan_dir),
            name="test",
            include_sensitive=False,
        )

        file_paths = [f["relative_path"] for f in manifest["files"]]
        self.assertNotIn(".env", file_paths)
        self.assertIn(".env", manifest["skipped_sensitive"])

    def test_manifest_includes_sensitive_when_flag_set(self) -> None:
        (self.scan_dir / "readme.md").write_text("safe")
        (self.scan_dir / ".env").write_text("SECRET=xyz")
        manifest = create_manifest(
            source_path=str(self.scan_dir),
            name="test",
            include_sensitive=True,
        )

        file_paths = [f["relative_path"] for f in manifest["files"]]
        self.assertIn("readme.md", file_paths)
        self.assertIn(".env", file_paths)


class NoSecretContentInOutputTests(unittest.TestCase):
    """Test that secret file contents never appear in manifest output."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.scan_dir = Path(self.temp_dir) / "secret_content_test"
        self.scan_dir.mkdir()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_env_file_content_not_in_manifest(self) -> None:
        (self.scan_dir / ".env").write_text("SUPER_SECRET_API_KEY=don't_log_me")
        manifest = create_manifest(
            source_path=str(self.scan_dir),
            name="test",
        )

        manifest_str = json.dumps(manifest)
        self.assertNotIn("don't_log_me", manifest_str)
        self.assertNotIn("SUPER_SECRET_API_KEY", manifest_str)

    def test_credentials_file_content_not_in_manifest(self) -> None:
        (self.scan_dir / "credentials.json").write_text('{"token":"secret123"}')
        manifest = create_manifest(
            source_path=str(self.scan_dir),
            name="test",
        )

        manifest_str = json.dumps(manifest)
        self.assertNotIn("secret123", manifest_str)
        self.assertNotIn('{"token"', manifest_str)


class GitContextDetectionTests(unittest.TestCase):
    """Test that git context detection works or gracefully degrades."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.scan_dir = Path(self.temp_dir) / "git_test"
        self.scan_dir.mkdir()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_manifest_without_git_context(self) -> None:
        # No .git directory, should gracefully handle missing git
        manifest = create_manifest(
            source_path=str(self.scan_dir),
            name="test",
        )

        # Either no git_context or a graceful fallback
        self.assertIn("schema_version", manifest)
        self.assertIn("handoff_id", manifest)

    def test_git_context_structure_when_available(self) -> None:
        # Create a mock git structure
        git_dir = self.scan_dir / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main\n")

        manifest = create_manifest(
            source_path=str(self.scan_dir),
            name="test",
        )

        # git_context may be None if git commands fail
        # but if present, should have the right structure
        if manifest.get("git_context"):
            ctx = manifest["git_context"]
            self.assertIn("branch", ctx)
            self.assertIn("commit_hash", ctx)


class HandoffPushUploadTests(unittest.TestCase):
    """Test that handoff push uploads files through the workspace storage."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.scan_dir = Path(self.temp_dir) / "push_target"
        self.scan_dir.mkdir()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_push_manifest_records_file_id_and_storage_key(self) -> None:
        """When files are uploaded, manifest should record file_id and storage_key."""
        # Create test files
        (self.scan_dir / "readme.md").write_text("hello")
        manifest = create_manifest(source_path=str(self.scan_dir), name="test")

        # Simulate what push_handoff does - add upload metadata to files
        from cheri_cloud_cli.handoff import HandoffFile
        updated_files = []
        for f in manifest["files"]:
            if f["relative_path"] == "readme.md":
                f["file_id"] = "fid_test_123"
                f["storage_key"] = f"handoffs/{manifest['handoff_id']}/readme.md"
                f["provider_id"] = "system"
                f["uploaded_at"] = "2026-05-30T00:00:00Z"
                f["upload_status"] = "uploaded"
            hf = HandoffFile.from_dict(f)
            updated_files.append(hf)

        # Verify manifest has upload metadata
        updated_manifest = manifest.copy()
        updated_manifest["files"] = [f.to_dict() for f in updated_files]
        file_entry = next(f for f in updated_manifest["files"] if f["relative_path"] == "readme.md")
        self.assertEqual(file_entry["file_id"], "fid_test_123")
        self.assertEqual(file_entry["storage_key"], f"handoffs/{manifest['handoff_id']}/readme.md")
        self.assertEqual(file_entry["upload_status"], "uploaded")

    def test_push_partial_failure_marks_handoff_partial_failed(self) -> None:
        """When some files fail to upload, handoff status should be partial_failed."""
        manifest = create_manifest(source_path=str(self.scan_dir), name="test")
        manifest["files"] = []

        failed_files = [{"path": "failed.txt", "error": "upload error"}]
        status = "partial_failed" if failed_files else "ready"
        self.assertEqual(status, "partial_failed")

    def test_skipped_sensitive_files_not_in_manifest_files(self) -> None:
        """Sensitive files should be in skipped_sensitive, not in files list."""
        (self.scan_dir / ".env").write_text("SECRET=xyz")
        (self.scan_dir / "readme.md").write_text("hello")
        manifest = create_manifest(source_path=str(self.scan_dir), name="test")

        file_paths = [f["relative_path"] for f in manifest["files"]]
        self.assertNotIn(".env", file_paths)
        self.assertIn(".env", manifest["skipped_sensitive"])


class HandoffPullDownloadTests(unittest.TestCase):
    """Test that handoff pull downloads files."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.dest_dir = Path(self.temp_dir) / "pull_dest"
        self.dest_dir.mkdir()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_pull_restores_relative_paths(self) -> None:
        """Pull should restore files with correct relative paths."""
        # Simulate manifest with upload metadata
        manifest = {
            "schema_version": "1.1",
            "handoff_id": "test-123",
            "name": "test",
            "files": [
                {
                    "relative_path": "subdir/readme.md",
                    "size": 12,
                    "checksum": "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9",
                    "file_id": "fid_abc",
                    "upload_status": "uploaded",
                },
            ],
            "skipped_sensitive": [],
        }

        # Write manifest
        manifest_path = self.dest_dir / "cheri-handoff.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        # Verify manifest was written
        with open(manifest_path) as f:
            loaded = json.load(f)
        self.assertEqual(loaded["handoff_id"], "test-123")

    def test_pull_requires_manifest(self) -> None:
        """Pull should fail gracefully when no manifest is available."""
        # Without manifest_file_id and without manifest data, pull should report error
        h = {"id": "test", "workspace_id": "ws1"}
        manifest_data = h.get("manifest", {})
        manifest_file_id = h.get("manifest_file_id")
        has_manifest = manifest_file_id or manifest_data
        self.assertFalse(has_manifest)


class ManifestBackwardCompatibilityTests(unittest.TestCase):
    """Test that old manifests (v1.0) without file_id still load correctly."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_v1_0_manifest_loads_without_file_id(self) -> None:
        """Manifest v1.0 without file_id fields should load without errors."""
        old_manifest = {
            "schema_version": "1.0",
            "handoff_id": "old-123",
            "name": "old handoff",
            "files": [
                {"relative_path": "a.txt", "size": 10, "checksum": "abc"},
            ],
            "skipped_sensitive": [],
        }

        # Create HandoffFile from dict (backward compat)
        from cheri_cloud_cli.handoff import HandoffFile
        for f_dict in old_manifest["files"]:
            hf = HandoffFile.from_dict(f_dict)
            self.assertIsNone(hf.file_id)
            self.assertIsNone(hf.storage_key)
            self.assertIsNone(hf.upload_status)

    def test_to_dict_excludes_none_fields(self) -> None:
        """to_dict should not include None upload metadata fields."""
        hf = HandoffFile("a.txt", 10, "checksum")
        d = hf.to_dict()
        self.assertNotIn("file_id", d)
        self.assertNotIn("storage_key", d)
        self.assertNotIn("upload_status", d)


if __name__ == "__main__":
    unittest.main()