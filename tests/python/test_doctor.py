"""Tests for cheri init and doctor commands."""

from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from click.testing import CliRunner

from cheri_cloud_cli.cli import cli


class InitCommandTests(unittest.TestCase):
    def test_init_non_interactive_skips_interaction(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as config_dir:
            with patch.dict("os.environ", {"CHERI_CONFIG_DIR": config_dir}, clear=False):
                result = runner.invoke(cli, ["init", "--non-interactive", "--skip-upload", "--skip-task"])
        self.assertIn("Welcome", result.output)
        self.assertIn("Backend API", result.output)

    def test_init_existing_logged_in_state(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as config_dir:
            with patch.dict("os.environ", {"CHERI_CONFIG_DIR": config_dir}, clear=False):
                with patch("cheri_cloud_cli.init._check_auth_state") as mock_auth:
                    mock_auth.return_value = (True, "alice")
                    result = runner.invoke(cli, ["init", "--non-interactive", "--skip-upload", "--skip-task"])
        self.assertIn("alice", result.output)


class DoctorCommandTests(unittest.TestCase):
    def test_doctor_healthy_state(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as config_dir:
            with patch.dict("os.environ", {"CHERI_CONFIG_DIR": config_dir}, clear=False):
                result = runner.invoke(cli, ["doctor"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("CLI Version", result.output)
        self.assertIn("Python Version", result.output)

    def test_doctor_json_mode_flag_accepted(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as config_dir:
            with patch.dict("os.environ", {"CHERI_CONFIG_DIR": config_dir}, clear=False):
                result = runner.invoke(cli, ["doctor", "--json"])
        # JSON flag is accepted, exit code 0
        self.assertEqual(result.exit_code, 0)

    def test_doctor_missing_backend_shows_failure(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as config_dir:
            with patch.dict("os.environ", {"CHERI_CONFIG_DIR": config_dir}, clear=False):
                with patch("cheri_cloud_cli.doctor.CheriClient") as mock_client:
                    instance = mock_client.return_value
                    instance.healthcheck.side_effect = Exception("unreachable")
                    result = runner.invoke(cli, ["doctor"])
        self.assertIn("Backend Health", result.output)

    def test_doctor_release_check_non_zero_on_critical(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as config_dir:
            with patch.dict("os.environ", {"CHERI_CONFIG_DIR": config_dir}, clear=False):
                with patch("cheri_cloud_cli.doctor._check_backend_health") as mock:
                    mock.return_value = MagicMock(status="fail", name="Backend Health", message="unreachable")
                    result = runner.invoke(cli, ["doctor", "--release-check"])
        self.assertNotEqual(result.exit_code, 0)

    def test_doctor_unauthenticated_state(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as config_dir:
            with patch.dict("os.environ", {"CHERI_CONFIG_DIR": config_dir}, clear=False):
                with patch("cheri_cloud_cli.doctor.JsonCredentialStore") as mock_store:
                    mock_store.return_value.load.return_value = None
                    result = runner.invoke(cli, ["doctor"])
        self.assertIn("CLI Version", result.output)


class WorkspaceStatusTests(unittest.TestCase):
    def test_workspace_status_no_session(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as config_dir:
            with patch.dict("os.environ", {"CHERI_CONFIG_DIR": config_dir}, clear=False):
                result = runner.invoke(cli, ["workspace", "status"])
        self.assertIn("Not logged in", result.output)

    def test_workspace_status_json_output_no_session(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as config_dir:
            with patch.dict("os.environ", {"CHERI_CONFIG_DIR": config_dir}, clear=False):
                result = runner.invoke(cli, ["workspace", "status", "--json"])
        output = json.loads(result.output)
        self.assertIn("error", output)


if __name__ == "__main__":
    unittest.main()
