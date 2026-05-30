"""Filesystem scanning and path safety for Cheri tasks."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

import click

from .models import TaskDefinition, TaskRuntimeState, iso_now


DEFAULT_EXCLUDE_PATTERNS = [
    ".git",
    ".git/*",
    ".git/**",
    ".cheri",
    ".cheri/*",
    ".cheri/**",
    "__pycache__",
    "__pycache__/*",
    "__pycache__/**",
    "*.swp",
    "*.tmp",
    "*.part",
    "*.crdownload",
    "*~",
    ".DS_Store",
    "Thumbs.db",
    ".env",
    ".env.*",
    "*.env",
    ".env/**",
    "credentials.json",
    "*.key",
    "*.pem",
    "id_rsa",
    "id_rsa*",
    "id_ed25519",
    "id_ed25519*",
    ".npmrc",
    ".pypirc",
    ".netrc",
    "secrets.json",
    "secret.json",
]


@dataclass
class TaskScanResult:
    task: TaskDefinition
    root_path: Path
    current_snapshot: Dict[str, Dict[str, int]]
    path_map: Dict[str, Path]
    changed_paths: List[str]
    deleted_paths: List[str]
    skipped_sensitive: List[str] = field(default_factory=list)


def normalize_target_path(raw_path: str, target_type: str) -> Path:
    path = Path(raw_path).expanduser()
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise click.ClickException(f"Task target does not exist: {raw_path}") from exc
    if target_type == "file" and not resolved.is_file():
        raise click.ClickException(f"Expected a file target, got: {resolved}")
    if target_type == "directory" and not resolved.is_dir():
        raise click.ClickException(f"Expected a directory target, got: {resolved}")
    return resolved


def display_path_label(path: Path) -> str:
    cwd = Path.cwd()
    home = Path.home()
    try:
        return str(path.relative_to(cwd))
    except ValueError:
        try:
            return str(path.relative_to(home))
        except ValueError:
            return str(path)


def target_label(task: TaskDefinition) -> str:
    return display_path_label(Path(task.target_path))


def _snapshot_entry(path: Path) -> Dict[str, int]:
    stats = path.stat()
    return {
        "mtime_ns": int(getattr(stats, "st_mtime_ns", int(stats.st_mtime * 1_000_000_000))),
        "size": int(stats.st_size),
    }


def _path_allowed(relative_path: str, task: TaskDefinition) -> bool:
    relative_posix = relative_path.replace("\\", "/")
    include_patterns = list(task.include_patterns)
    exclude_patterns = DEFAULT_EXCLUDE_PATTERNS + list(task.exclude_patterns)
    if include_patterns and not any(fnmatch.fnmatch(relative_posix, pattern) for pattern in include_patterns):
        return False
    if any(fnmatch.fnmatch(relative_posix, pattern) for pattern in exclude_patterns):
        return False
    return True


def _collect_directory_files(root_path: Path, task: TaskDefinition) -> Dict[str, Path]:
    path_map: Dict[str, Path] = {}
    iterator = root_path.rglob("*") if task.recursive else root_path.glob("*")
    for candidate in iterator:
        if candidate.is_symlink():
            continue
        if not candidate.is_file():
            continue
        relative_path = candidate.relative_to(root_path).as_posix()
        if _path_allowed(relative_path, task):
            path_map[relative_path] = candidate
    return path_map


def collect_task_paths(task: TaskDefinition) -> Dict[str, Path]:
    root_path = normalize_target_path(task.target_path, task.target_type)
    if task.target_type == "file":
        return {root_path.name: root_path}
    return _collect_directory_files(root_path, task)


def build_snapshot(task: TaskDefinition) -> Dict[str, Dict[str, int]]:
    return {
        relative_path: _snapshot_entry(path)
        for relative_path, path in collect_task_paths(task).items()
    }


def prime_runtime_state(task: TaskDefinition, runtime: TaskRuntimeState) -> TaskRuntimeState:
    runtime.snapshot = build_snapshot(task)
    runtime.last_detected_change_at = ""
    runtime.updated_at = iso_now()
    return runtime


def scan_task(task: TaskDefinition, runtime: TaskRuntimeState, *, force: bool = False) -> TaskScanResult:
    root_path = normalize_target_path(task.target_path, task.target_type)
    all_files = _collect_all_files(root_path, task)
    skipped_sensitive: List[str] = []
    allowed_paths: Dict[str, Path] = {}
    for relative_path, path in all_files.items():
        if _path_allowed(relative_path, task):
            allowed_paths[relative_path] = path
        else:
            skipped_sensitive.append(relative_path)
    path_map = allowed_paths
    current_snapshot = {
        relative_path: _snapshot_entry(path)
        for relative_path, path in path_map.items()
    }
    previous_snapshot = runtime.snapshot or {}
    if force:
        changed_paths = sorted(current_snapshot.keys())
    else:
        changed_paths = sorted(
            relative_path
            for relative_path, snapshot_entry in current_snapshot.items()
            if previous_snapshot.get(relative_path) != snapshot_entry
        )
    deleted_paths = sorted(relative_path for relative_path in previous_snapshot if relative_path not in current_snapshot)
    return TaskScanResult(
        task=task,
        root_path=root_path,
        current_snapshot=current_snapshot,
        path_map=path_map,
        changed_paths=changed_paths,
        deleted_paths=deleted_paths,
        skipped_sensitive=skipped_sensitive,
    )


def _collect_all_files(root_path: Path, task: TaskDefinition) -> Dict[str, Path]:
    """Collect all files including those that may be excluded (for tracking skipped)."""
    path_map: Dict[str, Path] = {}
    iterator = root_path.rglob("*") if task.recursive else root_path.glob("*")
    for candidate in iterator:
        if candidate.is_symlink():
            continue
        if not candidate.is_file():
            continue
        relative_path = candidate.relative_to(root_path).as_posix()
        path_map[relative_path] = candidate
    return path_map
