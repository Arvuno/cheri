"""Handoff service for creating, pushing, and managing handoffs."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..client import CheriClient
from ..sessions import JsonCredentialStore, load_authenticated_state


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_git_context(source_path: str) -> Optional[dict]:
    """Try to get git context for a path. Returns None if not in a git repo."""
    try:
        # Find the git repo root
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=source_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None

        repo_root = result.stdout.strip()

        # Get branch
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"

        # Get commit hash
        hash_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        commit_hash = hash_result.stdout.strip()[:12] if hash_result.returncode == 0 else "unknown"

        # Check dirty status
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        dirty = len(status_result.stdout.strip()) > 0 if status_result.returncode == 0 else False

        # Get remote URL (redacted if it contains credentials)
        remote_result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        remote_url = remote_result.stdout.strip() if remote_result.returncode == 0 else None
        # Redact any embedded credentials in URL
        if remote_url and ("://" in remote_url):
            # Simple redaction - remove user:pass@ if present
            import re
            remote_url = re.sub(r"://[^@]+@", "://", remote_url)

        return {
            "branch": branch,
            "commit_hash": commit_hash,
            "dirty": dirty,
            "remote_url": remote_url,
        }
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def create_manifest(
    source_path: str,
    name: str,
    description: str = "",
    tags: Optional[list[str]] = None,
    agent_name: Optional[str] = None,
    tool_name: Optional[str] = None,
    version_label: Optional[str] = None,
    include_sensitive: bool = False,
    notes: str = "",
) -> dict:
    """
    Create a handoff manifest for a path.

    Returns the manifest dict (does NOT write to disk).
    """
    from . import HandoffFile, HandoffManifest, GitContext, scan_directory, DEFAULT_EXCLUDE_PATTERNS

    path = Path(source_path)
    if not path.exists():
        raise FileNotFoundError(f"Path not found: {source_path}")

    is_dir = path.is_dir()
    source_context = "directory" if is_dir else "file"

    # Scan the directory/file
    if is_dir:
        files, skipped = scan_directory(path, recursive=True, exclude_patterns=DEFAULT_EXCLUDE_PATTERNS, include_sensitive=include_sensitive)
        total_size = sum(f.size for f in files)
        file_count = len(files)
    else:
        from . import calculate_checksum, get_content_type
        skipped = []
        stat = path.stat()
        checksum = calculate_checksum(path)
        content_type = get_content_type(path)
        files = [HandoffFile(
            relative_path=path.name,
            size=stat.st_size,
            checksum=checksum,
            content_type=content_type,
        )]
        total_size = stat.st_size
        file_count = 1

    # Git context
    git_ctx = None
    git_data = _get_git_context(source_path)
    if git_data:
        git_ctx = GitContext(
            branch=git_data["branch"],
            commit_hash=git_data["commit_hash"],
            dirty=git_data["dirty"],
            remote_url=git_data.get("remote_url"),
        )

    manifest = HandoffManifest(
        schema_version="1.0",
        name=name,
        description=description,
        tags=tags or [],
        generated_at=_now_iso(),
        source_path=str(path.absolute()),
        source_context=source_context,
        git_context=git_ctx,
        files=files,
        skipped_sensitive=skipped,
        notes=notes,
        agent_name=agent_name,
        tool_name=tool_name,
        version_label=version_label,
    )

    # Add metadata not in the manifest file itself
    result = manifest.to_dict()
    result["_file_count"] = file_count
    result["_total_size"] = total_size

    return result


def write_manifest(manifest: dict, output_dir: str) -> Path:
    """Write a manifest JSON file to the output directory."""
    output_path = Path(output_dir)
    if not output_path.exists():
        output_path.mkdir(parents=True, exist_ok=True)

    manifest_path = output_path / "cheri-handoff.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return manifest_path


def list_handoffs(client: CheriClient, store: JsonCredentialStore, workspace_id: Optional[str] = None) -> list[dict]:
    """List handoffs in a workspace."""
    state = load_authenticated_state(client, store)
    if not state.active_workspace:
        raise ValueError("No active workspace. Use --workspace to specify one.")

    ws_id = workspace_id or state.active_workspace.id
    return client.list_handoffs(state, ws_id)


def get_handoff(client: CheriClient, store: JsonCredentialStore, handoff_id: str) -> dict:
    """Get a handoff by ID."""
    state = load_authenticated_state(client, store)
    return client.get_handoff(state, handoff_id)


def get_latest_handoff(client: CheriClient, store: JsonCredentialStore, workspace_id: Optional[str] = None) -> dict:
    """Get the latest handoff for a workspace."""
    state = load_authenticated_state(client, store)
    ws_id = workspace_id or (state.active_workspace.id if state.active_workspace else None)
    if not ws_id:
        raise ValueError("No active workspace. Use --workspace to specify one.")
    return client.get_latest_handoff(state, ws_id)


def create_handoff_metadata(
    client: CheriClient,
    store: JsonCredentialStore,
    manifest: dict,
    workspace_id: Optional[str] = None,
) -> dict:
    """Create handoff metadata on the backend."""
    state = load_authenticated_state(client, store)
    ws_id = workspace_id or (state.active_workspace.id if state.active_workspace else None)
    if not ws_id:
        raise ValueError("No active workspace. Use --workspace to specify one.")

    return client.create_handoff(state, ws_id, manifest)


def upload_handoff_file(
    client: CheriClient,
    state,
    source_path: Path,
    handoff_id: str,
    relative_path: str,
    workspace_id: str,
) -> dict:
    """
    Upload a single handoff file through the workspace storage provider.
    Returns dict with file_id, storage_key, provider_id, uploaded_at.
    """
    logical_name = f"handoffs/{handoff_id}/{relative_path}"

    # Use the existing upload flow from files/service.py
    from ..files.service import upload_path_once

    remote_file = upload_path_once(
        client,
        state,
        source_path,
        workspace_id=workspace_id,
        show_progress=False,
        logical_name=logical_name,
    )

    return {
        "file_id": remote_file.id,
        "storage_key": logical_name,
        "provider_id": getattr(remote_file, 'provider_id', None) or "system",
        "uploaded_at": getattr(remote_file, 'modified_at', None) or datetime.now(timezone.utc).isoformat(),
        "upload_status": "uploaded",
    }