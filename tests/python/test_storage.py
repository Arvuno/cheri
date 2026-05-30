"""Tests for storage CLI commands."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from cheri_cloud_cli.storage import (
    list_storage_providers,
    show_storage_status,
    check_storage_connectivity,
)


class MockProviderCatalog:
    def __init__(self, providers):
        self._providers = providers

    def get_provider_catalog(self, include_experimental=False):
        if include_experimental:
            return self._providers
        return [p for p in self._providers if not p.get("experimental")]


class MockAuthState:
    def __init__(self, active_workspace_id="ws_active"):
        self.active_workspace_id = active_workspace_id

    @property
    def session_token(self):
        return "mock_token"

    @property
    def bootstrap_secret(self):
        return ""


SAMPLE_CATALOG = [
    {
        "kind": "system",
        "label": "System (recommended)",
        "description": "Worker-managed temporary storage.",
        "selectable": True,
        "coming_soon": False,
        "experimental": False,
        "recommended": True,
        "temporary": True,
        "reset_policy": "daily",
        "integration_status": "connected",
        "credential_fields": [],
    },
    {
        "kind": "s3-compatible",
        "label": "S3-compatible",
        "description": "Use an S3-style bucket.",
        "selectable": False,
        "coming_soon": True,
        "experimental": True,
        "recommended": False,
        "temporary": False,
        "reset_policy": "",
        "integration_status": "scaffolded",
        "credential_fields": [
            {"key": "endpoint", "label": "Endpoint URL", "required": True, "secret": False},
            {"key": "secret_access_key", "label": "Secret access key", "required": True, "secret": True},
        ],
    },
]


class ListStorageProvidersTests(unittest.TestCase):
    def test_lists_providers_without_experimental(self):
        mock_client = MagicMock()
        mock_client.get_provider_catalog.return_value = SAMPLE_CATALOG

        with patch("cheri_cloud_cli.storage.console"):
            list_storage_providers(mock_client, include_experimental=False)
            mock_client.get_provider_catalog.assert_called_once_with(include_experimental=False)

    def test_lists_providers_with_experimental(self):
        mock_client = MagicMock()
        mock_client.get_provider_catalog.return_value = SAMPLE_CATALOG

        with patch("cheri_cloud_cli.storage.console"):
            list_storage_providers(mock_client, include_experimental=True)
            mock_client.get_provider_catalog.assert_called_once_with(include_experimental=True)

    def test_warns_about_experimental_when_excluded(self):
        mock_client = MagicMock()
        mock_client.get_provider_catalog.return_value = SAMPLE_CATALOG

        with patch("cheri_cloud_cli.storage.console"):
            list_storage_providers(mock_client, include_experimental=False)

    def test_handles_client_error_gracefully(self):
        from cheri_cloud_cli.client import CheriClientError

        mock_client = MagicMock()
        mock_client.get_provider_catalog.side_effect = CheriClientError("Network error")

        with patch("cheri_cloud_cli.storage.console"):
            list_storage_providers(mock_client)


class ShowStorageStatusTests(unittest.TestCase):
    def test_shows_status_for_active_workspace(self):
        mock_client = MagicMock()
        mock_store = MagicMock()

        mock_workspace = MagicMock()
        mock_workspace.to_dict.return_value = {
            "id": "ws_active",
            "name": "active-workspace",
            "slug": "active-workspace",
            "storage": {
                "provider": {
                    "kind": "system",
                    "label": "System (recommended)",
                    "reset_policy": "daily",
                    "validation": {
                        "state": "ready",
                        "available": True,
                        "warnings": [],
                        "errors": [],
                    },
                }
            },
        }

        mock_client.list_workspaces.return_value = [mock_workspace]

        with patch("cheri_cloud_cli.storage.load_authenticated_state") as mock_load:
            mock_load.return_value = MockAuthState(active_workspace_id="ws_active")

            with patch("cheri_cloud_cli.storage.console"):
                show_storage_status(mock_client, mock_store)

    def test_handles_no_active_workspace(self):
        mock_client = MagicMock()
        mock_store = MagicMock()

        with patch("cheri_cloud_cli.storage.load_authenticated_state") as mock_load:
            mock_load.return_value = MockAuthState(active_workspace_id=None)

            with patch("cheri_cloud_cli.storage.console"):
                show_storage_status(mock_client, mock_store)

    def test_handles_not_logged_in(self):
        mock_client = MagicMock()
        mock_store = MagicMock()

        with patch("cheri_cloud_cli.storage.load_authenticated_state") as mock_load:
            mock_load.return_value = None

            with patch("cheri_cloud_cli.storage.console"):
                show_storage_status(mock_client, mock_store)


class CheckStorageConnectivityTests(unittest.TestCase):
    def test_reports_backend_health(self):
        mock_client = MagicMock()
        mock_client.healthcheck.return_value = {"product": "Cheri CLI API", "ok": True}
        mock_client.get_provider_catalog.return_value = SAMPLE_CATALOG

        with patch("cheri_cloud_cli.storage.console"):
            check_storage_connectivity(mock_client)

    def test_handles_backend_unreachable(self):
        from cheri_cloud_cli.client import CheriClientError

        mock_client = MagicMock()
        mock_client.healthcheck.side_effect = CheriClientError("Connection refused")

        with patch("cheri_cloud_cli.storage.console"):
            check_storage_connectivity(mock_client)


if __name__ == "__main__":
    unittest.main()