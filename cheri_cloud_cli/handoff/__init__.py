"""Handoff domain model for Cheri artifact handoff."""

from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class HandoffFile:
    """A file entry in a handoff manifest."""
    relative_path: str
    size: int
    checksum: str
    content_type: Optional[str] = None
    skipped: bool = False
    # Upload metadata fields (optional, populated after upload)
    file_id: Optional[str] = None
    storage_key: Optional[str] = None
    provider_id: Optional[str] = None
    uploaded_at: Optional[str] = None
    upload_status: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> HandoffFile:
        """Create a HandoffFile from a dict (handles v1.0 manifests without upload fields)."""
        return cls(
            relative_path=data["relative_path"],
            size=data["size"],
            checksum=data["checksum"],
            content_type=data.get("content_type"),
            skipped=data.get("skipped", False),
            file_id=data.get("file_id"),
            storage_key=data.get("storage_key"),
            provider_id=data.get("provider_id"),
            uploaded_at=data.get("uploaded_at"),
            upload_status=data.get("upload_status"),
        )

    def to_dict(self) -> dict:
        d = {
            "relative_path": self.relative_path,
            "size": self.size,
            "checksum": self.checksum,
        }
        if self.content_type:
            d["content_type"] = self.content_type
        if self.skipped:
            d["skipped"] = True
        # Only include upload metadata when set (not None)
        if self.file_id is not None:
            d["file_id"] = self.file_id
        if self.storage_key is not None:
            d["storage_key"] = self.storage_key
        if self.provider_id is not None:
            d["provider_id"] = self.provider_id
        if self.uploaded_at is not None:
            d["uploaded_at"] = self.uploaded_at
        if self.upload_status is not None:
            d["upload_status"] = self.upload_status
        return d


@dataclass
class GitContext:
    """Git context for a handoff."""
    branch: str
    commit_hash: str
    dirty: bool
    remote_url: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "branch": self.branch,
            "commit_hash": self.commit_hash,
            "dirty": self.dirty,
            "remote_url": self.remote_url,
        }


@dataclass
class HandoffManifest:
    """Handoff manifest with file listing and metadata."""
    schema_version: str = "1.1"
    handoff_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    generated_at: str = ""
    source_path: str = ""
    source_context: Optional[str] = None
    git_context: Optional[GitContext] = None
    files: list[HandoffFile] = field(default_factory=list)
    skipped_sensitive: list[str] = field(default_factory=list)
    notes: str = ""
    agent_name: Optional[str] = None
    tool_name: Optional[str] = None
    version_label: Optional[str] = None
    created_by: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "schema_version": self.schema_version,
            "handoff_id": self.handoff_id,
            "name": self.name,
        }
        # Only include fields with actual values (not empty defaults)
        if self.description:
            d["description"] = self.description
        if self.tags:
            d["tags"] = self.tags
        if self.generated_at:
            d["generated_at"] = self.generated_at
        if self.source_path:
            d["source_path"] = self.source_path
        d["files"] = [f.to_dict() for f in self.files]
        d["skipped_sensitive"] = self.skipped_sensitive
        if self.source_context:
            d["source_context"] = self.source_context
        if self.git_context:
            d["git_context"] = self.git_context.to_dict()
        if self.agent_name:
            d["agent_name"] = self.agent_name
        if self.tool_name:
            d["tool_name"] = self.tool_name
        if self.version_label:
            d["version_label"] = self.version_label
        if self.created_by:
            d["created_by"] = self.created_by
        return d


# Default secret-safe exclusion patterns (reused from task scanning)
DEFAULT_EXCLUDE_PATTERNS = [
    ".env",
    ".env.*",
    "*.env",
    "credentials.json",
    "*.key",
    "*.pem",
    "id_rsa",
    "id_ed25519",
    ".npmrc",
    ".pypirc",
    ".netrc",
    "secrets.json",
    "secret.json",
    ".git",
    ".DS_Store",
    "Thumbs.db",
    "*.swp",
    "*.swo",
    ".coverage.db",
]


def is_sensitive_path(path: str, exclude_patterns: Optional[list[str]] = None) -> bool:
    """Check if a path matches any sensitive/excluded pattern."""
    patterns = exclude_patterns or DEFAULT_EXCLUDE_PATTERNS
    path_lower = path.lower()
    path_normalized = path_lower.replace("\\", "/")

    # Get the basename (file/dir name without path)
    basename = os.path.basename(path_normalized)
    # Get all path segments for directory matching
    segments = path_normalized.split("/")

    for pattern in patterns:
        # Glob-style matching (e.g., "*.key", "*.pem", "*.env")
        if "*" in pattern:
            import fnmatch
            if fnmatch.fnmatch(path_normalized, pattern.lower()) or fnmatch.fnmatch(path_lower, pattern.lower()):
                return True
        else:
            # Exact segment match: pattern must match a full segment (directory or file name)
            # ".git" matches "/.git" or "foo/.git" but NOT ".gitignore"
            for seg in segments:
                if seg == pattern.lower():
                    return True

    # Extra check for common secret file names
    secret_names = {
        ".env", ".env.local", ".env.production", ".env.development",
        "credentials.json", "secrets.json", "secret.json",
        "id_rsa", "id_ed25519", "id_rsa.pub", "id_ed25519.pub",
        ".npmrc", ".pypirc", ".netrc",
        "aws_access_key", "aws_secret_key",
        "google_credentials.json", "gcloud credentials",
    }

    basename = os.path.basename(path)
    if basename in secret_names:
        return True

    return False


def calculate_checksum(path: Path) -> str:
    """Calculate SHA-256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_content_type(path: Path) -> Optional[str]:
    """Guess content type from file extension."""
    ext_map = {
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".json": "application/json",
        ".yaml": "text/yaml",
        ".yml": "text/yaml",
        ".py": "text/x-python",
        ".js": "text/javascript",
        ".ts": "text/typescript",
        ".tsx": "text/typescript+tsx",
        ".jsx": "text/javascript+jsx",
        ".html": "text/html",
        ".css": "text/css",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".pdf": "application/pdf",
        ".zip": "application/zip",
        ".tar": "application/x-tar",
        ".gz": "application/gzip",
    }
    return ext_map.get(path.suffix.lower())


def scan_directory(
    directory: Path,
    recursive: bool = True,
    exclude_patterns: Optional[list[str]] = None,
    include_sensitive: bool = False,
) -> tuple[list[HandoffFile], list[str]]:
    """
    Scan a directory and return (files, skipped_sensitive_paths).

    Does not follow symlinks.
    Respects exclude patterns.
    Does NOT read file contents of skipped files (secret-safe).
    """
    files: list[HandoffFile] = []
    skipped: list[str] = []

    patterns = exclude_patterns or DEFAULT_EXCLUDE_PATTERNS

    def _should_skip(path: Path) -> bool:
        if include_sensitive:
            return False
        rel = str(path.relative_to(directory) if directory in path.parents else path)
        if is_sensitive_path(rel, patterns):
            return True
        if is_sensitive_path(str(path), patterns):
            return True
        return False

    if recursive:
        for root, dirs, filenames in os.walk(directory, followlinks=False):
            root_path = Path(root)
            # Skip .git directories
            dirs[:] = [d for d in dirs if d != ".git"]

            for filename in filenames:
                file_path = root_path / filename
                rel_path = str(file_path.relative_to(directory))

                if _should_skip(file_path):
                    skipped.append(rel_path)
                    continue

                try:
                    stat = file_path.stat()
                    checksum = calculate_checksum(file_path)
                    content_type = get_content_type(file_path)
                    files.append(HandoffFile(
                        relative_path=rel_path,
                        size=stat.st_size,
                        checksum=checksum,
                        content_type=content_type,
                    ))
                except (OSError, IOError):
                    skipped.append(rel_path)
    else:
        for item in directory.iterdir():
            if item.is_file():
                rel_path = item.name
                if _should_skip(item):
                    skipped.append(rel_path)
                    continue
                try:
                    stat = item.stat()
                    checksum = calculate_checksum(item)
                    content_type = get_content_type(item)
                    files.append(HandoffFile(
                        relative_path=rel_path,
                        size=stat.st_size,
                        checksum=checksum,
                        content_type=content_type,
                    ))
                except (OSError, IOError):
                    skipped.append(rel_path)

    return files, skipped


# ruff: noqa: E402  # CIRCULAR IMPORT: service imports domain types
from .service import (
    create_manifest,
    write_manifest,
    list_handoffs as list_handoffs_service,
    get_handoff as get_handoff_service,
    get_latest_handoff as get_latest_handoff_service,
    create_handoff_metadata,
)

# CLI functions are imported in cli.py to avoid circular imports

__all__ = [
    "HandoffFile",
    "HandoffManifest",
    "GitContext",
    "is_sensitive_path",
    "calculate_checksum",
    "get_content_type",
    "scan_directory",
    "DEFAULT_EXCLUDE_PATTERNS",
    "create_manifest",
    "write_manifest",
    "list_handoffs",
    "get_handoff",
    "get_latest_handoff",
    "list_handoffs_service",
    "get_handoff_service",
    "get_latest_handoff_service",
    "create_handoff_metadata",
]