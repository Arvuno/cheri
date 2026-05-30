# Next v0.8 Plan

## Recommended Priority Items

### High Priority
1. **Resolve package version mismatch** (0.4.0b1 in wheel vs 0.6.0-reliability in __version__)
2. **Fix mypy type errors** (35+ errors, tech debt)
3. **Run ruff --fix** to clean up 36 auto-fixable style issues
4. **S3-compatible e2e test** — actual upload/download flow
5. **MinIO local dev environment** for testing S3-compatible provider

### Medium Priority
1. Add `long_description` to setup.py for PyPI
2. Keyring integration improvements
3. Add more Python unit tests for edge cases
4. Performance testing with large file handoffs

### Low Priority
1. Bidirectional sync (future feature, not in v0.8 scope)
2. WebSocket real-time updates
3. Team workspace analytics dashboard

## Blocking for v0.8

- PyPI publish requires owner approval
- Version number must be synchronized before publish
