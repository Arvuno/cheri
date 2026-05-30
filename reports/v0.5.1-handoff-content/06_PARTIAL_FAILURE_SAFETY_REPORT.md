# Partial Failure Safety Report

## Overview
Handoff push/pull handle partial failures gracefully without silent success claims.

## Push Partial Failure Behavior

### When Files Fail to Upload

```python
# In push_handoff(), for each file:
try:
    result = upload_handoff_file(...)
    # annotate manifest entry
    uploaded_files.append(result)
except Exception as exc:
    file_entry["upload_status"] = "failed"
    failed_files.append({"path": rel_path, "error": str(exc)})
    console.print(f"  [red]![/] {rel_path}: {exc}")
```

### Status Determination

```python
if failed_files:
    handoff_status = "partial_failed"
    console.print(f"\n[yellow]Warning:[/] {len(failed_files)} file(s) failed to upload")
else:
    handoff_status = "ready"
```

### Backend Update with Failure Info

```python
backend_updates = {
    "status": handoff_status,  # "partial_failed" or "ready"
    "failed_files": [f["path"] for f in failed_files],
    # ... other fields
}
result = client.update_handoff(state, manifest["handoff_id"], backend_updates)
```

### Summary Panel

```
Status        : partial_failed
```

Border is yellow (not green) when there are failures.

## Pull Partial Failure Behavior

### Download Failures

```python
try:
    # download file
    dest_path.write_bytes(content)
    downloaded.append(rel_path)
except Exception as exc:
    failed.append(rel_path)
    console.print(f"  [red]![/] {rel_path}: {exc}")
```

### Checksum Mismatches

```python
if expected_checksum:
    actual_checksum = hashlib.sha256(content).hexdigest()
    if actual_checksum != expected_checksum:
        checksum_mismatches.append({"path": rel_path, "expected": ..., "actual": ...})
        failed.append(rel_path)
        console.print(f"  [red]![/] {rel_path}: checksum mismatch!")
        continue  # Don't write corrupted file
```

### Skipped Files (no file_id)

```python
if not file_id:
    skipped.append(rel_path)
    console.print(f"  [dim]-[dim] {rel_path} (no file_id - not uploaded)")
    continue
```

### Summary

```python
console.print(Panel.fit(
    f"Handoff ID   : {handoff_id}\n"
    f"Downloaded   : {len(downloaded)} file(s)\n"
    f"Failed       : {len(failed)} file(s)\n"
    f"Checksum mismatches: {len(checksum_mismatches)}\n"
    f"Skipped (no file_id): {len(skipped)}\n"
    f"Destination  : {output_dir}",
    title="Pull Complete",
    border_style="green" if not failed and not checksum_mismatches else "yellow",
))
```

## Exit Criteria

| Criterion | Status |
|-----------|--------|
| Push continues on file upload failure | PASS |
| Push reports failed paths | PASS |
| Push marks handoff `partial_failed` when failures exist | PASS |
| Push summary panel shows yellow border on failures | PASS |
| Pull continues on download failure | PASS |
| Pull reports checksum mismatches separately | PASS |
| Pull reports skipped files (no file_id) | PASS |
| Pull summary panel shows yellow border on failures | PASS |