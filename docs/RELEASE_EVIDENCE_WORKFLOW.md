# Release Evidence Workflow

This document describes how to use Cheri's handoff feature to capture and share release evidence.

## Overview

Release evidence is the documentation, artifacts, and metadata that prove a release was completed successfully. Cheri's handoff feature makes it easy to capture and share this evidence through the CLI.

## Why Capture Release Evidence?

- **Audit trails**: Prove what was released, when, and by whom
- **Team visibility**: Share release details with the whole team automatically
- **Rollback support**: Understand what was in a release if you need to revert
- **Compliance**: Meet regulatory or organizational requirements for documented releases

## Release Evidence Components

A complete release evidence package typically includes:

### 1. Documentation
- Release notes (`CHANGELOG.md`, `RELEASE_NOTES.md`)
- Migration guides (for breaking changes)
- API documentation updates

### 2. Build Outputs
- Compiled binaries (if applicable)
- Container images (image references, not the images themselves)
- Test results and coverage reports

### 3. Metadata
- Version label (e.g., `v0.5.0`)
- Git commit hash
- Build timestamp
- Who approved the release

### 4. Verification
- Test pass/fail status
- Security scan results
- Lint/coverage checks

## Workflow

### 1. Prepare Release Directory

Before creating the handoff, organize your release evidence:

```bash
# Create a release evidence directory
mkdir -p release-evidence/v0.5.0

# Copy relevant files
cp CHANGELOG.md release-evidence/v0.5.0/
cp -r docs release-evidence/v0.5.0/
cp test-results/*.xml release-evidence/v0.5.0/ 2>/dev/null || true
```

### 2. Inspect Evidence

```bash
cheri handoff inspect ./release-evidence/v0.5.0
```

This shows what will be included and what was skipped (should include no secrets).

### 3. Create and Push Handoff

```bash
cheri handoff push ./release-evidence/v0.5.0 \
  --name "v0.5.0 release evidence" \
  --agent claude-code \
  --tool release-process \
  --version-label "v0.5.0" \
  --tag release \
  --tag v0.5.0 \
  --workspace engineering
```

### 4. Verify and Share

```bash
# Confirm the handoff
cheri handoff latest

# Team members can list and pull
cheri handoff list --workspace engineering | grep "v0.5.0"
cheri handoff pull hnd_abc123 --dest ~/release-reviews/v0.5.0
```

## Automated Release Integration

### CI/CD Pipeline Example

In a GitHub Actions workflow:

```yaml
- name: Create release handoff
  run: |
    mkdir -p release-artifacts
    echo "${{ github.sha }}" > release-artifacts/commit.txt
    echo "${{ github.event.release.tag_name }}" > release-artifacts/version.txt
    cp CHANGELOG.md release-artifacts/
    
    cheri handoff push ./release-artifacts \
      --name "${{ github.event.release.tag_name }} release" \
      --agent github-actions \
      --tool ci-pipeline \
      --version-label "${{ github.event.release.tag_name }}" \
      --tag release \
      --workspace ${{ env.CHERI_WORKSPACE }}
  env:
    CHERI_WORKSPACE: engineering
```

### Pre-release Verification

```bash
# Dry-run before pushing
cheri handoff inspect ./release-evidence

# List current handoffs to see history
cheri handoff list --workspace engineering
```

## Evidence Preservation

Handoff metadata is stored in the workspace's KV store and includes:

- Timestamp
- Source path
- Git context (branch, commit, dirty state)
- Agent/tool metadata
- File list with checksums

This provides an auditable trail of what was released.

## Post-Release Review

```bash
# Pull latest release evidence
cheri handoff pull $(cheri handoff latest --workspace engineering | grep id | cut -d: -f2) --dest ~/reviews
```

## Limitations

- Handoffs capture evidence at a point in time; they are not continuously updated
- File content upload depends on storage provider; large binaries may take time
- Pull does not merge with existing files; use a fresh directory for reviews

## See Also

- [AGENT_HANDOFF_WORKFLOWS.md](./AGENT_HANDOFF_WORKFLOWS.md)
- [HANDOFF_MANIFEST.md](./HANDOFF_MANIFEST.md)