# Manifest Schema Update Report

## Overview
Manifest schema bumped from 1.0 to 1.1 with addition of upload metadata fields per file entry.

## Changes

### HandoffFile (cheri_cloud_cli/handoff/__init__.py)

**New fields added:**
```python
file_id: Optional[str] = None           # From storage provider after upload
storage_key: Optional[str] = None      # Logical name: handoffs/{handoff_id}/{relative_path}
provider_id: Optional[str] = None      # Storage provider used (e.g., "system")
uploaded_at: Optional[str] = None       # ISO timestamp when uploaded
upload_status: Optional[str] = None    # "pending" | "uploaded" | "failed"
```

**New `to_dict()` behavior:**
Upload metadata fields are only included when set (not None):
```python
if self.file_id:
    d["file_id"] = self.file_id
if self.storage_key:
    d["storage_key"] = self.storage_key
# etc.
```

**New `from_dict()` class method for backward compatibility:**
```python
@classmethod
def from_dict(cls, d: dict) -> "HandoffFile":
    return cls(
        relative_path=d["relative_path"],
        size=d["size"],
        checksum=d["checksum"],
        content_type=d.get("content_type"),
        skipped=d.get("skipped", False),
        file_id=d.get("file_id"),
        storage_key=d.get("storage_key"),
        provider_id=d.get("provider_id"),
        uploaded_at=d.get("uploaded_at"),
        upload_status=d.get("upload_status"),
    )
```

### HandoffManifest

**Changed default:**
```python
schema_version: str = "1.1"  # Was "1.0"
```

## Backward Compatibility

| Scenario | Behavior |
|----------|----------|
| v1.0 manifest (no upload fields) loads via `HandoffFile.from_dict()` | All new fields default to None |
| `to_dict()` on v1.0-style HandoffFile | No upload metadata fields in output (they're None) |
| `create_manifest()` creates v1.1 manifest | New fields present only when set by push |

## Example v1.1 Manifest Entry

```json
{
  "relative_path": "src/app.js",
  "size": 1234,
  "checksum": "abc123...",
  "content_type": "text/javascript",
  "file_id": "fid_xyz789",
  "storage_key": "handoffs/hnd_abc123/src/app.js",
  "provider_id": "system",
  "uploaded_at": "2026-05-30T16:30:00Z",
  "upload_status": "uploaded"
}
```

## Verification

```python
>>> from cheri_cloud_cli.handoff import HandoffFile, HandoffManifest
>>> f = HandoffFile('a.txt', 100, 'abc', file_id='fid123', storage_key='handoffs/h123/a.txt', provider_id='system', uploaded_at='2026-05-30T00:00:00Z', upload_status='uploaded')
>>> d = f.to_dict()
>>> assert 'file_id' in d
>>> assert d['file_id'] == 'fid123'
>>> f2 = HandoffFile.from_dict({'relative_path': 'b.txt', 'size': 50, 'checksum': 'xyz'})
>>> assert f2.file_id is None  # v1.0 compatibility
>>> m = HandoffManifest(schema_version='1.1', name='test', files=[f])
>>> assert m.to_dict()['schema_version'] == '1.1'
```

## Exit Criteria

| Criterion | Status |
|-----------|--------|
| file_id, storage_key, provider_id, uploaded_at, upload_status fields exist | PASS |
| `from_dict()` handles v1.0 manifests (without new fields) | PASS |
| `to_dict()` only includes upload fields when set | PASS |
| schema_version defaults to "1.1" | PASS |