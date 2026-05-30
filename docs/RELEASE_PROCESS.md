# Release Process

## Version Policy

Cheri uses semantic versioning with a beta/RC track for early releases:

- `v0.1.x` — Foundation beta (this track)
- `v0.2.x` — Storage abstraction and provider refactor
- `v0.3.x` — S3/GDrive/B2 provider beta
- `v1.0.0` — First stable CLI product

Pre-release versions use the `0.N.x` pattern. Breaking changes to public APIs will increment the minor version with a clear deprecation notice.

## Release Triggers

A release is cut when:
1. All CI checks pass (tests, lint, type-check, worker tests)
2. A version bump commit is merged to main
3. A tag is pushed matching the version pattern (e.g., `v0.1.0b1`)

## Version Bump Steps

1. Update `cheri_cloud_cli/__init__.py` version string
2. Update `setup.py` version and `python_requires`
3. Update `package.json` version
4. Update `CHANGELOG.md` with release date and changes
5. Commit with message: `release: v0.1.0b1`
6. Tag: `git tag -a v0.1.0b1 -m "Cheri v0.1.0b1 foundation beta"`
7. Push: `git push && git push --tags`

## Not in This Phase

- PyPI publishing (TestPyPI later)
- npm package publishing
- GitHub Releases automation (manual for now)