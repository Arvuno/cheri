"""Local credential storage backends."""

from __future__ import annotations

import json
import os
import stat
import sys
import warnings
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Protocol

from ..config import get_legacy_config_dir, get_paths
from ..contracts import AuthState

_KEYRING_SERVICE_NAME = "cheri"


class KeyringBackend(Protocol):
    """Minimal protocol for keyring backend objects."""

    def get_password(self, service: str, username: str) -> str | None: ...
    def set_password(self, service: str, username: str, password: str) -> None: ...
    def delete_password(self, service: str, username: str) -> None: ...


class CredentialStore(ABC):
    @abstractmethod
    def load(self) -> Optional[AuthState]:
        raise NotImplementedError

    @abstractmethod
    def save(self, state: AuthState, *, persist_bootstrap_secret: bool | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        raise NotImplementedError


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _best_effort_restrict_directory(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            os.chmod(path, 0o700)
    except OSError:
        return


def _best_effort_restrict_file(path: Path) -> None:
    try:
        if os.name != "nt":
            os.chmod(path, 0o600)
        else:
            os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
    except OSError:
        return


def _write_json(path: Path, payload: dict, *, private: bool) -> None:
    _best_effort_restrict_directory(path.parent)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if private:
        _best_effort_restrict_file(tmp_path)
    tmp_path.replace(path)
    if private:
        _best_effort_restrict_file(path)


class JsonCredentialStore(CredentialStore):
    """File-backed storage with public state split from secret-bearing credentials."""

    def __init__(self) -> None:
        self.paths = get_paths()

    @property
    def location(self) -> Path:
        return self.paths.state_file

    @property
    def secret_location(self) -> Path:
        return self.paths.secret_file

    @property
    def legacy_location(self) -> Path:
        return get_legacy_config_dir() / "state.json"

    def has_saved_state(self) -> bool:
        return self.location.exists() or self.secret_location.exists() or self.legacy_location.exists()

    def describe_locations(self) -> str:
        return f"{self.location} and {self.secret_location}"

    def _load_split_payload(self) -> Optional[dict]:
        if self.location.exists() or self.secret_location.exists():
            public_payload = _read_json(self.location) if self.location.exists() else {"format_version": 2}
            secret_payload = _read_json(self.secret_location) if self.secret_location.exists() else {"format_version": 2}
            return {
                "format_version": 2,
                **public_payload,
                **secret_payload,
            }
        if self.legacy_location.exists():
            return _read_json(self.legacy_location)
        return None

    def _public_payload(self, state: AuthState) -> dict:
        return {
            "format_version": 2,
            "identity": state.identity.to_dict(),
            "workspace_access": state.workspace_access.to_dict(),
        }

    def _secret_payload(self, state: AuthState, *, persist_bootstrap_secret: bool) -> dict:
        return {
            "format_version": 2,
            "session": state.session.to_dict(),
            "bootstrap": {"secret": state.bootstrap.secret if persist_bootstrap_secret else ""},
        }

    def load(self) -> Optional[AuthState]:
        payload = self._load_split_payload()
        if not payload:
            return None
        return AuthState.from_local_payload(payload)

    def save(self, state: AuthState, *, persist_bootstrap_secret: bool | None = None) -> None:
        existing = self.load()
        should_persist_bootstrap = (
            bool(existing.bootstrap_secret) if persist_bootstrap_secret is None and existing else persist_bootstrap_secret
        )
        public_payload = self._public_payload(state)
        secret_payload = self._secret_payload(state, persist_bootstrap_secret=bool(should_persist_bootstrap))
        _write_json(self.location, public_payload, private=False)
        _write_json(self.secret_location, secret_payload, private=True)
        if self.legacy_location.exists() and self.legacy_location != self.location:
            try:
                self.legacy_location.unlink()
            except OSError:
                pass

    def clear(self) -> None:
        for path in (self.location, self.secret_location, self.legacy_location):
            if path.exists():
                path.unlink()


def _get_keyring() -> KeyringBackend | None:
    try:
        import keyring

        return keyring
    except Exception:
        return None


def _is_headless() -> bool:
    if sys.platform == "win32" or sys.platform == "darwin":
        return False
    if os.environ.get("DISPLAY"):
        return False
    if os.environ.get("WAYLAND_DISPLAY"):
        return False
    if os.environ.get("CHERI_FORCE_KEYRING"):
        return False
    return True


class KeyringCredentialStore(CredentialStore):
    """Secure credential store using OS keyring when available.

    Falls back to protected JSON file storage in headless environments
    (containers, servers, WSL without desktop) where keyring is unavailable.

    Migration: on first load with keyring available, reads existing plaintext
    credentials.json and stores secrets in the OS keychain, then sanitizes
    the plaintext file.
    """

    _SESSION_KEY = "cheri.session_token"
    _BOOTSTRAP_KEY = "cheri.bootstrap_secret"

    def __init__(self) -> None:
        self.paths = get_paths()
        self._keyring: KeyringBackend | None = _get_keyring()
        self._use_keyring = self._keyring is not None and not _is_headless()
        self._fallback_warned = False

    @property
    def keyring_available(self) -> bool:
        return self._use_keyring

    def _public_payload(self, state: AuthState) -> dict:
        return {
            "format_version": 2,
            "identity": state.identity.to_dict(),
            "workspace_access": state.workspace_access.to_dict(),
        }

    def _warn_fallback(self) -> None:
        if self._fallback_warned:
            return
        self._fallback_warned = True
        warnings.warn(
            "OS keyring is not available. Credentials are stored in a protected local file "
            "that may not be encrypted. Do not use this in untrusted multi-user environments.",
            UserWarning,
            stacklevel=2,
        )

    def _migrate_from_json_if_needed(self) -> Optional[AuthState]:
        """One-time migration: read plaintext credentials, store to keyring, create new state file."""
        legacy_cred_path = get_legacy_config_dir() / "credentials.json"
        if not legacy_cred_path.exists():
            return None
        try:
            payload = _read_json(legacy_cred_path)
            session_token = payload.get("session_token", "") or payload.get("session", {}).get("token", "")
            bootstrap_secret = (
                payload.get("bootstrap_secret", "") or payload.get("bootstrap", {}).get("secret", "")
            )
            if not session_token and not bootstrap_secret:
                return None
            identity = payload.get("identity", {})
            workspace_access = payload.get("workspace_access", {})
            if self._use_keyring and self._keyring is not None:
                if session_token:
                    self._keyring.set_password(_KEYRING_SERVICE_NAME, self._SESSION_KEY, session_token)
                if bootstrap_secret:
                    self._keyring.set_password(_KEYRING_SERVICE_NAME, self._BOOTSTRAP_KEY, bootstrap_secret)
            else:
                secret_payload = {
                    "format_version": 2,
                    "session": {"token": session_token},
                    "bootstrap": {"secret": bootstrap_secret},
                }
                _write_json(self.paths.secret_file, secret_payload, private=True)
            new_state_payload = {
                "format_version": 2,
                "identity": identity,
                "workspace_access": workspace_access,
            }
            _write_json(self.paths.state_file, new_state_payload, private=False)
            sanitized = {
                "format_version": 2,
                "migrated_at": "2026-05-30T00:00:00+00:00",
                "note": "secrets moved to OS keyring or protected file",
            }
            _write_json(legacy_cred_path, sanitized, private=True)
            return None
        except Exception:
            return None

    def load(self) -> Optional[AuthState]:
        self._migrate_from_json_if_needed()
        public_path = self.paths.state_file
        if not public_path.exists():
            return None
        try:
            public_payload = _read_json(public_path)
        except Exception:
            return None
        session_token = ""
        bootstrap_secret = ""
        if self._use_keyring and self._keyring is not None:
            try:
                session_token = str(self._keyring.get_password(_KEYRING_SERVICE_NAME, self._SESSION_KEY) or "")
            except Exception:
                pass
            try:
                bootstrap_secret = str(self._keyring.get_password(_KEYRING_SERVICE_NAME, self._BOOTSTRAP_KEY) or "")
            except Exception:
                pass
        else:
            self._warn_fallback()
            secret_payload = _read_json(self.paths.secret_file)
            session_token = secret_payload.get("session", {}).get("token", "")
            bootstrap_secret = secret_payload.get("bootstrap", {}).get("secret", "")
        from ..contracts import AuthState as AS

        combined = {**public_payload, "session_token": session_token, "bootstrap_secret": bootstrap_secret}
        return AS.from_local_payload(combined)

    def save(self, state: AuthState, *, persist_bootstrap_secret: bool | None = None) -> None:
        existing = self.load()
        should_persist = (
            bool(existing and existing.bootstrap_secret if persist_bootstrap_secret is None else persist_bootstrap_secret)
        )
        _write_json(self.paths.state_file, self._public_payload(state), private=False)
        if self._use_keyring and self._keyring is not None:
            try:
                self._keyring.set_password(_KEYRING_SERVICE_NAME, self._SESSION_KEY, state.session_token)
            except Exception:
                pass
            try:
                if should_persist:
                    self._keyring.set_password(_KEYRING_SERVICE_NAME, self._BOOTSTRAP_KEY, state.bootstrap_secret)
                else:
                    try:
                        self._keyring.delete_password(_KEYRING_SERVICE_NAME, self._BOOTSTRAP_KEY)
                    except Exception:
                        pass
            except Exception:
                pass
        else:
            self._warn_fallback()
            secret_payload = {
                "format_version": 2,
                "session": state.session.to_dict(),
                "bootstrap": {"secret": state.bootstrap.secret if should_persist else ""},
            }
            _write_json(self.paths.secret_file, secret_payload, private=True)

    def clear(self) -> None:
        if self._use_keyring and self._keyring is not None:
            try:
                self._keyring.delete_password(_KEYRING_SERVICE_NAME, self._SESSION_KEY)
            except Exception:
                pass
            try:
                self._keyring.delete_password(_KEYRING_SERVICE_NAME, self._BOOTSTRAP_KEY)
            except Exception:
                pass
        for path in (self.paths.state_file, self.paths.secret_file, get_legacy_config_dir() / "state.json"):
            if path.exists():
                path.unlink()


# Alias for backwards compatibility
SecureCredentialStore = KeyringCredentialStore
