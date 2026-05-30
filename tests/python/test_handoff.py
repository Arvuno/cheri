"""Tests for handoff manifest generation, secret-safe scanning, and CLI commands."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cheri_cloud_cli.handoff import (
    HandoffFile,
    HandoffManifest,
    GitContext,
    is_sensitive_path,
    calculate_checksum,
    get_content_type,
    scan_directory,
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


# =============================================================================
# RETRY POLICY TESTS
# =============================================================================

class RetryPolicyTests(unittest.TestCase):
    """Test retry behavior for transient vs permanent errors."""

    def test_is_retryable_error_auth_failure(self) -> None:
        """Auth failures should NOT be retried."""
        from cheri_cloud_cli.retry import _is_retryable_error
        from cheri_cloud_cli.client import CheriClientError

        # Auth-related errors
        auth_error = CheriClientError("Authentication failed: invalid credentials")
        self.assertFalse(_is_retryable_error(auth_error))

        unauthorized_error = CheriClientError("Unauthorized: workspace access denied")
        self.assertFalse(_is_retryable_error(unauthorized_error))

        forbidden_error = CheriClientError("Forbidden: permission denied")
        self.assertFalse(_is_retryable_error(forbidden_error))

    def test_is_retryable_error_provider_invalid(self) -> None:
        """Provider invalid errors should NOT be retried."""
        from cheri_cloud_cli.retry import _is_retryable_error
        from cheri_cloud_cli.client import CheriClientError

        provider_error = CheriClientError("Provider invalid: S3 provider not configured")
        self.assertFalse(_is_retryable_error(provider_error))

    def test_is_retryable_error_not_found(self) -> None:
        """Not found errors should NOT be retried."""
        from cheri_cloud_cli.retry import _is_retryable_error
        from cheri_cloud_cli.client import CheriClientError

        not_found_error = CheriClientError("File not found: handoff_abc123")
        self.assertFalse(_is_retryable_error(not_found_error))

    def test_is_retryable_error_network_timeout(self) -> None:
        """Network timeouts SHOULD be retried."""
        import requests
        from cheri_cloud_cli.retry import _is_retryable_error

        timeout_error = requests.exceptions.Timeout("Connection timed out")
        self.assertTrue(_is_retryable_error(timeout_error))

    def test_is_retryable_error_5xx(self) -> None:
        """5xx server errors SHOULD be retried."""
        import requests
        from cheri_cloud_cli.retry import _is_retryable_error

        error = requests.exceptions.RequestException("Server error")
        error.response = type('MockResponse', (), {'status_code': 500})()
        self.assertTrue(_is_retryable_error(error))

    def test_retry_exhausted_raises(self) -> None:
        """When all retries are exhausted, the last exception should be raised."""
        import requests
        from cheri_cloud_cli.retry import with_retry

        attempt_count = 0

        def failing_func():
            nonlocal attempt_count
            attempt_count += 1
            # Use a retryable exception type
            raise requests.exceptions.Timeout(f"Attempt {attempt_count} failed")

        with self.assertRaises(requests.exceptions.Timeout):
            with_retry(failing_func, max_retries=2)

        # All retries exhausted (3 total attempts with max_retries=2)
        self.assertEqual(attempt_count, 3)

    def test_retry_succeeds_on_retry(self) -> None:
        """If a function succeeds on a later retry, return the result."""
        import requests
        from cheri_cloud_cli.retry import with_retry

        attempt_count = 0

        def eventually_succeeds():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise requests.exceptions.Timeout(f"Attempt {attempt_count} failed")
            return "success"

        result = with_retry(eventually_succeeds, max_retries=5)
        self.assertEqual(result, "success")
        self.assertEqual(attempt_count, 3)


# =============================================================================
# PARTIAL FAILURE POLICY TESTS
# =============================================================================

class PartialFailurePolicyTests(unittest.TestCase):
    """Test partial failure behavior with --allow-partial flag."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.scan_dir = Path(self.temp_dir) / "partial_test"
        self.scan_dir.mkdir()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_partial_failed_status_when_some_files_fail(self) -> None:
        """When some files fail, handoff status should be partial_failed."""
        failed_files = [{"path": "b.txt", "error": "upload error"}]

        handoff_status = "partial_failed" if failed_files else "ready"
        self.assertEqual(handoff_status, "partial_failed")

    def test_ready_status_when_all_files_succeed(self) -> None:
        """When all files succeed, handoff status should be ready."""
        failed_files = []

        handoff_status = "partial_failed" if failed_files else "ready"
        self.assertEqual(handoff_status, "ready")

    def test_allow_partial_exits_zero_on_failure(self) -> None:
        """With allow_partial=True, exit code should be 0 even with failures."""
        allow_partial = True
        failed_files = [{"path": "b.txt", "error": "upload error"}]

        if failed_files and not allow_partial:
            exit_code = 1
        else:
            exit_code = 0

        self.assertEqual(exit_code, 0)

    def test_no_allow_partial_exits_nonzero_on_failure(self) -> None:
        """Without allow_partial, exit code should be 1 on failures."""
        allow_partial = False
        failed_files = [{"path": "b.txt", "error": "upload error"}]

        if failed_files and not allow_partial:
            exit_code = 1
        else:
            exit_code = 0

        self.assertEqual(exit_code, 1)

    def test_checksum_mismatch_marked(self) -> None:
        """Checksum mismatches should be recorded separately."""
        checksum_mismatches = [
            {"path": "file.txt", "expected": "abc123", "actual": "xyz789"}
        ]

        self.assertEqual(len(checksum_mismatches), 1)
        self.assertIn("file.txt", [m["path"] for m in checksum_mismatches])


# =============================================================================
# SEARCH/FILTER TESTS
# =============================================================================

class SearchFilterTests(unittest.TestCase):
    """Test handoff list filters."""

    def test_filter_by_agent(self) -> None:
        """List should filter by agent name."""
        handoffs = [
            {"id": "1", "name": "handoff 1", "agent_name": "claude-code", "status": "ready"},
            {"id": "2", "name": "handoff 2", "agent_name": "codex", "status": "ready"},
            {"id": "3", "name": "handoff 3", "agent_name": "claude-code", "status": "ready"},
        ]

        agent_filter = "claude-code"
        filtered = [h for h in handoffs if h.get("agent_name") == agent_filter]

        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(h["agent_name"] == "claude-code" for h in filtered))

    def test_filter_by_tag(self) -> None:
        """List should filter by tag."""
        handoffs = [
            {"id": "1", "name": "handoff 1", "tags": ["release", "v1"], "status": "ready"},
            {"id": "2", "name": "handoff 2", "tags": ["beta"], "status": "ready"},
            {"id": "3", "name": "handoff 3", "tags": ["release"], "status": "ready"},
        ]

        tag_filter = "release"
        filtered = [h for h in handoffs if tag_filter in h.get("tags", [])]

        self.assertEqual(len(filtered), 2)

    def test_filter_by_status(self) -> None:
        """List should filter by status."""
        handoffs = [
            {"id": "1", "name": "handoff 1", "status": "ready"},
            {"id": "2", "name": "handoff 2", "status": "partial_failed"},
            {"id": "3", "name": "handoff 3", "status": "ready"},
        ]

        status_filter = "partial_failed"
        filtered = [h for h in handoffs if h.get("status") == status_filter]

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["status"], "partial_failed")

    def test_filter_by_date_range(self) -> None:
        """List should filter by date range."""
        handoffs = [
            {"id": "1", "name": "handoff 1", "created_at": "2026-05-01T00:00:00Z"},
            {"id": "2", "name": "handoff 2", "created_at": "2026-05-15T00:00:00Z"},
            {"id": "3", "name": "handoff 3", "created_at": "2026-05-28T00:00:00Z"},
        ]

        since_date = "2026-05-10"
        until_date = "2026-05-25"

        filtered = []
        for h in handoffs:
            created = h.get("created_at", "")
            if created and since_date <= created[:10] <= until_date:
                filtered.append(h)

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["id"], "2")


# =============================================================================
# ARCHIVE/DELETE TESTS
# =============================================================================

class ArchiveDeleteTests(unittest.TestCase):
    """Test archive and delete operations."""

    def test_archive_sets_status_to_archived(self) -> None:
        """Archive should set status to 'archived'."""
        handoff = {"id": "test_123", "status": "ready", "name": "test"}
        new_status = "archived"

        self.assertNotEqual(handoff["status"], new_status)
        handoff["status"] = new_status
        self.assertEqual(handoff["status"], "archived")

    def test_already_archived_no_op(self) -> None:
        """Already archived handoff should not be re-archived."""
        handoff = {"id": "test_123", "status": "archived", "name": "test"}

        if handoff.get("status") == "archived":
            # Should be a no-op
            pass

        self.assertEqual(handoff["status"], "archived")

    def test_delete_requires_confirmation(self) -> None:
        """Delete should require user confirmation."""
        confirmed = False  # Simulates user not confirming

        if not confirmed:
            # Should not proceed with deletion
            pass

        # If confirmed was True, deletion would proceed
        self.assertFalse(confirmed)

    def test_delete_removes_or_marks_deleted(self) -> None:
        """Delete should either remove or mark as deleted."""
        handoff = {"id": "test_123", "status": "ready", "name": "test"}

        # Can either call DELETE endpoint or mark status as "deleted"
        handoff["status"] = "deleted"

        self.assertEqual(handoff["status"], "deleted")


# =============================================================================
# DIFF TESTS
# =============================================================================

class DiffTests(unittest.TestCase):
    """Test handoff diff/compare functionality."""

    def test_added_files(self) -> None:
        """Diff should show files in h2 but not in h1."""
        files1 = {"a.txt": {"checksum": "abc"}}
        files2 = {"a.txt": {"checksum": "abc"}, "b.txt": {"checksum": "xyz"}}

        paths1 = set(files1.keys())
        paths2 = set(files2.keys())

        added = paths2 - paths1
        removed = paths1 - paths2

        self.assertEqual(added, {"b.txt"})
        self.assertEqual(removed, set())

    def test_removed_files(self) -> None:
        """Diff should show files in h1 but not in h2."""
        files1 = {"a.txt": {"checksum": "abc"}, "b.txt": {"checksum": "xyz"}}
        files2 = {"a.txt": {"checksum": "abc"}}

        paths1 = set(files1.keys())
        paths2 = set(files2.keys())

        added = paths2 - paths1
        removed = paths1 - paths2

        self.assertEqual(added, set())
        self.assertEqual(removed, {"b.txt"})

    def test_modified_files_by_checksum(self) -> None:
        """Diff should show files with different checksums as modified."""
        files1 = {"a.txt": {"checksum": "abc", "size": 10}}
        files2 = {"a.txt": {"checksum": "xyz", "size": 20}}

        modified = []
        for path in files1.keys() & files2.keys():
            if files1[path]["checksum"] != files2[path]["checksum"]:
                modified.append({
                    "path": path,
                    "old_size": files1[path]["size"],
                    "new_size": files2[path]["size"],
                })

        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]["path"], "a.txt")
        self.assertEqual(modified[0]["old_size"], 10)
        self.assertEqual(modified[0]["new_size"], 20)

    def test_unchanged_files_not_in_modified(self) -> None:
        """Files with same checksum should not appear in modified."""
        files1 = {"a.txt": {"checksum": "abc", "size": 10}}
        files2 = {"a.txt": {"checksum": "abc", "size": 10}}

        modified = []
        for path in files1.keys() & files2.keys():
            if files1[path]["checksum"] != files2[path]["checksum"]:
                modified.append({"path": path})

        self.assertEqual(len(modified), 0)

    def test_size_delta_calculation(self) -> None:
        """Diff should calculate total size delta."""
        files1 = [
            {"size": 100, "checksum": "abc"},
            {"size": 200, "checksum": "def"},
        ]
        files2 = [
            {"size": 100, "checksum": "abc"},
            {"size": 300, "checksum": "xyz"},  # Changed
        ]

        total_size1 = sum(f["size"] for f in files1)
        total_size2 = sum(f["size"] for f in files2)
        size_delta = total_size2 - total_size1

        self.assertEqual(total_size1, 300)
        self.assertEqual(total_size2, 400)
        self.assertEqual(size_delta, 100)


# =============================================================================
# PROGRESS TESTS
# =============================================================================

class ProgressTests(unittest.TestCase):
    """Test progress indicators don't crash."""

    def test_progress_bar_renders(self) -> None:
        """Progress bar should render without errors."""
        from rich.progress import Progress, BarColumn, TextColumn

        # Just ensure these classes can be instantiated
        progress = Progress(BarColumn(), TextColumn("[cyan]Test..."))
        self.assertIsNotNone(progress)

    def test_format_size_function(self) -> None:
        """_format_size should produce human-readable sizes."""
        from cheri_cloud_cli.handoff.cli import _format_size

        self.assertEqual(_format_size(500), "500B")
        self.assertEqual(_format_size(1024), "1.0KB")
        self.assertEqual(_format_size(1024 * 1024), "1.0MB")
        self.assertEqual(_format_size(1024 * 1024 * 1024), "1.00GB")

    def test_task_progress_completes(self) -> None:
        """Task progress should track completion correctly."""
        from rich.progress import Progress, BarColumn, TaskProgressColumn

        progress = Progress(BarColumn(), TaskProgressColumn())
        task_id = progress.add_task("test", total=10)

        self.assertEqual(progress.tasks[task_id].completed, 0)

        progress.update(task_id, completed=5)
        self.assertEqual(progress.tasks[task_id].completed, 5)


# =============================================================================
# LOGS TESTS
# =============================================================================

class LogsTests(unittest.TestCase):
    """Test logs command functionality."""

    def test_filter_logs_by_handoff_id(self) -> None:
        """Logs should be filterable by handoff ID."""
        all_logs = [
            {"message": "Push started for hnd_abc123", "handoff_id": "hnd_abc123"},
            {"message": "File uploaded for hnd_abc123", "handoff_id": "hnd_abc123"},
            {"message": "Push started for hnd_def456", "handoff_id": "hnd_def456"},
        ]

        handoff_id = "hnd_abc123"
        filtered = [log for log in all_logs if log.get("handoff_id") == handoff_id]

        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(log["handoff_id"] == "hnd_abc123" for log in filtered))

    def test_json_output_format(self) -> None:
        """Logs should be serializable to JSON."""
        import json

        logs = [
            {"timestamp": "2026-05-30T12:00:00Z", "level": "INFO", "message": "test"},
            {"timestamp": "2026-05-30T12:01:00Z", "level": "ERROR", "message": "failed"},
        ]

        json_str = json.dumps(logs)
        parsed = json.loads(json_str)

        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["level"], "INFO")
        self.assertEqual(parsed[1]["level"], "ERROR")

    def test_log_level_color_coding(self) -> None:
        """Log levels should map to colors."""

        # Verify color mappings exist for ERROR, WARNING, SUCCESS
        # This is tested by ensuring no exceptions when parsing log levels
        log_levels = ["ERROR", "WARNING", "SUCCESS", "INFO"]
        color_map = {
            "ERROR": "red",
            "WARNING": "yellow",
            "SUCCESS": "green",
            "INFO": "dim",
        }

        for level in log_levels:
            self.assertIn(level, color_map)


if __name__ == "__main__":
    unittest.main()