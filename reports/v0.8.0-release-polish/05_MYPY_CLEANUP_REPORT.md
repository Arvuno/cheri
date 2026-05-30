# Mypy Cleanup Report

> Date: 2026-05-30

## Commands Run

```bash
mypy cheri_cloud_cli --ignore-missing-imports
```

## Initial State

49 errors across 14 files — pre-existing type debt

## Fixes Applied This Pass

None — these are pre-existing issues requiring significant refactoring

## Remaining Issues by Category

### Category: External Library Type Stubs

| File | Count | Root Cause |
|------|-------|------------|
| `sessions/store.py` | 12 | keyring uses `object` for credentials |
| `cli_framework.py` | 6 | Click mixin attrs not in stubs |

### Category: Complex Type Mismatches

| File | Count | Root Cause |
|------|-------|------------|
| `workspace/service.py` | 6 | TaskDefinition.get, list type mismatches |
| `services/watch_service.py` | 5 | Popen overloads, TaskRuntimeState |
| `storage.py` | 4 | WorkspaceSummary.get, Any vs AuthState |

### Category: Any Type Propagation

| File | Count | Root Cause |
|------|-------|------------|
| `contracts.py` | 3 | SessionContext/ProviderObjectRef Any vs str |
| `handoff/__init__.py` | 4 | to_dict() incompatible types |

### Category: Missing Attribute Definitions

| File | Count | Root Cause |
|------|-------|------------|
| `doctor.py` | 2 | TaskDefinition.get, generator type |
| `cli.py` | 2 | isinstance arg, Command.get_command |
| `init.py` | 2 | Union-attr on None |

### Category: API Differences

| File | Count | Root Cause |
|------|-------|------------|
| `handoff/cli.py` | 6 | Rich Console.input `default` kwarg not in stubs |

## Risk Assessment

Fixing would require:
1. Adding type: ignore comments (quick but dirty)
2. Refactoring type structures (time-consuming, risky)
3. Waiting for upstream stub fixes (not under our control)

## Recommendation

Document for v0.9 type cleanup sprint. Risky refactoring at this stage could introduce regressions.

## Result

**PARTIAL** — 49 pre-existing type errors remain, documented for v0.9 planning.
