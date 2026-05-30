"""Tests for session credential stores."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch, MagicMock

from cheri_cloud_cli.config import get_legacy_config_dir
from cheri_cloud_cli.contracts import AuthState
from cheri_cloud_cli.sessions.store import (
    JsonCredentialStore,
    KeyringCredentialStore,
)


def sample_auth_state() -> AuthState:
    return AuthState.from_payload(
        {
            "identity": {
                "id": "usr_123",
                "username": "alice",
                "created_at": "2026-03-15T00:00:00+00:00",
            },
            "session": {
                "token": "tok_1234567890abcdef",
                "issued_at": "2026-03-15T00:00:00+00:00",
                "id": "ses_123",
            },
            "bootstrap": {
                "secret": "amber anchor apple atlas bamboo beacon berry birch candle cedar cloud cobalt",
            },
            "workspace_access": {
                "active_workspace_id": "ws_123",
                "workspaces": [
                    {
                        "id": "ws_123",
                        "name": "docs",
                        "slug": "docs",
                        "role": "admin",
                        "created_at": "2026-03-15T00:00:00+00:00",
                        "joined_at": "2026-03-15T00:00:00+00:00",
                        "provider": {
                            "kind": "system",
                            "label": "System (recommended)",
                            "temporary": True,
                            "recommended": True,
                            "reset_policy": "daily",
                            "validation": {"state": "ready", "available": True},
                        },
                    }
                ],
            },
        }
    )


class JsonCredentialStoreTests(unittest.TestCase):
    def test_store_splits_public_and_secret_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"CHERI_CONFIG_DIR": temp_dir}, clear=False):
                store = JsonCredentialStore()
                state = sample_auth_state()

                store.save(state, persist_bootstrap_secret=False)

                public_payload = json.loads(Path(store.location).read_text(encoding="utf-8"))
                secret_payload = json.loads(Path(store.secret_location).read_text(encoding="utf-8"))

                self.assertIn("identity", public_payload)
                self.assertIn("workspace_access", public_payload)
                self.assertNotIn("session", public_payload)
                self.assertNotIn("bootstrap", public_payload)

                self.assertIn("session", secret_payload)
                self.assertEqual(secret_payload["session"]["token"], state.session_token)
                self.assertEqual(secret_payload["bootstrap"]["secret"], "")

                loaded = store.load()
                self.assertIsNotNone(loaded)
                self.assertEqual(loaded.session_token, state.session_token)
                self.assertEqual(loaded.bootstrap_secret, "")

    def test_store_can_persist_bootstrap_secret_when_explicitly_requested(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"CHERI_CONFIG_DIR": temp_dir}, clear=False):
                store = JsonCredentialStore()
                state = sample_auth_state()

                store.save(state, persist_bootstrap_secret=True)

                loaded = store.load()
                self.assertEqual(loaded.bootstrap_secret, state.bootstrap_secret)

    def test_clear_removes_both_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"CHERI_CONFIG_DIR": temp_dir}, clear=False):
                store = JsonCredentialStore()
                state = sample_auth_state()
                store.save(state, persist_bootstrap_secret=True)

                self.assertTrue(store.location.exists())
                self.assertTrue(store.secret_location.exists())

                store.clear()

                self.assertFalse(store.location.exists())
                self.assertFalse(store.secret_location.exists())
                self.assertIsNone(store.load())

    def test_migration_from_legacy_credentials_json(self) -> None:
        """Legacy credentials.json is read by store but secrets are not retained as plaintext."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"CHERI_CONFIG_DIR": temp_dir}, clear=False):
                legacy_path = Path(temp_dir) / "credentials.json"
                legacy_path.write_text(
                    json.dumps(
                        {
                            "session_token": "legacy_tok_abc123",
                            "bootstrap_secret": "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12",
                            "identity": {"id": "usr_old", "username": "olduser", "created_at": "2026-01-01T00:00:00+00:00"},
                        }
                    ),
                    encoding="utf-8",
                )
                store = JsonCredentialStore()
                loaded = store.load()
                self.assertIsNotNone(loaded)
                self.assertEqual(loaded.session_token, "legacy_tok_abc123")
                self.assertEqual(loaded.bootstrap_secret, "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12")


class KeyringCredentialStoreTests(unittest.TestCase):
    def test_keyring_store_saves_and_loads_session_token(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"CHERI_CONFIG_DIR": temp_dir}, clear=False):
                mock_keyring = MagicMock()
                store = KeyringCredentialStore()
                store._keyring = mock_keyring
                store._use_keyring = True
                state = sample_auth_state()

                store.save(state, persist_bootstrap_secret=False)

                mock_keyring.set_password.assert_any_call("cheri", "cheri.session_token", state.session_token)
                calls = mock_keyring.set_password.call_args_list
                bootstrap_call = [c for c in calls if c[0][1] == "cheri.bootstrap_secret"]
                self.assertEqual(len(bootstrap_call), 0)

    def test_keyring_store_saves_bootstrap_secret_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"CHERI_CONFIG_DIR": temp_dir}, clear=False):
                mock_keyring = MagicMock()
                store = KeyringCredentialStore()
                store._keyring = mock_keyring
                store._use_keyring = True
                state = sample_auth_state()

                store.save(state, persist_bootstrap_secret=True)

                mock_keyring.set_password.assert_any_call("cheri", "cheri.bootstrap_secret", state.bootstrap_secret)

    def test_keyring_store_loads_from_keyring(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"CHERI_CONFIG_DIR": temp_dir}, clear=False):
                mock_keyring = MagicMock()
                mock_keyring.get_password.side_effect = lambda svc, key, **kw: {
                    ("cheri", "cheri.session_token"): "tok_from_keyring",
                    ("cheri", "cheri.bootstrap_secret"): "keyring bootstrap",
                }.get((svc, key), None)

                store = KeyringCredentialStore()
                store._keyring = mock_keyring
                store._use_keyring = True

                state_file = store.paths.state_file
                state_file.parent.mkdir(parents=True, exist_ok=True)
                state_file.write_text(
                    json.dumps(
                        {
                            "format_version": 2,
                            "identity": {"id": "usr_kr", "username": "keyringuser", "created_at": "2026-03-15T00:00:00+00:00"},
                            "workspace_access": {
                                "active_workspace_id": "ws_kr",
                                "workspaces": [],
                            },
                        }
                    ),
                    encoding="utf-8",
                )

                loaded = store.load()
                self.assertIsNotNone(loaded)
                self.assertEqual(loaded.session_token, "tok_from_keyring")
                self.assertEqual(loaded.bootstrap_secret, "keyring bootstrap")

    def test_keyring_store_fallback_warns_when_keyring_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"CHERI_CONFIG_DIR": temp_dir}, clear=False):
                mock_keyring = MagicMock()
                store = KeyringCredentialStore()
                store._keyring = mock_keyring
                store._use_keyring = False
                store._fallback_warned = False
                state = sample_auth_state()

                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    store.save(state, persist_bootstrap_secret=True)

                    keyring_warnings = [x for x in w if "keyring" in str(x.message).lower()]
                    self.assertTrue(len(keyring_warnings) >= 1)

    def test_keyring_store_migrates_legacy_json_to_keyring(self) -> None:
        import shutil

        legacy_path = get_legacy_config_dir() / "credentials.json"
        get_legacy_config_dir().mkdir(parents=True, exist_ok=True)
        try:
            mock_keyring = MagicMock()
            with patch("cheri_cloud_cli.sessions.store._get_keyring", return_value=mock_keyring):
                store = KeyringCredentialStore()
                self.assertTrue(store.keyring_available)

            legacy_path.write_text(
                json.dumps(
                    {
                        "session_token": "migrated_tok",
                        "bootstrap_secret": "migrated bootstrap words one two three four five six seven eight nine ten eleven twelve",
                    }
                ),
                encoding="utf-8",
            )

            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                store._migrate_from_json_if_needed()

            mock_keyring.set_password.assert_any_call("cheri", "cheri.session_token", "migrated_tok")
            mock_keyring.set_password.assert_any_call(
                "cheri",
                "cheri.bootstrap_secret",
                "migrated bootstrap words one two three four five six seven eight nine ten eleven twelve",
            )

            sanitized = json.loads(legacy_path.read_text(encoding="utf-8"))
            self.assertNotIn("session_token", sanitized)
            self.assertNotIn("bootstrap_secret", sanitized)
            self.assertIn("note", sanitized)
        finally:
            if legacy_path.exists():
                legacy_path.unlink()
            try:
                shutil.rmtree(get_legacy_config_dir())
            except Exception:
                pass

    def test_no_plaintext_bootstrap_secret_after_keyring_migration(self) -> None:
        import shutil

        legacy_path = get_legacy_config_dir() / "credentials.json"
        get_legacy_config_dir().mkdir(parents=True, exist_ok=True)
        try:
            legacy_path.write_text(
                json.dumps(
                    {
                        "session_token": "secret_tok",
                        "bootstrap_secret": "my secret bootstrap phrase",
                    }
                ),
                encoding="utf-8",
            )

            mock_keyring = MagicMock()
            with patch("cheri_cloud_cli.sessions.store._get_keyring", return_value=mock_keyring):
                store = KeyringCredentialStore()
                self.assertTrue(store.keyring_available)

            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                store._migrate_from_json_if_needed()

            sanitized = json.loads(legacy_path.read_text(encoding="utf-8"))
            self.assertNotIn("secret_tok", json.dumps(sanitized))
            self.assertNotIn("my secret", json.dumps(sanitized))
        finally:
            if legacy_path.exists():
                legacy_path.unlink()
            try:
                shutil.rmtree(get_legacy_config_dir())
            except Exception:
                pass

    def test_fallback_when_keyring_not_installed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"CHERI_CONFIG_DIR": temp_dir}, clear=False):
                with patch("cheri_cloud_cli.sessions.store._get_keyring", return_value=None):
                    store = KeyringCredentialStore()
                    self.assertFalse(store.keyring_available)

    def test_clear_removes_keyring_entries_and_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"CHERI_CONFIG_DIR": temp_dir}, clear=False):
                mock_keyring = MagicMock()
                store = KeyringCredentialStore()
                store._keyring = mock_keyring
                store._use_keyring = True
                state = sample_auth_state()
                store.save(state, persist_bootstrap_secret=True)

                store.clear()

                mock_keyring.delete_password.assert_any_call("cheri", "cheri.session_token")
                mock_keyring.delete_password.assert_any_call("cheri", "cheri.bootstrap_secret")


if __name__ == "__main__":
    unittest.main()