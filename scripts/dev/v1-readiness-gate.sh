#!/bin/bash
# v1.0 Readiness Gate Script
# Runs all critical checks to verify Cheri is ready for v1.0 RC
# Exit codes: 0 = all pass, 1 = some fail

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

export CHERI_ALLOW_MYPY_DEBT="${CHERI_ALLOW_MYPY_DEBT:-0}"

echo "=========================================="
echo "Cheri v1.0 Readiness Gate"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS_COUNT=0
FAIL_COUNT=0

run_check() {
    local name="$1"
    local expected_exit="$2"
    shift 2
    echo -n "Checking: $name ... "
    set +e
    output=$("$@" 2>&1)
    actual_exit=$?
    set -e
    if [ $actual_exit -eq $expected_exit ]; then
        echo -e "${GREEN}PASS${NC}"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo -e "${RED}FAIL${NC} (exit code: $actual_exit)"
        echo "$output" | head -20
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
}

echo "--- Python Tests ---"
run_check "Python unit tests" 0 python -m unittest discover -s tests/python -p test_*.py

echo ""
echo "--- Node.js Tests ---"
run_check "Worker Node tests" 0 node tests/node/worker.test.mjs
run_check "Storage Node tests" 0 node tests/node/storage.test.mjs

echo ""
echo "--- npm Tests ---"
run_check "npm test" 0 npm test

echo ""
echo "--- Linting ---"
run_check "ruff check" 0 ruff check .

echo ""
echo "--- Type Checking ---"
MYPY_OUTPUT=$(mypy cheri_cloud_cli --ignore-missing-imports 2>&1)
MYPY_EXIT=$?
MYPY_ERRORS=$(echo "$MYPY_OUTPUT" | grep -c "error:" || echo "0")
echo -n "Checking: mypy type check ... "
if [ $MYPY_EXIT -eq 0 ]; then
    echo -e "${GREEN}PASS${NC} (0 errors)"
    PASS_COUNT=$((PASS_COUNT + 1))
elif [ "$CHERI_ALLOW_MYPY_DEBT" = "1" ]; then
    echo -e "${YELLOW}WARN${NC} (mypy errors: $MYPY_ERRORS, debt allowed)"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "${RED}FAIL${NC} (mypy errors: $MYPY_ERRORS)"
    echo "Set CHERI_ALLOW_MYPY_DEBT=1 to allow mypy debt for this session."
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi

echo ""
echo "--- CLI Version ---"
run_check "cheri CLI --help" 0 python -m cheri_cloud_cli.cli --help

echo ""
echo "--- Package Build ---"
run_check "python setup.py --version" 0 python setup.py --version
run_check "python build" 0 python -m build

echo ""
echo "--- Package Distribution Check ---"
run_check "twine check dist/*" 0 twine check dist/*

echo ""
echo "=========================================="
echo "Results: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "=========================================="

if [ $FAIL_COUNT -gt 0 ]; then
    echo -e "${RED}Gate FAILED${NC} - Fix failures before v1.0 RC"
    exit 1
else
    echo -e "${GREEN}Gate PASSED${NC} - Ready for v1.0 RC"
    exit 0
fi
